"""Operator-reviewed Pre-ICFES journey with encrypted environment-bound intents."""

from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException, Response
from pydantic import Field

from app.institutional import db, siie_records as records, siie_environment as environments
from app.institutional import siie_preicfes_client as source
from app.institutional.auth import authorize, rate
from app.institutional.models import Strict
from app.institutional.policy import request_authority
from app.institutional.siie_webhook import config
from app.institutional.store import transaction

PREFIX = "/api/institution/siie-registration/preicfes"


class Prepare(Strict):
    event_id: str
    conversation_id: str
    environment: dict
    reviewed: Literal[True]


class Command(Strict):
    operation_id: str
    revision: int = Field(ge=1)
    reviewed: Literal[True]
    plan_id: int | None = Field(default=None, ge=1, le=2147483647)
    mode: Literal["CONTADO", "FINANCIADO"] | None = None
    quote_revision_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    choice_message_id: str | None = None
    installment_id: int | None = Field(default=None, ge=1, le=2147483647)


def actor(c, settings):
    return authorize(c, settings, request_authority.get(), "crm.write")


def sender(c, settings, conversation):
    rows = db.rows(c, "SELECT TOP(2) i.IdentityId,i.IntegrationId,i.ExternalId,i.ContactId "
        "FROM crm_channels2.ExternalIdentity i JOIN crm_channels2.Integration a "
        "ON a.InstitutionId=i.InstitutionId AND a.IntegrationId=i.IntegrationId "
        "JOIN crm.Conversation v ON v.ConversationId=i.ConversationId AND v.ContactId=i.ContactId "
        "WHERE i.InstitutionId=? AND i.ConversationId=? AND a.Channel='whatsapp' AND v.State<>'closed' "
        "AND EXISTS(SELECT 1 FROM crm.Message m JOIN crm_channels2.MessageRoute r "
        "ON r.InstitutionId=i.InstitutionId AND r.MessageId=m.MessageId AND r.IdentityId=i.IdentityId "
        "AND r.IntegrationId=i.IntegrationId WHERE m.ConversationId=i.ConversationId "
        "AND m.Direction='incoming' AND r.ActorKind='external')",
        db.institution(settings), db.uid(conversation))
    if len(rows) != 1:
        raise HTTPException(409, "siie_finance_verified_sender_required")
    row = rows[0]
    from app.institutional.workspace import primary
    return {"identity_id": db.uid(str(row["IdentityId"])), "contact_id": primary(c,str(row["ContactId"])),
            "waId": str(row["ExternalId"]), "channelAccountId": db.uid(str(row["IntegrationId"])),
            "conversationId": db.uid(conversation)}


def flow(c, settings, identity):
    value = records.get(c, settings, "sf", db.uid(identity))
    if not value:
        raise HTTPException(404, "siie_finance_flow_not_found")
    return value


def live(c, settings, value):
    private = value["private"]
    environments.require(private["environment"])
    if sender(c,settings,private["sender"]["conversationId"]) != private["sender"]:
        raise HTTPException(409, "siie_finance_sender_changed")
    return private


def payload(private, *, binding=True):
    result = {**private["ids"], **{k:private["sender"][k] for k in ("conversationId","channelAccountId")}}
    if binding:
        bound = private.get("binding")
        if not bound:
            raise HTTPException(409, "siie_finance_binding_required")
        source.future(bound["expiresAtUtc"])
        result["bindingId"] = bound["bindingId"]
    return result


