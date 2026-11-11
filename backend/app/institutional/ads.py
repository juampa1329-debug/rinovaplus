"""Account-scoped local Ads records and CRM links. No advertising provider IO."""

import hashlib
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import HTTPException

from app.institutional.auth import authorize
from app.institutional.channel_text import sql_text
from app.institutional.crypto import canonical, seal
from app.institutional.db import (
    institution,
    key,
    one,
    record_operation,
    replay,
    rows,
    uid,
    utc,
)
from app.institutional.settings import setting
from app.institutional.store import transaction
from app.institutional.workspace import primary
from app.modules.crm_configuration.application.service import (
    read_configuration,
    validate_contact,
)
from app.modules.inbox.application.state import control
from app.sql_workspace import Contact


def packed(v):
    return canonical(v).decode()


def stable(*v):
    return str(uuid5(NAMESPACE_URL, "cbn-ads9:" + packed(v)))


def clock():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def account(c, s, id):
    row = one(
        c,
        "SELECT * FROM crm_ads9.Account WHERE InstitutionId=? AND AccountId=?",
        institution(s),
        uid(str(id)),
    )
    if not row:
        raise HTTPException(404, "ads_account_not_found")
    return row


def get(c, s, id, kind):
    table, col = {
        "campaign": ("Campaign", "CampaignId"),
        "intake": ("Intake", "IntakeId"),
        "run": ("SyncRun", "RunId"),
    }[kind]
    row = one(
        c,
        "SELECT * FROM crm_ads9." + table + " WHERE InstitutionId=? AND " + col + "=?",
        institution(s),
        uid(str(id)),
    )
    if not row:
        raise HTTPException(404, "ads_record_not_found")
    return row


def event(c, s, a, actor, kind, data, *, intake=None, run=None):
    c.execute(
        "INSERT crm_ads9.Event(InstitutionId,EventId,AccountId,Kind,IntakeId,RunId,ActorId,Document) VALUES(?,?,?,?,?,?,?,?)",
        institution(s),
        str(uuid4()),
        str(a),
        kind,
        intake,
        run,
        actor["UserId"],
        packed(data),
    )


def program(c, s, id):
    if id is None:
        return None
    value = one(
        c,
        "SELECT ProgramId,Name,Schedule FROM crm_agents5.Program WHERE InstitutionId=? AND ProgramId=? AND Active=1",
        institution(s),
        id,
    )
    if not value:
        raise HTTPException(409, "ads_program_review_required")
    return value


def stage(c, document):
    config, _ = read_configuration(c, foundation=True)
    selected = next(
        (
            v
            for v in config.stages
            if v.active
            and (
                v.key == document["initial_stage_key"]
                if document["initial_stage_key"]
                else True
            )
        ),
        None,
    )
    if not selected:
        raise HTTPException(409, "ads_stage_review_required")
    return selected


def same_channel(a, channel):
    if (a["Provider"] == "tiktok") != (channel == "tiktok"):
        raise HTTPException(409, "ads_account_channel_mismatch")


def conversation_matches(c, conversation, contact):
    value = c.execute(
        "SELECT ContactId FROM crm.Conversation WHERE ConversationId=?", conversation
    ).fetchone()
    return bool(value and primary(c, uid(str(value[0]))) == contact)


def linked(c, s, row):
    if not row.get("IdentityId"):
        return {}
    link = one(
        c,
        "SELECT * FROM crm_ads9.Identity WHERE InstitutionId=? AND AccountId=? AND IdentityId=?",
        institution(s),
        row["AccountId"],
        row["IdentityId"],
    )
    if not link:
        raise HTTPException(409, "ads_identity_link_unavailable")
    contact = primary(c, uid(str(link["ContactId"])))
    if not conversation_matches(c, link["ConversationId"], contact):
        raise HTTPException(409, "ads_conversation_link_changed")
    return dict(contact_id=contact, conversation_id=uid(str(link["ConversationId"])))


