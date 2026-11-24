"""Institutional authority and durable human-requested agent inference."""

import base64
import json
from contextlib import contextmanager
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.institutional.agent_ai import AgentAI
from app.institutional.agent_catalog import Catalog
from app.institutional.auth import authorize
from app.institutional.comment_ai import reserve_budget
from app.institutional.db import bound_hash, institution, one, rows, uid
from app.institutional.policy import request_authority
from app.institutional.settings import setting
from app.institutional.store import transaction
from app.modules.agents.domain import (
    AgentWrite,
    Configuration,
    ContextWrite,
    JsonUUID,
    SimulationRequest,
    chain_for,
    digest,
)
from app.modules.agents.runtime import reserve_cost
from app.modules.agents.service import (
    AgentsService,
    load,
    preflight,
    resolve_conversation,
)
from app.modules.ai.infrastructure.providers import AiError


class ContextCommand(ContextWrite):
    resource_conversation_id: JsonUUID


def invalidate(c, conversation=None):
    # Preserve the old B011 queues; this composition has only the C10 dispatcher.
    suffix = " AND ConversationId=?" if conversation else ""
    c.execute(
        (
            "UPDATE crm_agents5.Request SET State='"
            "cancelled',ErrorCode='agents_context_c"
            "hanged' WHERE State='running'"
        )
        + suffix,
        *((conversation,) if conversation else ()),
    )
    if conversation:
        from app.institutional.whatsapp_gemini import ACTOR

        c.execute(
            "UPDATE crm_channels2.ProviderOperation SET Status='abandoned',"
            "ResultCode='agents_context_changed',CompletedAt=SYSUTCDATETIME() "
            "WHERE ActorRef=? AND Status='pending' AND OperationId IN ("
            "SELECT q.OperationId FROM crm_channels2.SendJob q "
            "JOIN crm.Message m ON m.MessageId=q.MessageId "
            "WHERE m.ConversationId=? AND q.State='queued')",
            ACTOR,
            conversation,
        )
        c.execute(
            (
                "UPDATE q SET State='cancelled',LastErr"
                "orCode='agents_context_changed',Comple"
                "tedAt=SYSUTCDATETIME() FROM crm_channe"
                "ls2.SendJob q JOIN crm.Message m ON m."
                "MessageId=q.MessageId WHERE m.Conversa"
                "tionId=? AND q.State='queued'"
            ),
            conversation,
        )


def expire_requests(c):
    c.execute(
        (
            "UPDATE crm_agents5.Request SET State='"
            "uncertain',ErrorCode='agents_request_l"
            "ease_expired',CompletedAt=SYSUTCDATETI"
            "ME(),LeaseId=NULL,LeaseUntil=NULL WHER"
            "E State='running' AND LeaseUntil<=SYSU"
            "TCDATETIME()"
        )
    )
    c.execute(
        (
            "UPDATE u SET State='uncertain' FROM cr"
            "m_agents.Usage u JOIN crm_agents5.Requ"
            "est r ON r.RequestId=u.RequestId WHERE"
            " u.State='reserved' AND r.State IN('un"
            "certain','cancelled')"
        )
    )
    c.execute(
        (
            "UPDATE e SET State='uncertain',ErrorCo"
            "de='agents_request_uncertain',Finished"
            "At=SYSUTCDATETIME() FROM crm_agents.Ex"
            "ecution e JOIN crm_agents5.Request r O"
            "N r.RequestId=e.RequestId WHERE e.Stat"
            "e='reserved' AND r.State IN('uncertain"
            "','cancelled')"
        )
    )