class Finance:
    def __init__(self, settings):
        self.settings = settings

    def tx(self, write=False, *, anonymous=False):
        return transaction(self.settings, write, permission=None if anonymous else "crm.write", anonymous=anonymous)

    def read(self, identity):
        with self.tx() as c:
            actor(c,self.settings)
            value = flow(c,self.settings,identity)
            private = value["private"]
            binding_expired = False
            if private.get("binding"):
                try:
                    source.future(private["binding"]["expiresAtUtc"])
                except HTTPException as expired:
                    if expired.detail != "siie_finance_expired":
                        raise
                    binding_expired = True
            return {"id":identity,"revision":value["revision"],**value["metadata"],
                    **{k:v for k,v in private.items() if k in {"environment","registration","binding","plans","assignment","order","payment","pending"}},
                    "environment_current": private["environment"] == environments.current().document(),
                    "binding_expired":binding_expired,
                    "writes_enabled":config(c,self.settings)["writes_enabled"], "gateway_enabled":False}

    def recent(self, offset=0):
        with self.tx() as c:
            actor(c,self.settings)
            return records.recent(c,self.settings,"sf",offset=offset)

    def prepare(self, body):
        body = body.model_copy(update={"event_id":db.uid(body.event_id),"conversation_id":db.uid(body.conversation_id)})
        environment = environments.require(body.environment).document()
        with self.tx() as c:
            actor(c,self.settings)
            receipt = records.get(c,self.settings,"se",db.uid(body.event_id))
            if not receipt or receipt["private"]["event"]["event_type"] != "registration.created":
                raise HTTPException(409,"siie_finance_registration_event_required")
            event = receipt["private"]["event"]
            proof = sender(c,self.settings,db.uid(body.conversation_id))
            linked = receipt["private"].get("contact_id")
            from app.institutional.workspace import primary
            if not linked or primary(c,str(linked)) != proof["contact_id"]:
                raise HTTPException(409,"siie_finance_contact_link_required")
            ids = {k:event[k] for k in source.IDS}
        registered = source.request("registration",ids,environment)["data"]
        # A same-number or same-name candidate is never sufficient; SIIE's
        # subsequent binding also checks the original event and trusted sender.
        if registered["documento"] != event["documento"]:
            raise HTTPException(409,"siie_finance_registration_mismatch")
        identity = str(uuid5(NAMESPACE_URL,"siie-finance:"+environment["fingerprint"]+":"+body.event_id+":"+body.conversation_id))
        with self.tx(True) as c:
            who = actor(c,self.settings)
            environments.require(environment)
            if sender(c,self.settings,body.conversation_id) != proof:
                raise HTTPException(409,"siie_finance_sender_changed")
            old = records.get(c,self.settings,"sf",identity)
            if not old:
                records.put(c,self.settings,"sf",identity,{"state":"registration_confirmed","environment_fingerprint":environment["fingerprint"],"base_url":environment["base_url"]},
                    {"environment":environment,"ids":ids,"event_id":body.event_id,"sender":proof,"registration":registered})
                db.audit(c,self.settings,who["UserId"],"siie.finance.prepared",identity)
        return self.read(identity)

    def query(self, identity, kind):
        with self.tx() as c:
            actor(c,self.settings); value=flow(c,self.settings,identity); private=live(c,self.settings,value)
            request=payload(private)
            if kind == "payment":
                if not private.get("order"):
                    raise HTTPException(409,"siie_finance_order_required")
                request["orderId"]=private["order"]["orderId"]
        result=source.request(kind,request,private["environment"])["data"]
        with self.tx(True) as c:
            actor(c,self.settings); current=flow(c,self.settings,identity); live(c,self.settings,current)
            if current["revision"] != value["revision"]:
                raise HTTPException(409,"revision_conflict")
            records.put(c,self.settings,"sf",identity,current["metadata"],{**current["private"],kind:result},current)
        return self.read(identity)

    def command(self, identity, kind, body):
        operation=db.uid(body.operation_id)
        digest=db.bound_hash(self.settings,{"flow":identity,"kind":kind,"command":body.model_dump()},"siie_finance_command").hex()
        with self.tx(True) as c:
            who=actor(c,self.settings); value=flow(c,self.settings,identity); private=live(c,self.settings,value)
            prior=records.get(c,self.settings,"sx",operation)
            if prior:
                if prior["private"]["digest"] != digest:
                    raise HTTPException(409,"operation_conflict")
                return {"operation_id":operation,**prior["private"]["result"],"repeated":True}
            renewing = False
            if private.get("pending") and kind == "binding" and private.get("binding"):
                prior_op = records.get(c,self.settings,"sx",private["pending"])
                if prior_op and prior_op["private"]["kind"] != "binding":
                    try:
                        source.future(private["binding"]["expiresAtUtc"])
                    except HTTPException as expired:
                        if expired.detail == "siie_finance_expired":
                            renewing = True
            if value["revision"] != body.revision or (private.get("pending") and not renewing):
                raise HTTPException(409,"siie_finance_reconciliation_required")
            if not config(c,self.settings)["writes_enabled"]:
                raise HTTPException(409,"siie_registration_writes_disabled")
            request=payload(private,binding=kind!="binding")
            request["requestId"]=operation
            if kind=="binding":
                request.update(eventId=private["event_id"],waId=private["sender"]["waId"])
            elif kind=="assign":
                options=private.get("plans",{}).get("options",[])
                chosen=next((v for v in options if (v["planId"],v["mode"],v["quoteRevisionId"]) ==
                            (body.plan_id,body.mode,body.quote_revision_id)),None)
                if not chosen or not body.choice_message_id:
                    raise HTTPException(409,"siie_finance_explicit_choice_required")
                source.future(chosen["expiresAtUtc"])
                message=db.one(c,"SELECT m.Body FROM crm.Message m JOIN crm_channels2.MessageRoute r ON r.MessageId=m.MessageId "
                    "WHERE r.InstitutionId=? AND r.IdentityId=? AND m.ConversationId=? AND m.MessageId=? "
                    "AND m.Direction='incoming' AND r.ActorKind='external'",db.institution(self.settings),
                    private["sender"]["identity_id"],private["sender"]["conversationId"],db.uid(body.choice_message_id))
                if not message or not message["Body"]:
                    raise HTTPException(409,"siie_finance_explicit_choice_required")
                request.update(planId=body.plan_id,mode=body.mode,quoteRevisionId=body.quote_revision_id)
            elif kind=="order":
                assigned=private.get("assignment",{})
                if not any(v["installmentId"]==body.installment_id for v in assigned.get("plan",{}).get("installments",[])):
                    raise HTTPException(409,"siie_finance_assignment_required")
                request.update(assignmentId=assigned["assignmentId"],installmentId=body.installment_id)
            else:
                raise HTTPException(404,"siie_finance_route_not_found")
            source.parameters(kind,request)
            if not rate(c,self.settings,"siie-finance-write",30,60):
                raise HTTPException(429,"siie_registration_rate_limited",headers={"Retry-After":"60"})
            result={"state":"uncertain","code":"siie_finance_pending_reconciliation"}
            records.put(c,self.settings,"sx",operation,{"state":"pending_review","kind":kind},
                {"digest":digest,"flow_id":identity,"environment":private["environment"],"kind":kind,"payload":request,"result":result})
            records.put(c,self.settings,"sf",identity,{**value["metadata"],"state":"pending_review"},
                {**private,**({"reconcile_pending":private["pending"]} if renewing else {}),"pending":operation},value)
            db.audit(c,self.settings,who["UserId"],"siie.finance.intent",operation,kind=kind)
        result=source.request(kind,request,private["environment"])
        self.settle(identity,operation,result)
        with self.tx() as c:
            actor(c,self.settings)
        return {"operation_id":operation,**result}

    def settle(self, identity, operation, result):
        with self.tx(True,anonymous=True) as c:
            value=flow(c,self.settings,identity); op=records.get(c,self.settings,"sx",operation)
            if not op or value["private"].get("pending") != operation:
                raise HTTPException(409,"siie_finance_reconciliation_required")
            private={**value["private"]}; kind=op["private"]["kind"]
            if result["state"]!="uncertain":
                private.pop("pending",None)
                if kind == "binding" and private.get("reconcile_pending"):
                    private["pending"] = private.pop("reconcile_pending")
            if result["state"]=="confirmed":
                private[{"binding":"binding","assign":"assignment","order":"order"}[kind]]=result["data"]
            records.put(c,self.settings,"sx",operation,{**op["metadata"],"state":result["state"]},{**op["private"],"result":result},op)
            records.put(c,self.settings,"sf",identity,{**value["metadata"],"state":result["state"]},private,value)
            db.audit(c,self.settings,None,"siie.finance.result",operation,kind=kind)

    def reconcile(self, identity):
        with self.tx() as c:
            actor(c,self.settings); value=flow(c,self.settings,identity); private=live(c,self.settings,value)
            operation=private.get("pending")
            op=records.get(c,self.settings,"sx",operation) if operation else None
            if not op:
                raise HTTPException(409,"siie_finance_reconciliation_required")
            kind=op["private"]["kind"]
            request={**payload(private,binding=kind!="binding"),"requestId":operation,
                     "operation":{"binding":"Conversacion","assign":"Plan","order":"Volante"}[kind]}
        result=source.request("operation",request,private["environment"])
        source.validate(kind,result["data"],op["private"]["payload"])
        self.settle(identity,operation,result)
        return self.read(identity)

    def pdf(self, identity):
        with self.tx() as c:
            actor(c,self.settings); value=flow(c,self.settings,identity); private=live(c,self.settings,value)
            order=private.get("order")
            if not order:
                raise HTTPException(409,"siie_finance_order_required")
            request={**payload(private),"orderId":order["orderId"],"pdfVersion":order["pdf"]["version"]}
        data=source.request("pdf",request,private["environment"],pdf=order["pdf"])
        with self.tx() as c:
            actor(c,self.settings); current=flow(c,self.settings,identity); live(c,self.settings,current)
            if current["revision"]!=value["revision"]:
                raise HTTPException(409,"revision_conflict")
        return Response(data,media_type="application/pdf",headers={"Cache-Control":"no-store",
            "Content-Disposition":'attachment; filename="volante-preicfes.pdf"',"X-Content-Type-Options":"nosniff"})


def install(app, settings):
    service=Finance(settings)
    @app.get(PREFIX)
    def recent(offset:int=0):
        if not 0 <= offset <= 1000000:
            raise HTTPException(422,"siie_invalid_parameter")
        return service.recent(offset)
    @app.post(PREFIX+"/prepare")
    def prepare(body:Prepare):return service.prepare(body)
    @app.get(PREFIX+"/{identity}")
    def read(identity:str):return service.read(db.uid(identity))
    @app.get(PREFIX+"/{identity}/plans")
    def plans(identity:str):return service.query(db.uid(identity),"plans")
    @app.get(PREFIX+"/{identity}/payment")
    def payment(identity:str):return service.query(db.uid(identity),"payment")
    @app.post(PREFIX+"/{identity}/reconcile")
    def reconcile(identity:str):return service.reconcile(db.uid(identity))
    @app.post(PREFIX+"/{identity}/{kind}")
    def command(identity:str,kind:Literal["binding","assign","order"],body:Command):return service.command(db.uid(identity),kind,body)
    @app.get(PREFIX+"/{identity}/pdf")
    def pdf(identity:str):return service.pdf(db.uid(identity))