def public(c, s, row, kind):
    value = json.loads(row["Document"])
    idkey = {
        "account": "AccountId",
        "campaign": "CampaignId",
        "intake": "IntakeId",
        "run": "RunId",
    }[kind]
    result = dict(
        value,
        id=uid(str(row[idkey])),
        revision=row["Revision"],
        created_at=utc(row.get("CreatedAt", row.get("StartedAt"))),
        updated_at=utc(row.get("UpdatedAt", row.get("CompletedAt"))),
        provider_writes=False,
    )
    if row.get("AccountId"):
        result["account_id"] = uid(str(row["AccountId"]))
    if kind == "account":
        result.update(
            status=row["State"],
            has_access_token=row["SecretId"] is not None,
            credential_verified=False,
            record_authority="operator_declared",
            last_sync_at=None,
        )
    elif kind == "campaign":
        result.update(metric_source="operator_declared", last_sync_at=None)
    elif kind == "intake":
        result.update(
            kind=row["Kind"],
            status=row["State"],
            origin=row["Origin"],
            captured_at=utc(row["CapturedAt"]),
            converted_at=utc(row["ConvertedAt"]),
            **linked(c, s, row),
        )
    else:
        result.update(
            state=row["State"],
            error=row["ErrorCode"],
            receipt_id=uid(str(row["ReceiptId"])),
            source="verified_C10_receipts",
            started_at=utc(row["StartedAt"]),
            completed_at=utc(row["CompletedAt"]),
        )
    return result


def identity_subject(doc, kind, external_id):
    """Use useful explicit coordinates only; malformed values never coalesce people."""
    if doc["author_id"]:
        return "author:" + doc["author_id"]
    if kind == "lead":
        raw = doc["phone"].strip()
        digits = "".join(v for v in raw if "0" <= v <= "9")
        if (
            7 <= len(digits) <= 15
            and all(v in "0123456789+ ().-" for v in raw)
            and ("+" not in raw or raw.startswith("+") and raw.count("+") == 1)
        ):
            return "phone:" + digits
        email = doc["email"].strip().casefold()
        if (
            email.count("@") == 1
            and all(email.split("@"))
            and not any(v.isspace() for v in email)
        ):
            return "email:" + email
    return kind + ":" + external_id