class Agents(AgentsService):
    institutional = True

    def source_scope(self, key, request):
        if self.profile.ticket.get("version") in {
            "cbn-institutional-knowledge-p6-v1",
            "cbn-institutional-broadcast-p7-v1",
            "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
            raise AiError("knowledge_use_versioned_source_editor", 409)
        return super().source_scope(key, request)

    def __init__(self, application, settings, gateway_factory=None):
        self.application, self.profile = application, settings
        self.gateway_factory = gateway_factory
        self.ai = AgentAI(settings, gateway_factory)
        self.catalog_adapter = Catalog(settings)
        self.conversation_binding = None

    def catalog(self):
        value = super().catalog()
        return {
            **value,
            "authorization": "institutional_agents_manage",
            "academic_accuracy": "declared_CRM_not_verified_SIIE",
            "knowledge_reindex_available": False,
            "institutional": True,
            "knowledge_scope_editor": self.profile.ticket.get("version")
            in {
                "cbn-institutional-knowledge-p6-v1",
                "cbn-institutional-broadcast-p7-v1",
                "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'},
        }

    def supervision(self, offset):
        with self.transaction() as c:
            from app.institutional.db import rows
            from app.modules.agents.runtime import REPORTED_TOKENS_SQL

            records = rows(
                c,
                (
                    "SELECT RequestId,ConversationId,AgentI"
                    "d,State,ErrorCode,CreatedAt,Result FRO"
                    "M crm_agents5.Request WHERE Institutio"
                    "nId=? ORDER BY CreatedAt DESC,RequestI"
                    "d OFFSET ? ROWS FETCH NEXT 26 ROWS ONL"
                    "Y"
                ),
                institution(self.profile),
                offset,
            )
            usage = c.execute(
                (
                    "SELECT COUNT(*),COALESCE(SUM(CONVERT(b"
                    "igint,u.TokensReserved)),0),SUM("
                )
                + REPORTED_TOKENS_SQL
                + (
                    ") FROM crm_agents.Usage u LEFT JOIN cr"
                    "m_agents.Execution e ON e.RequestId=u."
                    "RequestId WHERE u.CreatedAt>=DATEFROMP"
                    "ARTS(YEAR(SYSUTCDATETIME()),MONTH(SYSU"
                    "TCDATETIME()),1)"
                )
            ).fetchone()
            return {
                "items": [
                    {
                        "message_id": uid(str(v["RequestId"])),
                        "conversation_id": uid(str(v["ConversationId"]))
                        if v["ConversationId"]
                        else None,
                        "state": v["State"],
                        "reason": v["ErrorCode"],
                        "created_at": str(v["CreatedAt"]),
                        "agent": {
                            "agent_id": uid(str(v["AgentId"])),
                            "version": json.loads(v["Result"] or "{}").get(
                                "config_version"
                            ),
                        },
                    }
                    for v in records[:25]
                ],
                "has_more": len(records) > 25,
                "usage": {
                    "requests": usage[0],
                    "tokens_reserved": usage[1],
                    "tokens_reported": usage[2],
                    "billing": "not_available",
                },
            }

    @contextmanager
    def transaction(self, write=False):
        authority = request_authority.get()
        if authority is None:
            raise HTTPException(401, "session_required")
        with transaction(self.profile, write, anonymous=True) as c:
            from app.institutional.conversation_scope import configure as configure_scope
            configure_scope(c, self.profile)
            actor = authorize(c, self.profile, authority, authority["permission"])
            if not setting(c, self.profile, "modules")["document"]["enabled"].get(
                "agents", False
            ):
                raise HTTPException(403, "module_disabled")
            if str(authority.get("resource", "")).endswith("/reindex"):
                raise AiError("knowledge_index_management_unavailable", 409)
            c.agent_actor = "u:" + base64.urlsafe_b64encode(
                UUID(actor["UserId"]).bytes
            ).decode().rstrip("=")
            c.agent_user, c.agent_session = actor["UserId"], actor["SessionId"]
            c.agent_catalog = self.catalog_adapter
            c.agent_budget_unlimited = setting(c, self.profile, "budgets")["document"].get("ai_budget_unlimited", False)
            from app.institutional.sales_context import configure as configure_sales
            configure_sales(c, self.profile)
            def validate_sales(config, previous):
                if config.auto_sales_crm and not previous.get("auto_sales_crm"):
                    authorize(c, self.profile, authority, "crm.write")
                    authorize(c, self.profile, authority, "inbox.write")
            c.agent_sales_profile = validate_sales
            from app.institutional.voice_audio import policy as voice_policy
            def validate_voice(chosen, previous):
                if chosen and chosen != previous and not any(
                    p.id == chosen and p.active for p in voice_policy(c, self.profile).profiles
                ):
                    raise AiError("voice_profile_unavailable", 409)
            c.agent_voice_profile = validate_voice
            from app.institutional.email_notifications import emit as emit_email
            c.agent_email_event = lambda event, resource: emit_email(c, self.profile, event, resource, module="agents")
            c.agent_invalidate = invalidate
            if self.profile.ticket.get("version") in {
                "cbn-institutional-knowledge-p6-v1",
                "cbn-institutional-broadcast-p7-v1",
                "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
                from app.institutional.knowledge import effective, enrich, search

                c.agent_conversation = (self.conversation_binding or {}).get("id")
                c.agent_knowledge = lambda question, selected, config: search(
                    c,
                    self.profile,
                    question,
                    selected.get("program_id"),
                    selected.get("stage_id"),
                    config["document_ids"],
                )
                def compose(selection, program, stage):
                    enrich(c, self.profile, selection, program, stage)
                    configured = setting(c, self.profile, "ai")
                    selection["configuration"] = {**selection["configuration"], "instructions":
                        configured["document"].get("system_prompt", "") + "\n" + selection["configuration"]["instructions"]}
                    selection["binding"] = digest([selection["binding"], configured["revision"]])
                c.agent_composition = compose
                c.agent_memory = lambda selection, conversation: effective(
                    c, self.profile, selection, conversation or c.agent_conversation
                )
            if self.conversation_binding:
                self.check_conversation(c, self.conversation_binding)
            yield c

    def check_conversation(self, c, binding):
        value = self.conversation_state(c, binding["id"])
        if (
            not value
            or value["State"] == "closed"
            or digest(value) != binding["digest"]
        ):
            raise AiError("agents_conversation_control_changed", 409)

    @staticmethod
    def conversation_state(c, conversation):
        value = one(
            c,
            (
                "SELECT v.ControlMode,v.State,COALESCE("
                "ctrl.Epoch,0) AS Epoch,(SELECT COALESC"
                "E(MAX(Sequence),0) FROM crm.Message m "
                "WHERE m.ConversationId=v.ConversationI"
                "d) AS Sequence FROM crm.Conversation v"
                " LEFT JOIN crm_channels.ConversationCo"
                "ntrol ctrl ON ctrl.ConversationId=v.Co"
                "nversationId WHERE v.ConversationId=?"
            ),
            conversation,
        )
        return value

    async def draft_conversation(self, conversation, body):
        with self.transaction() as c:
            selected = resolve_conversation(c, conversation, body.channel, for_draft=True)
            state = self.conversation_state(c, conversation)
            if selected["assignment"]["revision"] != body.revision:
                raise AiError("agents_revision_conflict", 409)
            context = selected["context"] or selected.get("commercial_interest") or {}
            request = SimulationRequest(
                agent_id=selected["agent_id"],
                config_version=selected["version"],
                program_id=context.get("program_id"),
                stage_id=context.get("stage_id"),
                question=body.question,
                history=[{"role": "user" if v["Direction"] == "incoming" else "assistant", "content": v["Body"][:1600]}
                    for v in reversed(rows(c,
                        "SELECT TOP(12) Direction,Body FROM crm.Message WHERE ConversationId=? ORDER BY Sequence DESC", conversation))],
                channel=body.channel,
                request_id=body.request_id,
                call_provider=body.call_provider,
                acknowledge_consumption=body.acknowledge_consumption,
            )
            binding = {
                "id": conversation,
                "epoch": state["Epoch"],
                "digest": digest(state),
            }
        result = await self.simulate(request, conversation_binding=binding)
        return {
            **result,
            "messages": None,
            "automatic_send": False,
            "requires_human_review": True,
            "control_epoch": state["Epoch"],
        }

    def save_context(self, conversation_id, key, request):
        if request.applicant_id is not None or request.period_id is not None:
            raise AiError("agents_academic_mapping_required", 409)
        command = ContextCommand(
            **request.model_dump(), resource_conversation_id=conversation_id
        )
        return super().save_context(conversation_id, key, command)

    def reserve(self, c, request_id, selection, messages):
        if selection["configuration"]["primary_model"] == "cbn-demo-unconfigured":
            raise AiError("agents_demo_model_not_connected", 409)
        super().reserve(c, request_id, selection, messages)
        row = c.execute(
            ("SELECT TokensReserved FROM crm_agents.Usage WHERE RequestId=?"),
            request_id,
        ).fetchval()
        cost = reserve_cost(selection["configuration"], row)
        if cost is None:
            raise AiError("agents_pricing_required", 409)
        budget = setting(c, self.profile, "budgets")["document"]
        # ponytail: daily institutional ceilings retain the conservative reservation;
        # add reconciliation only when measured throughput requires it.
        reserve_budget(c, self.profile, "tokens", row, budget["daily_tokens"])
        reserve_budget(
            c,
            self.profile,
            "usd",
            max(cost, 0.000001),
            budget["daily_usd_micros"] / 1_000_000,
        )

    def execute_action(self, c, action):
        authority = request_authority.get()
        actor = authorize(c, self.profile, authority, "inbox.write")
        conversation = uid(action["conversation_id"])
        if action["kind"] == "crm_note":
            authorize(c, self.profile, authority, "crm.write")
            if len(action["context"].encode("utf-16-le")) > 4000:
                raise AiError("agents_note_context_too_long", 422)
            contact = c.execute(
                ("SELECT ContactId FROM crm.Conversation WHERE ConversationId=?"),
                conversation,
            ).fetchval()
            c.execute(
                (
                    "INSERT crm_workspace.Note(NoteId,Conta"
                    "ctId,InstitutionId,AuthorId,Body) VALU"
                    "ES(?,?,?,?,?)"
                ),
                str(uuid4()),
                contact,
                institution(self.profile),
                actor["UserId"],
                action["context"],
            )
        else:
            if len(action["title"].encode("utf-16-le")) > 240:
                raise AiError("agents_task_title_too_long", 422)
            c.execute(
                (
                    "INSERT crm_workspace.Task(TaskId,Insti"
                    "tutionId,ConversationId,UserId,Title,S"
                    "tatus,Priority) VALUES(?,?,?, ?,?,'pen"
                    "ding',?)"
                ),
                str(uuid4()),
                institution(self.profile),
                conversation,
                actor["UserId"],
                action["title"],
                "high" if action["impact"] == "high" else "normal",
            )
        c.execute(
            ("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
        )

    def conversation(self, key):
        value = super().conversation(key)
        if value.get("selection"):
            selected = value["selection"]
            value["selection"] = {
                k: selected.get(k)
                for k in ["agent_id", "reason", "version", "supervisor_id"]
            }
        return value

    def restore_version(self, key, request):
        with self.transaction() as c:
            agents, _ = load(c)
            current = agents.get(key)
            if not current:
                raise AiError("agents_not_found", 404)
            body = AgentWrite(
                operation_id=request.operation_id,
                revision=request.revision,
                name=current["name"],
                level=current["level"],
                parent_id=current["parent_id"],
                program_id=current["program_id"],
                stage_id=current["stage_id"],
                configuration=Configuration.model_validate(current["configuration"]),
            )
        return self.save_agent(
            key, body, restore_version=request.version, restore_request=request
        )

    async def simulate(self, request, *, conversation_binding=None):
        if conversation_binding and request.provider_override:
            raise AiError("agents_simulation_route_only", 409)
        # Each paid request has its own gateway and usage metadata. A concurrent
        # metadata request cannot replace the first request's gateway.
        runtime = Agents(self.application, self.profile, self.gateway_factory)
        runtime.conversation_binding = conversation_binding
        return await runtime.execute(request)

    async def execute(self, request):
        if not request.call_provider:
            return await super().simulate(request)
        operation, lease = uid(str(request.request_id)), str(uuid4())
        digest_value = bound_hash(
            self.profile,
            [request.model_dump(mode="json"), self.conversation_binding],
            "agent-request",
        )
        with self.transaction(True) as c:
            expire_requests(c)
            agents, stages = load(c)
            selected = agents.get(str(request.agent_id))
            if not selected:
                raise AiError("agents_not_found", 404)
            if selected["version"] != request.config_version:
                raise AiError("agents_revision_conflict", 409)
            if any(
                v["state"] != "active" or not v["enabled"]
                for v in chain_for(selected, agents)
            ):
                raise AiError("agents_parent_or_agent_unavailable", 409)
            checked = preflight(c, selected, agents, stages)
            if not checked["ready"]:
                raise AiError(checked["checks"][0], 409)
            previous = one(
                c,
                (
                    "SELECT * FROM crm_agents5.Request WHER"
                    "E InstitutionId=? AND RequestId=?"
                ),
                institution(self.profile),
                operation,
            )
            knowledge_binding = None
            if self.profile.ticket.get("version") in {
                "cbn-institutional-knowledge-p6-v1",
                "cbn-institutional-broadcast-p7-v1",
                "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
                from app.institutional.knowledge import freshness

                knowledge_binding = freshness(
                    c, self.profile, (self.conversation_binding or {}).get("id")
                )
            if previous:
                if (
                    bytes(previous["PayloadHash"]) != digest_value
                    or uid(str(previous["ActorId"])) != c.agent_user
                ):
                    raise AiError("agents_operation_conflict", 409)
                if previous["State"] == "confirmed":
                    if (
                        knowledge_binding is not None
                        and bytes(previous["BindingHash"] or b"") != knowledge_binding
                    ):
                        raise AiError("agents_knowledge_context_changed", 409)
                    return json.loads(previous["Result"])
                raise AiError(previous["ErrorCode"] or "agents_request_uncertain", 409)
            c.execute(
                (
                    "INSERT crm_agents5.Request(Institution"
                    "Id,RequestId,ActorId,SessionId,AgentId"
                    ",ConversationId,Epoch,Kind,PayloadHash"
                    ",State,LeaseId,LeaseUntil) VALUES(?,?,"
                    "?,?,?,?,?,? ,?,'running',?,DATEADD(min"
                    "ute,5,SYSUTCDATETIME()))"
                ),
                institution(self.profile),
                operation,
                c.agent_user,
                c.agent_session,
                str(request.agent_id),
                (self.conversation_binding or {}).get("id"),
                (self.conversation_binding or {}).get("epoch"),
                "conversation_draft" if self.conversation_binding else "simulation",
                digest_value,
                lease,
            )
            if knowledge_binding is not None:
                c.execute(
                    (
                        "UPDATE crm_agents5.Request SET Binding"
                        "Hash=? WHERE InstitutionId=? AND Reque"
                        "stId=?"
                    ),
                    knowledge_binding,
                    institution(self.profile),
                    operation,
                )
        result, failure = None, None
        try:
            with self.transaction() as c:
                agents, stages = load(c)
                selected = agents.get(str(request.agent_id))
                if not selected or any(
                    v["state"] != "active" or not v["enabled"]
                    for v in chain_for(selected, agents)
                ):
                    raise AiError("agents_parent_or_agent_unavailable", 409)
            result = await super().simulate(request)
        except BaseException as error:
            failure = error
        # Internal settlement owns this exact lease; it does not grant a revoked
        # actor access to the result and never initiates another provider call.
        with transaction(self.profile, True, anonymous=True) as c:
            try:
                authority = request_authority.get()
                authorize(c, self.profile, authority, authority["permission"])
                if not setting(c, self.profile, "modules")["document"]["enabled"].get(
                    "agents", False
                ):
                    raise HTTPException(403, "module_disabled")
                if self.conversation_binding:
                    self.check_conversation(c, self.conversation_binding)
                if knowledge_binding is not None:
                    from app.institutional.knowledge import freshness

                    if (
                        freshness(
                            c, self.profile, (self.conversation_binding or {}).get("id")
                        )
                        != knowledge_binding
                    ):
                        raise AiError("agents_knowledge_context_changed", 409)
            except (HTTPException, AiError) as error:
                failure = error
            state = "confirmed" if failure is None else "uncertain"
            code = getattr(failure, "code", None) or (
                "agents_authority_or_result_changed" if failure else None
            )
            if isinstance(failure, AiError) and failure.status < 500:
                state = "failed"
            c.execute(
                (
                    "UPDATE crm_agents5.Request SET State=?"
                    ",Result=?,ErrorCode=?,CompletedAt=SYSU"
                    "TCDATETIME(),LeaseId=NULL,LeaseUntil=N"
                    "ULL WHERE InstitutionId=? AND RequestI"
                    "d=? AND State='running' AND LeaseId=? "
                    "AND LeaseUntil>SYSUTCDATETIME()"
                ),
                state,
                json.dumps(result if state == "confirmed" else {}, ensure_ascii=False),
                code,
                institution(self.profile),
                operation,
                lease,
            )
            if c.rowcount != 1:
                failure = AiError("agents_request_uncertain", 409)
            elif failure is None or isinstance(failure, AiError) and failure.status >= 500:
                from app.institutional.email_notifications import observe_service
                observe_service(c, self.profile, "agent-provider", failed=failure is not None)
        if failure:
            raise failure
        return result