def convert(c, s, auth, actor, row, a):
    authorize(c, s, auth, "crm.write")
    authorize(c, s, auth, "inbox.write")
    if row["IdentityId"]:
        return linked(c, s, row)
    if a["State"] != "connected":
        raise HTTPException(409, "ads_account_paused")
    if row["State"] in {"deleted", "hidden"}:
        raise HTTPException(409, "ads_capture_unavailable")
    doc = json.loads(row["Document"])
    adoc = json.loads(a["Document"])
    author = doc["author_id"]
    subject_value = identity_subject(doc, row["Kind"], row["ExternalId"])
    subject = hashlib.sha256(
        packed([doc["channel"], subject_value]).encode()
    ).hexdigest()
    identity = one(
        c,
        "SELECT * FROM crm_ads9.Identity WHERE InstitutionId=? AND AccountId=? AND Channel=? AND SubjectKey=?",
        institution(s),
        a["AccountId"],
        doc["channel"],
        subject,
    )
    contact = conversation = None
    if not identity and author and a["IntegrationId"]:
        # An existing DM/comment link may be reused; a form never creates a DM identity.
        native = one(
            c,
            "SELECT ContactId,ConversationId FROM crm_channels2.ExternalIdentity WHERE InstitutionId=? AND IntegrationId=? AND ExternalId=?",
            institution(s),
            a["IntegrationId"],
            author,
        )
        if not native:
            native = one(
                c,
                "SELECT TOP(1) TRY_CONVERT(uniqueidentifier,JSON_VALUE(Payload,'$._crm.contact_id')) AS ContactId,TRY_CONVERT(uniqueidentifier,JSON_VALUE(Payload,'$._crm.conversation_id')) AS ConversationId FROM crm_channels2.SocialComment WHERE InstitutionId=? AND IntegrationId=? AND AuthorExternalId=? AND JSON_VALUE(Payload,'$._crm.contact_id') IS NOT NULL ORDER BY ReceivedAt,CommentId",
                institution(s),
                a["IntegrationId"],
                author,
            )
        if native:
            contact = primary(c, uid(str(native["ContactId"])))
            conversation = uid(str(native["ConversationId"]))
            if not conversation_matches(c, conversation, contact):
                raise HTTPException(409, "ads_conversation_link_changed")
    if identity:
        contact = primary(c, uid(str(identity["ContactId"])))
        conversation = uid(str(identity["ConversationId"]))
        if not conversation_matches(c, conversation, contact):
            raise HTTPException(409, "ads_conversation_link_changed")
    if not contact:
        offering = program(c, s, row["ProgramId"])
        selected = stage(c, adoc)
        contact, conversation = str(uuid4()), str(uuid4())
        candidate = Contact(
            id=contact,
            name=sql_text(doc["contact_name"] or "Aspirante de " + adoc["name"], 100),
            phone=doc["phone"],
            city="",
            programId=row["ProgramId"],
            program=offering["Name"] if offering else "",
            schedule=sql_text(offering["Schedule"], 100) if offering else "",
            stage=selected.label,
            tags="",
            notes="",
            type="",
            interests="",
            customValues={},
        )
        validate_contact(c, candidate, foundation=True)
        c.execute(
            "INSERT crm.Contact(ContactId,Name,Phone,City,ProgramId,Program,Schedule,Stage,Tags,Notes,Type,Interests,CustomValues) VALUES(?,?,?,'',?,?,?,?,'','','','','{}')",
            contact,
            candidate.name,
            candidate.phone,
            candidate.programId,
            candidate.program,
            candidate.schedule,
            candidate.stage,
        )
        c.execute(
            "INSERT crm.Conversation(ConversationId,ContactId,State,Priority,ControlMode,Unread) VALUES(?,?,'open','normal','human',1)",
            conversation,
            contact,
        )
        control(c, conversation)
    historical_contact = uid(
        str(
            c.execute(
                "SELECT ContactId FROM crm.Conversation WHERE ConversationId=?",
                conversation,
            ).fetchval()
        )
    )
    if row.get("SocialCommentId"):
        comment = one(
            c,
            "SELECT Payload FROM crm_channels2.SocialComment WHERE InstitutionId=? AND CommentId=? AND IntegrationId=?",
            institution(s),
            row["SocialCommentId"],
            a["IntegrationId"],
        )
        if not comment:
            raise HTTPException(409, "ads_comment_link_changed")
        payload = json.loads(comment["Payload"])
        state = payload.setdefault("_crm", {})
        if state.get("state") == "deleted":
            raise HTTPException(409, "comment_deleted")
        if state.get("contact_id") and (
            primary(c, state["contact_id"]) != contact
            or state.get("conversation_id") != conversation
        ):
            raise HTTPException(409, "ads_comment_link_changed")
        state.update(contact_id=historical_contact, conversation_id=conversation)
        c.execute(
            "UPDATE crm_channels2.SocialComment SET Payload=? WHERE InstitutionId=? AND CommentId=?",
            packed(payload),
            institution(s),
            row["SocialCommentId"],
        )
    if not identity:
        identity = dict(IdentityId=str(uuid4()))
        c.execute(
            "INSERT crm_ads9.Identity(InstitutionId,IdentityId,AccountId,Channel,SubjectKey,ContactId,ConversationId) VALUES(?,?,?,?,?,?,?)",
            institution(s),
            identity["IdentityId"],
            a["AccountId"],
            doc["channel"],
            subject,
            historical_contact,
            conversation,
        )
    c.execute(
        "INSERT crm_workspace.Note(NoteId,ContactId,InstitutionId,AuthorId,Body) VALUES(?,?,?,?,?)",
        str(uuid4()),
        historical_contact,
        institution(s),
        actor["UserId"],
        sql_text(
            "Captación "
            + ("formulario" if row["Kind"] == "lead" else "comentario")
            + " · "
            + adoc["name"]
            + " · "
            + row["ExternalId"]
            + "\n"
            + doc["email"]
            + "\n"
            + doc["message"],
            2000,
        ),
    )
    c.execute(
        "UPDATE crm_ads9.Intake SET IdentityId=?,State='converted',ConvertedAt=SYSUTCDATETIME(),Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND IntakeId=?",
        identity["IdentityId"],
        institution(s),
        row["IntakeId"],
    )
    c.execute("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
    event(
        c,
        s,
        a["AccountId"],
        actor,
        "converted",
        dict(
            contact_id=contact,
            conversation_id=conversation,
            messaging_consent_granted=False,
        ),
        intake=str(row["IntakeId"]),
    )
    return dict(contact_id=contact, conversation_id=conversation)


class Ads:
    def __init__(self, settings):
        self.settings = settings

    @contextmanager
    def tx(self, auth, write=False, recent=False):
        with transaction(self.settings, write, anonymous=True) as c:
            actor = authorize(c, self.settings, auth, "ads.manage", recent=recent)
            authorize(c, self.settings, auth, "crm.read")
            if not setting(c, self.settings, "modules")["document"]["enabled"].get(
                "ads", False
            ):
                raise HTTPException(403, "module_disabled")
            yield c, actor

    def options(self, auth):
        from app.institutional.agent_catalog import Catalog

        with self.tx(auth) as (c, _):
            config, _ = read_configuration(c, foundation=True)
            return dict(
                accounts=[
                    public(c, self.settings, v, "account")
                    for v in rows(
                        c,
                        "SELECT TOP(201) * FROM crm_ads9.Account WHERE InstitutionId=? ORDER BY UpdatedAt DESC,AccountId",
                        institution(self.settings),
                    )
                ],
                integrations=[
                    dict(
                        id=uid(str(v["IntegrationId"])),
                        name=v["DisplayName"],
                        channel=v["Channel"],
                        provider=v["Provider"],
                    )
                    for v in rows(
                        c,
                        "SELECT IntegrationId,DisplayName,Channel,Provider FROM crm_channels2.Integration WHERE InstitutionId=? AND Channel IN('facebook','messenger','instagram','tiktok') AND VerifiedStatus<>'retired' ORDER BY DisplayName",
                        institution(self.settings),
                    )
                ],
                programs=Catalog(self.settings).programs(c, 0, 300)["items"],
                stages=[
                    dict(key=v.key, label=v.label) for v in config.stages if v.active
                ],
                external_sync_supported=False,
                provider_spending_supported=False,
                creative_addons_enabled=False,
            )

    def _list(
        self, c, kind, account_id=None, status=None, offset=0, start=None, end=None
    ):
        table = {
            "account": "Account",
            "campaign": "Campaign",
            "lead": "Intake",
            "comment": "Intake",
            "run": "SyncRun",
        }[kind]
        where = "InstitutionId=?"
        params = [institution(self.settings)]
        if account_id:
            account(c, self.settings, account_id)
            where += " AND AccountId=?"
            params.append(account_id)
        if kind in {"lead", "comment"}:
            where += " AND Kind=?"
            params.append(kind)
        if status and status != "all" and kind in {"lead", "comment", "run"}:
            where += " AND State=?"
            params.append(status)
        date = (
            "CapturedAt"
            if kind in {"lead", "comment"}
            else "StartedAt"
            if kind == "run"
            else "UpdatedAt"
        )
        if start:
            where += " AND " + date + ">=?"
            params.append(start)
        if end:
            where += " AND " + date + "<DATEADD(day,1,CONVERT(datetime2,?))"
            params.append(end)
        idcol = {
            "account": "AccountId",
            "campaign": "CampaignId",
            "lead": "IntakeId",
            "comment": "IntakeId",
            "run": "RunId",
        }[kind]
        values = rows(
            c,
            "SELECT * FROM crm_ads9."
            + table
            + " WHERE "
            + where
            + " ORDER BY "
            + date
            + " DESC,"
            + idcol
            + " OFFSET ? ROWS FETCH NEXT 51 ROWS ONLY",
            *params,
            offset,
        )
        return [
            public(
                c, self.settings, v, "intake" if kind in {"lead", "comment"} else kind
            )
            for v in values
        ]

    def listing(self, auth, kind, **filters):
        with self.tx(auth) as (c, _):
            values = self._list(c, kind, **filters)
            return dict(
                items=values[:50],
                has_more=len(values) > 50,
                offset=filters.get("offset", 0),
                limit=50,
                source="local_Ads_records",
                provider_writes=False,
            )

    def summary(self, auth, account_id=None, start=None, end=None):
        with self.tx(auth) as (c, _):
            if account_id:
                account(c, self.settings, account_id)
            suffix = " AND AccountId=?" if account_id else ""
            args = [institution(self.settings), *([account_id] if account_id else [])]
            counts = {
                n: c.execute(
                    "SELECT COUNT(*) FROM crm_ads9."
                    + t
                    + " WHERE InstitutionId=?"
                    + suffix,
                    *args,
                ).fetchval()
                for n, t in [("accounts", "Account"), ("campaigns", "Campaign")]
            }
            predicate = "InstitutionId=?" + suffix
            params = list(args)
            if start:
                predicate += " AND CapturedAt>=?"
                params.append(start)
            if end:
                predicate += " AND CapturedAt<DATEADD(day,1,CONVERT(datetime2,?))"
                params.append(end)
            for k in ["lead", "comment"]:
                counts[k + "s"] = c.execute(
                    "SELECT COUNT(*) FROM crm_ads9.Intake WHERE "
                    + predicate
                    + " AND Kind=?",
                    *params,
                    k,
                ).fetchval()
                counts["open_" + k + "s"] = c.execute(
                    "SELECT COUNT(*) FROM crm_ads9.Intake WHERE "
                    + predicate
                    + " AND Kind=? AND State IN('new','review')",
                    *params,
                    k,
                ).fetchval()
            counts["conversations"] = c.execute(
                "SELECT COUNT(DISTINCT ConversationId) FROM crm_ads9.Identity WHERE InstitutionId=?"
                + suffix,
                *args,
            ).fetchval()
            receipt_where = "r.InstitutionId=? AND r.Authentication='verified'"
            receipt_params = [institution(self.settings)]
            if account_id:
                receipt_where += " AND a.AccountId=?"
                receipt_params.append(account_id)
            if start:
                receipt_where += " AND r.ReceivedAt>=?"
                receipt_params.append(start)
            if end:
                receipt_where += " AND r.ReceivedAt<DATEADD(day,1,CONVERT(datetime2,?))"
                receipt_params.append(end)
            counts["webhook_events"] = c.execute(
                "SELECT COUNT(DISTINCT r.ReceiptId) FROM crm_channels2.WebhookReceipt r JOIN crm_channels2.EndpointIntegration ei ON ei.InstitutionId=r.InstitutionId AND ei.EndpointId=r.EndpointId AND ei.ApplicationId=r.ApplicationId JOIN crm_ads9.Account a ON a.InstitutionId=ei.InstitutionId AND a.IntegrationId=ei.IntegrationId WHERE "
                + receipt_where,
                *receipt_params,
            ).fetchval()
            counts["social_conversations"] = counts["conversations"]
            return dict(
                summary=counts,
                period=dict(start=start, end=end),
                source="local_Ads_records",
                as_of=utc(clock()),
                provider_writes=False,
                external_sync=False,
            )

    def save_account(self, auth, body, id=None):
        patch_existing = id is not None
        doc = body.document.model_dump(mode="json")
        s = self.settings
        id = (
            uid(id)
            if id
            else stable(institution(s), doc["provider"], doc["external_account_id"])
        )
        with self.tx(auth, True) as (c, actor):
            digest, old = replay(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.account",
                id,
                body.model_dump(mode="json"),
            )
            if old:
                return old
            current = one(
                c,
                "SELECT * FROM crm_ads9.Account WHERE InstitutionId=? AND AccountId=?",
                institution(s),
                id,
            )
            if patch_existing and not current:
                raise HTTPException(404, "ads_capture_unavailable")
            if (
                current
                and current["Revision"] != body.revision
                or not current
                and body.revision
            ):
                raise HTTPException(409, "revision_conflict")
            if current and (
                current["Provider"] != doc["provider"]
                or current["ExternalId"] != doc["external_account_id"]
            ):
                raise HTTPException(409, "ads_account_identity_immutable")
            if doc["integration_id"]:
                native = one(
                    c,
                    "SELECT Provider,Channel FROM crm_channels2.Integration WHERE InstitutionId=? AND IntegrationId=?",
                    institution(s),
                    doc["integration_id"],
                )
                if (
                    not native
                    or native["Provider"] != doc["provider"]
                    or native["Channel"]
                    not in {"facebook", "messenger", "instagram", "tiktok"}
                ):
                    raise HTTPException(409, "ads_account_channel_mismatch")
                if (
                    current
                    and str(current["IntegrationId"] or "").lower()
                    != doc["integration_id"]
                    and c.execute(
                        "SELECT 1 FROM crm_ads9.Intake WHERE InstitutionId=? AND AccountId=?",
                        institution(s),
                        id,
                    ).fetchone()
                ):
                    raise HTTPException(409, "ads_account_binding_in_use")
            elif (
                current
                and current["IntegrationId"]
                and c.execute(
                    "SELECT 1 FROM crm_ads9.Intake WHERE InstitutionId=? AND AccountId=?",
                    institution(s),
                    id,
                ).fetchone()
            ):
                raise HTTPException(409, "ads_account_binding_in_use")
            program(c, s, doc["program_id"])
            doc["initial_stage_key"] = stage(c, doc).key
            if current:
                c.execute(
                    "UPDATE crm_ads9.Account SET State=?,IntegrationId=?,Document=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND AccountId=?",
                    doc["status"],
                    doc["integration_id"],
                    packed(doc),
                    institution(s),
                    id,
                )
            else:
                if (
                    c.execute(
                        "SELECT COUNT(*) FROM crm_ads9.Account WHERE InstitutionId=?",
                        institution(s),
                    ).fetchval()
                    >= 200
                ):
                    raise HTTPException(413, "ads_account_limit")
                c.execute(
                    "INSERT crm_ads9.Account(InstitutionId,AccountId,Provider,ExternalId,IntegrationId,State,Revision,Document) VALUES(?,?,?,?,?,?,1,?)",
                    institution(s),
                    id,
                    doc["provider"],
                    doc["external_account_id"],
                    doc["integration_id"],
                    doc["status"],
                    packed(doc),
                )
            event(c, s, id, actor, "account_saved", dict(revision=body.revision + 1))
            result = public(c, s, account(c, s, id), "account")
            record_operation(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.account",
                id,
                digest,
                result,
            )
            return result

    def save_campaign(self, auth, body, id=None):
        s = self.settings
        patch_existing = id is not None
        doc = body.document.model_dump(mode="json")
        id = (
            uid(id)
            if id
            else stable(institution(s), doc["account_id"], doc["external_campaign_id"])
        )
        with self.tx(auth, True) as (c, actor):
            digest, old = replay(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.campaign",
                id,
                body.model_dump(mode="json"),
            )
            if old:
                return old
            a = account(c, s, doc["account_id"])
            same_channel(a, doc["channel"])
            current = one(
                c,
                "SELECT * FROM crm_ads9.Campaign WHERE InstitutionId=? AND CampaignId=?",
                institution(s),
                id,
            )
            if patch_existing and not current:
                raise HTTPException(404, "ads_capture_unavailable")
            if (
                current
                and current["Revision"] != body.revision
                or not current
                and body.revision
            ):
                raise HTTPException(409, "revision_conflict")
            if current and (
                uid(str(current["AccountId"])) != doc["account_id"]
                or current["ExternalId"] != doc["external_campaign_id"]
            ):
                raise HTTPException(409, "ads_campaign_identity_immutable")
            if current:
                c.execute(
                    "UPDATE crm_ads9.Campaign SET Document=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND CampaignId=?",
                    packed(doc),
                    institution(s),
                    id,
                )
            else:
                c.execute(
                    "INSERT crm_ads9.Campaign(InstitutionId,CampaignId,AccountId,ExternalId,Revision,Document) VALUES(?,?,?,?,1,?)",
                    institution(s),
                    id,
                    doc["account_id"],
                    doc["external_campaign_id"],
                    packed(doc),
                )
            event(
                c,
                s,
                a["AccountId"],
                actor,
                "campaign_saved",
                dict(campaign_id=id, budget_is_recorded_only=True),
            )
            result = public(c, s, get(c, s, id, "campaign"), "campaign")
            record_operation(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.campaign",
                id,
                digest,
                result,
            )
            return result

    def import_intake(self, auth, body, kind, id=None):
        patch_existing = id is not None
        doc = body.document.model_dump(mode="json")
        s = self.settings
        id = (
            uid(id)
            if id
            else stable(
                institution(s),
                doc["account_id"],
                kind,
                doc["channel"],
                doc["external_id"],
            )
        )
        with self.tx(auth, True) as (c, actor):
            digest, old = replay(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9." + kind,
                id,
                body.model_dump(mode="json"),
            )
            if old:
                return old
            a = account(c, s, doc["account_id"])
            current = one(
                c,
                "SELECT * FROM crm_ads9.Intake WHERE InstitutionId=? AND IntakeId=?",
                institution(s),
                id,
            )
            if patch_existing and not current:
                raise HTTPException(404, "ads_capture_unavailable")
            if current:
                if (
                    uid(str(current["AccountId"])) != doc["account_id"]
                    or current["Kind"] != kind
                    or current["Channel"] != doc["channel"]
                    or current["ExternalId"] != doc["external_id"]
                ):
                    raise HTTPException(409, "ads_capture_identity_immutable")
                if body.revision:
                    if current["Revision"] != body.revision:
                        raise HTTPException(409, "revision_conflict")
                    if not current["IdentityId"] and doc["status"] == "converted":
                        raise HTTPException(409, "ads_convert_requires_review")
                    program(c, s, doc["program_id"])
                    c.execute(
                        "UPDATE crm_ads9.Intake SET State=?,ProgramId=?,Document=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND IntakeId=?",
                        doc["status"],
                        doc["program_id"],
                        packed(doc),
                        institution(s),
                        id,
                    )
                    event(
                        c,
                        s,
                        a["AccountId"],
                        actor,
                        "capture_updated",
                        dict(kind=kind),
                        intake=id,
                    )
            else:
                if body.revision:
                    raise HTTPException(409, "revision_conflict")
                self.insert_intake(c, actor, a, kind, id, doc)
            current = get(c, s, id, "intake")
            if body.create_conversation:
                convert(c, s, auth, actor, current, a)
            result = public(c, s, get(c, s, id, "intake"), "intake")
            record_operation(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9." + kind,
                id,
                digest,
                result,
            )
            return result

    def insert_intake(
        self, c, actor, a, kind, id, doc, *, receipt=None, origin="operator"
    ):
        s = self.settings
        same_channel(a, doc["channel"])
        if a["State"] != "connected":
            raise HTTPException(409, "ads_account_paused")
        doc = dict(doc)
        if doc["status"] == "converted":
            raise HTTPException(422, "ads_convert_requires_review")
        if doc["program_id"] is None:
            doc["program_id"] = json.loads(a["Document"])["program_id"]
        program(c, s, doc["program_id"])
        campaign = (
            one(
                c,
                "SELECT CampaignId FROM crm_ads9.Campaign WHERE InstitutionId=? AND AccountId=? AND ExternalId=?",
                institution(s),
                a["AccountId"],
                doc["external_campaign_id"],
            )
            if doc["external_campaign_id"]
            else None
        )
        social = (
            one(
                c,
                "SELECT CommentId FROM crm_channels2.SocialComment WHERE InstitutionId=? AND IntegrationId=? AND ExternalId=?",
                institution(s),
                a["IntegrationId"],
                doc["external_id"],
            )
            if kind == "comment" and a["IntegrationId"]
            else None
        )
        captured = (
            datetime.fromisoformat(doc["captured_at"].replace("Z", "+00:00"))
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
            if doc["captured_at"]
            else clock()
        )
        c.execute(
            "INSERT crm_ads9.Intake(InstitutionId,IntakeId,AccountId,Kind,Channel,ExternalId,CampaignId,SocialCommentId,ReceiptId,Origin,State,Revision,ProgramId,Document,CapturedAt) VALUES(?,?,?,?,?,?,?,?,?,?,?,1,?,?,?)",
            institution(s),
            id,
            a["AccountId"],
            kind,
            doc["channel"],
            doc["external_id"],
            campaign["CampaignId"] if campaign else None,
            social["CommentId"] if social else None,
            receipt,
            origin,
            doc["status"],
            doc["program_id"],
            packed(doc),
            captured,
        )
        event(
            c,
            s,
            a["AccountId"],
            actor,
            "capture_imported",
            dict(kind=kind, origin=origin),
            intake=id,
        )

    def to_inbox(self, auth, id, body, kind=None):
        s = self.settings
        with self.tx(auth, True) as (c, actor):
            digest, old = replay(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.convert",
                id,
                body.model_dump(mode="json"),
            )
            if old:
                return old
            row = get(c, s, id, "intake")
            if kind and row["Kind"] != kind:
                raise HTTPException(404, "ads_record_not_found")
            if body.revision != row["Revision"]:
                raise HTTPException(409, "revision_conflict")
            result = convert(c, s, auth, actor, row, account(c, s, row["AccountId"]))
            record_operation(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.convert",
                id,
                digest,
                result,
            )
            return result

    def credential(self, auth, id, body):
        s = self.settings
        raw = body.value.get_secret_value() if body.value else None
        with self.tx(auth, True, True) as (c, actor):
            authorize(c, s, auth, "settings.channels.write", recent=True)
            payload = body.model_dump(mode="json")
            payload["value"] = raw
            digest, old = replay(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.credential",
                id,
                payload,
            )
            if old:
                return old
            a = account(c, s, id)
            if a["Revision"] != body.revision:
                raise HTTPException(409, "revision_conflict")
            secret = None
            if raw:
                secret = str(uuid4())
                version = c.execute(
                    "SELECT ISNULL(MAX(VersionNo),0)+1 FROM crm_ads9.Secret WHERE InstitutionId=? AND AccountId=?",
                    institution(s),
                    id,
                ).fetchval()
                binding = dict(
                    institution=institution(s),
                    scope="ads9",
                    owner=id,
                    kind="access_token",
                    version=version,
                    secret_id=secret,
                )
                nonce, cipher = seal(key(s), binding, raw)
                c.execute(
                    "INSERT crm_ads9.Secret(InstitutionId,SecretId,AccountId,VersionNo,Kind,KeyId,Nonce,Ciphertext,ActorId) VALUES(?,?,?,?,'access_token',?,?,?,?)",
                    institution(s),
                    secret,
                    id,
                    version,
                    hashlib.sha256(key(s)).hexdigest()[:32],
                    nonce,
                    cipher,
                    actor["UserId"],
                )
            c.execute(
                "UPDATE crm_ads9.Account SET SecretId=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND AccountId=?",
                secret,
                institution(s),
                id,
            )
            event(
                c,
                s,
                id,
                actor,
                "credential_stored" if raw else "credential_revoked",
                dict(provider_verified=False),
            )
            result = dict(
                stored=bool(raw), provider_verified=False, revision=a["Revision"] + 1
            )
            record_operation(
                c,
                s,
                actor["UserId"],
                str(body.operation_id),
                "ads9.credential",
                id,
                digest,
                result,
            )
            return result

    def comment_link(self, c, integration, external, author):
        values = rows(
            c,
            "SELECT DISTINCT i.ContactId,i.ConversationId FROM crm_ads9.Intake t JOIN crm_ads9.Account a ON a.InstitutionId=t.InstitutionId AND a.AccountId=t.AccountId JOIN crm_ads9.Identity i ON i.InstitutionId=t.InstitutionId AND i.AccountId=t.AccountId AND i.IdentityId=t.IdentityId WHERE t.InstitutionId=? AND a.IntegrationId=? AND ((t.Kind='comment' AND t.ExternalId=?) OR (JSON_VALUE(t.Document,'$.author_id')=? AND ?<>''))",
            institution(self.settings),
            integration,
            external,
            author,
            author,
        )
        links = {
            (primary(c, uid(str(v["ContactId"]))), uid(str(v["ConversationId"])))
            for v in values
        }
        if len(links) > 1:
            raise HTTPException(409, "ads_comment_link_ambiguous")
        if not links:
            return None
        contact, conversation = next(iter(links))
        if not conversation_matches(c, conversation, contact):
            raise HTTPException(409, "ads_conversation_link_changed")
        historical = uid(
            str(
                c.execute(
                    "SELECT ContactId FROM crm.Conversation WHERE ConversationId=?",
                    conversation,
                ).fetchval()
            )
        )
        return dict(contact_id=historical, conversation_id=conversation)

    def history(self, auth, id, offset=0):
        with self.tx(auth) as (c, _):
            account(c, self.settings, id)
            data = rows(
                c,
                "SELECT * FROM crm_ads9.Event WHERE InstitutionId=? AND AccountId=? ORDER BY CreatedAt DESC,EventId OFFSET ? ROWS FETCH NEXT 51 ROWS ONLY",
                institution(self.settings),
                id,
                offset,
            )
            return dict(
                items=[
                    dict(
                        id=uid(str(v["EventId"])),
                        kind=v["Kind"],
                        at=utc(v["CreatedAt"]),
                        document=json.loads(v["Document"]),
                    )
                    for v in data[:50]
                ],
                has_more=len(data) > 50,
            )
