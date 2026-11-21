"""SQL-owned admissions context, memory and fenced asynchronous replies."""

import asyncio
import hashlib
import json
import re
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from app.modules.ai.infrastructure.providers import AiError
from app.modules.ai.infrastructure.openrouter import OpenRouterClient
from app.modules.knowledge.service import search
from app.modules.catalog.infrastructure.institutional_context import read_context, programs, plain
from .admissions_prompt import AdmissionsPolicy, assemble_prompt, requests_human, validate_reply


def packed(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def literal_program(question, name):
    words = list(re.finditer(r"[^\W_]+", question))
    wanted = plain(name).split()
    for index in range(len(words) - len(wanted) + 1):
        if [plain(word.group()) for word in words[index:index + len(wanted)]] == wanted:
            return question[words[index].start():words[index + len(wanted) - 1].end()][:240]
    return ""


def declared_availability(question):
    # Store only a bounded explicit availability clause, not a transcript.
    marker = r"(?:mi\s+(?:disponibilidad(?:\s+horaria)?|horario)(?:\s+para\s+estudiar)?(?:\s+(?:ahora|cambi[oó]))?(?:\s+es)?|(?:ahora\s+)?(?:solo\s+)?puedo\s+(?:estudiar|asistir)|estoy\s+disponible)"
    found = None
    for match in re.finditer(r"\b" + marker + r"\s*[:=]?\s*(.{1,240}?)(?=[!?;\n](?:\s|$)|\.(?!\s*m\.)(?:\s|$)|$)", question, re.I):
        value = match.group(1).strip()
        end = match.end()
        if re.search(r"\b[ap]\.\s*m$", value, re.I) and question[end:end + 1] == ".":
            value += "."
            end += 1
        if len(value) > 240:
            continue
        normalized = plain(value)
        if not re.search(r"\b(?:lunes|martes|miercoles|jueves|viernes|sabado|sabados|domingo|domingos|semana|manana|tarde|noche|noches|horas?|pm|am)\b|\d", normalized):
            continue
        if re.search(r"@|https?://|\d{7,}", value, re.I) or re.search(r"\b(?:telefono|cedula|documento|correo|nombre)\b", normalized):
            continue
        if re.search(r"\bno\s*$", question[max(0, match.start() - 12):match.start()], re.I):
            continue
        found = {"value": value, "quote": question[match.start():end].strip()[:320]}
    return found


def installed(cursor):
    if not cursor.execute("SELECT OBJECT_ID(N'crm_ai.AdmissionsPolicy')").fetchval():
        raise AiError("admissions_schema_required", 503)


def policy_row(cursor):
    installed(cursor)
    row = cursor.execute("SELECT Revision,Enabled,ActivationSequence,KnowledgeRevision,Document FROM crm_ai.AdmissionsPolicy WHERE PolicyId=1").fetchone()
    return {"revision": row[0], "enabled": bool(row[1]), "activation_sequence": row[2], "knowledge_revision": row[3], "settings": AdmissionsPolicy.model_validate_json(row[4]).model_dump()}


def memory_row(cursor, conversation_id, create=False):
    if not cursor.execute("SELECT 1 FROM crm.Conversation WHERE ConversationId=?", conversation_id).fetchone():
        raise AiError("conversation_not_found", 404)
    if create:
        cursor.execute("IF NOT EXISTS(SELECT 1 FROM crm_ai.ProspectMemory WHERE ConversationId=?) INSERT crm_ai.ProspectMemory(ConversationId) VALUES(?)", conversation_id, conversation_id)
    row = cursor.execute("SELECT Revision,Generation,BaselineSequence,Document FROM crm_ai.ProspectMemory WHERE ConversationId=?", conversation_id).fetchone()
    return {"revision": row[0], "generation": row[1], "baseline_sequence": row[2], "facts": json.loads(row[3])} if row else {"revision": 0, "generation": 0, "baseline_sequence": 0, "facts": {}}


def history_rows(cursor, conversation_id, baseline, through=None, identity_id=None):
    rows = cursor.execute("SELECT TOP(12) m.MessageId,m.Body,m.Direction,m.Sequence FROM crm.Message m "
        "JOIN crm_channels.MessageRoute r ON r.MessageId=m.MessageId "
        "LEFT JOIN crm_channels.outbound_queue q ON q.QueueId=r.QueueId "
        "WHERE m.ConversationId=? AND m.Sequence>? AND (? IS NULL OR m.Sequence<=?) "
        "AND (? IS NULL OR r.IdentityId=?) AND ((m.Direction='incoming' AND r.ActorKind='external') "
        "OR (m.Direction='outgoing' AND q.State IN('sent','delivered','read'))) ORDER BY m.Sequence DESC", conversation_id, baseline, through, through, identity_id, identity_id).fetchall()
    return [{"id": str(r[0]), "text": r[1], "role": "user" if r[2] == "incoming" else "assistant", "sequence": r[3]} for r in reversed(rows)]


class AdmissionsService:
    def __init__(self, application):
        self.application = application
        self.ai = application.state.ai_service
        self.store = getattr(self.ai.repository, "store", None)

    @contextmanager
    def transaction(self, write=False):
        if self.store is None:
            raise AiError("local_sql_copy_required", 503)
        with self.store.transaction(write) as cursor:
            lock = cursor.execute("DECLARE @r int; EXEC @r=sys.sp_getapplock @Resource=N'crm.local.commit',@LockMode=?,@LockOwner='Transaction',@LockTimeout=3000; SELECT @r", "Exclusive" if write else "Shared").fetchone()
            if not lock or lock[0] < 0:
                raise AiError("admissions_storage_busy", 503)
            yield cursor

    def settings(self):
        with self.transaction() as cursor:
            value = policy_row(cursor)
        snapshot = self.ai.connection_snapshot()
        return {**value, "openrouter_configured": any(p["id"] == "openrouter" and p["configured"] for p in snapshot["providers"]), "global_ai_enabled": self.ai.repository.read().settings.enabled, "outbound_enabled": self.ai.outbound, "retrieval": "sql_lexical_index"}

    def save_settings(self, request):
        policy = request.settings
        if ".." in policy.primary_model or ".." in policy.fallback_model or (policy.fallback_model and policy.fallback_model == policy.primary_model):
            raise AiError("invalid_model_id")
        self.ai.refresh_credentials()
        if request.enabled and (not policy.primary_model or not self.ai.gateway.keys.get("openrouter") or not self.ai.repository.read().settings.enabled or not self.ai.outbound):
            raise AiError("admissions_activation_requires_openrouter_and_global_gates", 409)
        with self.transaction(True) as cursor:
            current = policy_row(cursor)
            if current["revision"] != request.revision:
                raise AiError("admissions_revision_conflict", 409)
            watermark = cursor.execute("SELECT COALESCE(MAX(Sequence),0) FROM crm.Message").fetchval()
            activation = watermark if request.enabled and not current["enabled"] else current["activation_sequence"]
            cursor.execute("UPDATE crm_ai.AdmissionsPolicy SET Revision=Revision+1,Enabled=?,ActivationSequence=?,Document=?,UpdatedAt=SYSUTCDATETIME() WHERE PolicyId=1", request.enabled, activation, policy.model_dump_json())
            # Previously generated replies must not survive a policy change.
            cursor.execute("UPDATE q SET State='failed',LastError='admissions_policy_changed',LeaseId=NULL FROM crm_channels.outbound_queue q JOIN crm_ai.ResponseJob j ON j.ResponseMessageId=q.MessageId JOIN crm_channels.MessageRoute r ON r.QueueId=q.QueueId WHERE r.StartedAt IS NULL AND q.State IN('queued','sending')")
        return self.settings()

    def memory(self, conversation_id):
        with self.transaction() as cursor:
            installed(cursor)
            return memory_row(cursor, conversation_id)

    def reset(self, conversation_id, revision):
        with self.transaction(True) as cursor:
            installed(cursor)
            current = memory_row(cursor, conversation_id, True)
            if current["revision"] != revision:
                raise AiError("memory_revision_conflict", 409)
            baseline = cursor.execute("SELECT COALESCE(MAX(Sequence),0) FROM crm.Message WHERE ConversationId=?", conversation_id).fetchval()
            cursor.execute("UPDATE crm_ai.ProspectMemory SET Document='{}',Revision=Revision+1,Generation=Generation+1,BaselineSequence=?,UpdatedAt=SYSUTCDATETIME() WHERE ConversationId=?", baseline, conversation_id)
            cursor.execute("UPDATE crm_ai.ResponseJob SET State='cancelled',LeaseId=NULL,LastError='memory_reset' WHERE ConversationId=? AND State IN('queued','processing')", conversation_id)
            cursor.execute("UPDATE q SET State='failed',LastError='memory_reset',LeaseId=NULL FROM crm_channels.outbound_queue q JOIN crm_ai.ResponseJob j ON j.ResponseMessageId=q.MessageId JOIN crm_channels.MessageRoute r ON r.QueueId=q.QueueId WHERE j.ConversationId=? AND r.StartedAt IS NULL AND q.State IN('queued','sending')", conversation_id)
            return memory_row(cursor, conversation_id)

    @staticmethod
    def sources(cursor, question, program_id=None, semester=None):
        from app.institutional.cbn_profile import reviewed_sources
        institutional = read_context(cursor, question, program_id, semester)
        documents = [{**s, "source_kind": "document"} for s in search(cursor, question, limit=2)]
        return institutional, reviewed_sources([*institutional["sources"], *documents])

    def academic_programs(self, offset=0, limit=150):
        with self.transaction() as cursor:
            return programs(cursor, offset, limit)

    def context(self, conversation_id, question, program_id=None, semester=None):
        with self.transaction() as cursor:
            policy = policy_row(cursor)
            memory = memory_row(cursor, conversation_id)
            history = history_rows(cursor, conversation_id, memory["baseline_sequence"])
            institutional, sources = self.sources(cursor, question, program_id, semester)
            messages = assemble_prompt(AdmissionsPolicy(**policy["settings"]), question, memory["facts"], sources, history)
            return {"messages": messages, "sources": sources, "institutional": institutional, "memory": memory, "policy_revision": policy["revision"], "knowledge_revision": policy["knowledge_revision"], "network_called": False}

    @staticmethod
    def preview_scope(conversation_id, binding, model):
        return ":admissions:" + hashlib.sha256(packed([conversation_id, *binding, model]).encode()).hexdigest()

    def preview_model(self, selected):
        current = self.ai.repository.read()
        model = selected or current.settings.model
        if selected and model not in self.ai.catalogs.get(current.settings.provider, {}):
            raise AiError("model_catalog_required", 409)
        return model

    def preview_session(self, conversation_id, selected_model="", question="", program_id=None, semester=None):
        model = self.preview_model(selected_model)
        with self.transaction() as cursor:
            policy = policy_row(cursor)
            memory = memory_row(cursor, conversation_id)
            institutional, _ = self.sources(cursor, question, program_id, semester)
            binding = (policy["revision"], policy["knowledge_revision"], memory["generation"], memory["revision"], institutional["fingerprint"])
        return self.ai.create_conversation(scope=self.preview_scope(conversation_id, binding, model))

    async def preview(self, conversation_id, request):
        if request.attachment or request.search or request.history:
            raise AiError("admissions_preview_text_only")
        model = self.preview_model(request.preview_model)
        with self.transaction() as cursor:
            policy = policy_row(cursor)
            memory = memory_row(cursor, conversation_id)
            institutional, sources = self.sources(cursor, request.prompt, request.program_id, request.semester)
            # Manual preview sends only selected declarative memory and published
            # sources, never private operator notes or the CRM identity profile.
            messages = assemble_prompt(AdmissionsPolicy(**policy["settings"]), request.prompt, memory["facts"], sources, [], structured=False)
            binding = (policy["revision"], policy["knowledge_revision"], memory["generation"], memory["revision"], institutional["fingerprint"])
        def guard():
            with self.transaction() as cursor:
                latest_policy = policy_row(cursor)
                latest_memory = memory_row(cursor, conversation_id)
                current_sql = read_context(cursor, request.prompt, request.program_id, request.semester)
                if binding != (latest_policy["revision"], latest_policy["knowledge_revision"], latest_memory["generation"], latest_memory["revision"], current_sql["fingerprint"]):
                    raise AiError("admissions_snapshot_obsolete", 409)
                global_state = cursor.execute("SELECT c.Revision,x.Revision,x.Outbound,c.Document FROM crm_ai.Configuration c CROSS JOIN crm_ai.Connection x WHERE c.ConfigurationId=1 AND x.ConnectionId=1").fetchone()
                if not global_state or (global_state[0], global_state[1]) != (request.revision, request.credential_revision) or not global_state[2] or not json.loads(global_state[3]).get("enabled"):
                    raise AiError("conversation_configuration_changed", 409)

        result = await self.ai.media_chat(request, institutional_messages=messages, institutional_guard=guard, conversation_scope=self.preview_scope(conversation_id, binding, model), generation_model=model)
        guard()
        return {**result, "admissions_sources": [{"id": s["id"], "title": s["title"], "page": s["page"], "source_kind": s.get("source_kind", "document")} for s in sources], "institutional": institutional, "knowledge_missing": not sources, "documents_missing": not any(s.get("source_kind") == "document" for s in sources), "crm_written": False, "inbox_delivered": False, "voice_provider": self.ai.repository.read().settings.media.voice_provider}

    def assistant_sources(self, cursor, question, remembered):
        context = dict(remembered)
        catalog = programs(cursor, 0, 300)
        availability = declared_availability(question)
        selection_text = question.replace(availability["quote"], "", 1) if availability else question
        normalized = " " + plain(selection_text) + " "
        named = [p for p in catalog["items"] if " " + plain(p["name"]) + " " in normalized]
        correction = re.split(r"\b(?:prefiero|corrijo|cambio a|ahora quiero)\b", plain(selection_text))[-1] if re.search(r"\bjornada\b", plain(selection_text)) else ""
        schedules = {p["schedule"] for p in catalog["items"] if p["schedule"] and " " + plain(p["schedule"]) + " " in " " + correction + " "}
        if named and schedules:
            named = [p for p in named if p["schedule"] in schedules]
        declaration = re.search(r"(?:^|[.;!\n]\s*)(?:ahora\s+)?(?:me interesa|quiero estudiar|deseo estudiar|mi programa(?: de inter[eé]s)? es)\s+(?!saber\b|conocer\b|recordar\b)", question, re.I)
        withdrawal = bool(re.search(r"\b(?:no me interesa|no quiero estudiar|descarta el programa|olvida (?:el|mi) programa)\b", plain(question)))
        change_intent = re.search(r"(?:^|[.;!\n]\s*)(?:ahora\s+)?(?:(?:quiero|deseo) cambiar(?:me)? de (?:programa|carrera)|cambio de (?:programa|carrera)|prefiero (?:el programa|la carrera))\b", question, re.I)
        identifier = context["program_id"]
        if withdrawal:
            identifier = None
        elif named:
            same_reference = (
                identifier in {p["program_id"] for p in named}
                and len({plain(p["name"]) for p in named}) == 1
                and not (declaration or change_intent or schedules)
                and not re.search(r"\b(?:jornada|comparar|compara|comparacion|diferencias?|ambas|ambos)\b", plain(selection_text))
            )
            identifier = identifier if same_reference else named[0]["program_id"] if len(named) == 1 and not catalog["has_more"] else None
        elif schedules and identifier:
            previous = next((p for p in catalog["items"] if p["program_id"] == identifier), None)
            variants = [p for p in catalog["items"] if previous and p["name"] == previous["name"] and p["schedule"] in schedules]
            identifier = variants[0]["program_id"] if len(variants) == 1 else None
        elif change_intent or declaration and not re.search(r"\b(?:ese|este|mismo|esa|esta)\b", plain(question)):
            identifier = None
        previous = next((p for p in catalog["items"] if p["program_id"] == context["program_id"]), None)
        current = next((p for p in catalog["items"] if p["program_id"] == identifier), None)
        if withdrawal or identifier != context["program_id"] and not (previous and current and previous["name"] == current["name"]):
            context.update(program_interest="", program_evidence="")
        # Explicit current ambiguity/withdrawal must not reselect the old offer.
        lookup = "Consulta la oferta vigente y solicita selección de programa y jornada." if withdrawal or named and identifier is None else selection_text
        institutional, sources = self.sources(cursor, lookup, identifier)
        selected = institutional["selected_program"]
        context["program_id"] = selected["program_id"] if selected else None
        evidence = literal_program(question, selected["name"]) if selected else ""
        if declaration and evidence and not withdrawal:
            context.update(program_interest=selected["name"][:240], program_evidence=evidence)
        if availability:
            context.update(schedule_availability=availability["value"], schedule_evidence=availability["quote"])
        elif re.search(r"\b(?:olvida mi (?:disponibilidad|horario)|ya no puedo estudiar|no estoy disponible|ya no tengo disponibilidad)\b", plain(question)):
            context.update(schedule_availability="", schedule_evidence="")
        return institutional, sources, context, lookup

    async def assistant_media_chat(self, request):
        assistant_settings = self.ai.repository.read().settings
        session_binding = self.ai.media_binding()
        remembered = self.ai.ledger.admissions_context(request.conversation_id, session_binding)
        with self.transaction() as cursor:
            policy = policy_row(cursor)
            institutional, sources, context, lookup = self.assistant_sources(cursor, request.prompt, remembered)
            memory = {}
            if context["program_interest"]:
                memory["program_interest"] = {"value": context["program_interest"], "quote": context["program_evidence"], "authority": "user_declared"}
            if context["schedule_availability"]:
                memory["schedule_availability"] = {"value": context["schedule_availability"], "quote": context["schedule_evidence"], "authority": "user_declared_not_institutional_hours"}
            history = [{"id": "assistant-history:" + str(index), "role": item.role, "text": item.content} for index, item in enumerate(request.history)]
            messages = assemble_prompt(AdmissionsPolicy(**policy["settings"]), request.prompt or "Orienta sobre el contenido del adjunto sin inventar hechos institucionales.", memory, sources, history, structured=False)
            messages[0]["content"] += "\nLa memoria de esta sesión contiene sólo declaraciones del usuario. Una corrección explícita actual reemplaza la anterior. La disponibilidad personal no confirma el horario oficial de clases. Una etiqueta de jornada como NOCTURNA no especifica días ni horas oficiales: no afirmes ni niegues compatibilidad con la disponibilidad personal sin fuentes que detallen esos días y horas. Si solicita recordar sus datos, responde únicamente los hechos declarados recordados; no agregues comparaciones, recomendaciones ni conclusiones sobre horarios. No vuelvas a preguntar programa/disponibilidad ya declarados."
            messages[0]["content"] += "\nPreferencias globales del propietario para el Asistente, subordinadas a la seguridad y fuentes institucionales anteriores:\n" + assistant_settings.system_prompt
            if assistant_settings.brief_responses:
                messages[0]["content"] += "\nPrefiere respuestas breves sin perder el contexto necesario."
            if sum(len(item["content"]) for item in messages) > 40000:
                raise AiError("admissions_context_limit", 413)
            binding = (policy["revision"], policy["knowledge_revision"], institutional["fingerprint"])
        def guard():
            if self.ai.ledger.admissions_context(request.conversation_id, session_binding) != remembered:
                raise AiError("conversation_context_changed", 409)
            with self.transaction() as cursor:
                latest = policy_row(cursor)
                sql = read_context(cursor, lookup, context["program_id"])
                state = cursor.execute("SELECT c.Revision,x.Revision,x.Outbound,c.Document FROM crm_ai.Configuration c CROSS JOIN crm_ai.Connection x WHERE c.ConfigurationId=1 AND x.ConnectionId=1").fetchone()
                if binding != (latest["revision"], latest["knowledge_revision"], sql["fingerprint"]) or not state or (state[0], state[1]) != (request.revision, request.credential_revision) or not state[2] or not json.loads(state[3]).get("enabled"):
                    raise AiError("admissions_snapshot_obsolete", 409)
        result = await self.ai.media_chat(request, institutional_messages=messages, institutional_guard=guard)
        guard()
        self.ai.ledger.save_admissions_context(request.conversation_id, session_binding, remembered, context)
        return {**result, "assistant_memory": memory, "institutional_sources": [{"id": s["id"], "title": s["title"], "page": s["page"], "source_kind": s.get("source_kind", "document")} for s in sources], "institutional_period": institutional["period"], "institutional_selection_required": institutional["selection_required"]}

    def snapshot(self, cursor, job):
        policy = policy_row(cursor)
        row = cursor.execute("SELECT c.ControlMode,c.State,k.Epoch,i.Channel,i.ExternalId,a.Revision,a.State,i.LastIncomingAt,m.Body,m.Sequence "
            "FROM crm.Conversation c WITH(UPDLOCK,HOLDLOCK) JOIN crm_channels.ConversationControl k ON k.ConversationId=c.ConversationId "
            "JOIN crm_channels.ExternalIdentity i ON i.ConversationId=c.ConversationId AND i.IdentityId=? "
            "JOIN crm_channels.Account a ON a.Channel=i.Channel JOIN crm.Message m ON m.ConversationId=c.ConversationId AND m.MessageId=? "
            "WHERE c.ConversationId=?", job[2], job[0], job[1]).fetchone()
        if not row or not policy["enabled"] or row[0] != "ai" or row[1] == "closed" or row[6] not in ("connected", "awaiting_webhook") or row[9] <= policy["activation_sequence"]:
            raise AiError("admissions_control_obsolete", 409)
        if not row[7] or (datetime.now(timezone.utc).replace(tzinfo=None) - row[7]).total_seconds() > (172800 if row[3] == "tiktok" else 86400):
            raise AiError("admissions_channel_window_expired", 409)
        memory = memory_row(cursor, str(job[1]), True)
        if row[9] <= memory["baseline_sequence"]:
            raise AiError("memory_generation_obsolete", 409)
        config = cursor.execute("SELECT Revision,Document FROM crm_ai.Configuration WHERE ConfigurationId=1").fetchone()
        credential = cursor.execute("SELECT Revision,Outbound FROM crm_ai.Connection WHERE ConnectionId=1").fetchone()
        if not json.loads(config[1]).get("enabled") or not credential[1]:
            raise AiError("admissions_global_gate_closed", 409)
        latest = cursor.execute("SELECT COALESCE(MAX(Sequence),0) FROM crm.Message WHERE ConversationId=?", job[1]).fetchval()
        if latest != row[9]:
            raise AiError("admissions_input_superseded", 409)
        institutional, sources = self.sources(cursor, row[8])
        from app.modules.agents.service import managed_conversation, runtime_context

        selection = None
        if managed_conversation(cursor, str(job[1])):
            selection = runtime_context(cursor, str(job[1]), row[8], row[3])
            institutional, sources = selection["institutional"], selection["sources"]
            if row[9] <= selection["assignment"]["baseline_sequence"]:
                raise AiError("agents_input_before_assignment", 409)
        binding = [policy["revision"], policy["knowledge_revision"], row[2], row[5], config[0], credential[0], memory["generation"], memory["revision"], latest, institutional["fingerprint"]]
        if selection:
            binding.append(selection["binding"])
        return {"binding": binding, "policy": policy, "memory": memory, "institutional": institutional, "sources": sources, "channel": row[3], "target": row[4], "question": row[8], "sequence": row[9], "agent_selection": selection}

    def claim(self):
        with self.transaction(True) as cursor:
            policy = policy_row(cursor)
            if not policy["enabled"]:
                return None
            cursor.execute("UPDATE crm_ai.ResponseJob SET State='queued',LeaseId=NULL,LastError='interrupted_generation' WHERE State='processing' AND DueAt<SYSUTCDATETIME() AND Attempts<3")
            cursor.execute("UPDATE crm_ai.ResponseJob SET State='failed',LeaseId=NULL,LastError='generation_attempts_exhausted' WHERE State='processing' AND DueAt<SYSUTCDATETIME() AND Attempts>=3")
            lease = str(uuid4())
            row = cursor.execute(";WITH candidate AS(SELECT TOP(1) * FROM crm_ai.ResponseJob WITH(UPDLOCK,READPAST) WHERE State='queued' AND DueAt<=SYSUTCDATETIME() ORDER BY CreatedAt,MessageId) UPDATE candidate SET State='processing',LeaseId=?,Attempts=Attempts+1,DueAt=DATEADD(second,90,SYSUTCDATETIME()) OUTPUT inserted.MessageId,inserted.ConversationId,inserted.IdentityId,inserted.Attempts", lease).fetchone()
            return (*tuple(row), lease) if row else None

    def guard(self, job, binding):
        with self.transaction(True) as cursor:
            active = cursor.execute("SELECT 1 FROM crm_ai.ResponseJob WHERE MessageId=? AND LeaseId=? AND State='processing' AND DueAt>SYSUTCDATETIME()", job[0], job[4]).fetchone()
            if not active or self.snapshot(cursor, job)["binding"] != binding:
                raise AiError("admissions_snapshot_obsolete", 409)

    def finish(self, job, snapshot, reply=None, facts=None, result=None, reason=None):
        with self.transaction(True) as cursor:
            active = cursor.execute("SELECT 1 FROM crm_ai.ResponseJob WITH(UPDLOCK) WHERE MessageId=? AND LeaseId=? AND State='processing' AND DueAt>SYSUTCDATETIME()", job[0], job[4]).fetchone()
            if not active or self.snapshot(cursor, job)["binding"] != snapshot["binding"]:
                raise AiError("admissions_snapshot_obsolete", 409)
            if facts:
                selection = snapshot.get("agent_selection")
                if selection:
                    if selection["context"] and "customer_profile" in selection["configuration"].get("memories", ["customer_profile"]):
                        allowed = {"program_interest", "schedule_availability", "registration_reported"}
                        merged = {**{k: v for k, v in selection["facts"].items() if k in allowed}, **{k: v for k, v in facts.items() if k in allowed}}
                        cursor.execute("UPDATE crm_agents.Context SET MemoryJson=? WHERE ContextId=?", packed(merged), selection["context"]["id"])
                else:
                    merged = {**snapshot["memory"]["facts"], **facts}
                    cursor.execute("UPDATE crm_ai.ProspectMemory SET Document=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE ConversationId=?", packed(merged), job[1])
            if reason or reply.handoff:
                from app.modules.inbox.application.state import change_control

                change_control(cursor, str(job[1]), ("ai", "open"), ("human", "open"))
                cursor.execute("UPDATE crm.Conversation SET ControlMode='human',Priority=CASE WHEN Priority='urgent' THEN Priority ELSE 'high' END,Unread=1,UpdatedAt=SYSUTCDATETIME() WHERE ConversationId=?", job[1])
                task = str(uuid4())
                cursor.execute("INSERT crm_inbox.Task(TaskId,ConversationId,Title,HumanEmployeeId,Priority,Status) SELECT ?,c.ConversationId,N'Atención humana solicitada por el asistente',a.HumanEmployeeId,'high','pending' FROM crm.Conversation c LEFT JOIN crm_inbox.Assignment a ON a.ConversationId=c.ConversationId WHERE c.ConversationId=?", task, job[1])
                cursor.execute("UPDATE crm_ai.ResponseJob SET State='handoff',TaskId=?,LeaseId=NULL,LastError=? WHERE MessageId=?", task, reason or "answer_requires_advisor", job[0])
                cursor.execute("INSERT crm_channels.Audit(Channel,Action,EntityId) VALUES(?,'admissions_handoff',?)", snapshot["channel"], job[0])
                return
            message, queue = str(uuid4()), str(uuid4())
            references = [{"id": s["id"], "title": s["title"], "page": s["page"], "source_kind": s.get("source_kind", "document")} for s in result["sources"] if s["id"] in reply.references]
            citations = "\n\nFuentes: " + "; ".join(s["title"][:100] + (" (p. " + str(s["page"]) + ")" if s["page"] else "") for s in references)
            body = ("Asistente virtual de admisiones: " + reply.answer.strip())[:3000] + citations[:900]
            cursor.execute("INSERT crm.Message(MessageId,ConversationId,Body,Direction) VALUES(?,?,?,'outgoing')", message, job[1], body)
            cursor.execute("INSERT crm_channels.outbound_queue(QueueId,Channel,IdentityId,MessageId,Payload) VALUES(?,?,?,?,?)", queue, snapshot["channel"], job[2], message, packed({"kind": "message", "target": snapshot["target"], "body": body, "origin": "bot"}))
            cursor.execute("INSERT crm_channels.MessageRoute(MessageId,IdentityId,QueueId,ActorKind,ControlEpoch) VALUES(?,?,?,'bot',?)", message, job[2], queue, snapshot["binding"][2])
            selected = snapshot.get("agent_selection")
            summary = {k: selected[k] for k in ("agent_id", "version", "supervisor_id", "reason", "binding")} if selected else None
            cursor.execute("UPDATE crm_ai.ResponseJob SET State='completed',ResponseMessageId=?,Result=?,LeaseId=NULL WHERE MessageId=?", message, packed({"model": result["model"], "usage": result["usage"], "references": references, "binding": snapshot["binding"], "agent_selection": summary}), job[0])
            cursor.execute("UPDATE crm.Conversation SET UpdatedAt=SYSUTCDATETIME() WHERE ConversationId=?", job[1])
            cursor.execute("INSERT crm_channels.Audit(Channel,Action,EntityId) VALUES(?,'admissions_reply',?)", snapshot["channel"], message)

    async def process(self, job):
        snapshot = None
        result = None
        try:
            with self.transaction(True) as cursor:
                snapshot = self.snapshot(cursor, job)
                history = history_rows(
                    cursor,
                    str(job[1]),
                    snapshot["memory"]["baseline_sequence"],
                    snapshot["sequence"],
                    str(job[2]),
                )
                sources = snapshot["sources"]
                selection = snapshot.get("agent_selection")
                if selection:
                    # Do not replay text from another application/program context.
                    baseline = max(
                        selection["assignment"]["baseline_sequence"],
                        (selection["context"] or {}).get("baseline_sequence", 0),
                    )
                    history = history_rows(
                        cursor, str(job[1]), baseline, snapshot["sequence"], str(job[2])
                    )
                    if "short" not in selection["configuration"].get("memories", ["short"]):
                        history = [h for h in history if h["id"].lower() == str(job[0]).lower()]
            if (
                requests_human(snapshot["question"])
                or not sources
                or snapshot["question"].startswith("[")
            ):
                self.finish(
                    job,
                    snapshot,
                    reason="human_requested"
                    if requests_human(snapshot["question"])
                    else "knowledge_or_text_missing",
                )
                return
            credentials = self.ai.credentials.read()
            if (
                credentials.revision != snapshot["binding"][5]
                or not credentials.outbound
            ):
                raise AiError("credential_revision_conflict", 409)
            client = None
            if not selection:
                secret = credentials.keys.get("openrouter")
                key = (
                    secret.get_secret_value()
                    if secret
                    else self.ai.environment_keys.get("openrouter", "")
                )
                if not key:
                    self.finish(job, snapshot, reason="openrouter_key_missing")
                    return
                client = OpenRouterClient(key, self.ai.gateway.transport)
            policy = AdmissionsPolicy(**snapshot["policy"]["settings"])
            if selection:
                from app.modules.agents.service import policy_for

                policy = policy_for(selection)
            messages = assemble_prompt(
                policy,
                snapshot["question"],
                selection["facts"] if selection else snapshot["memory"]["facts"],
                sources,
                [h for h in history if h["id"].lower() != str(job[0]).lower()],
            )
            # Current message appears only once in the prompt; its id is supplied
            # as metadata so extracted memory can still cite its exact origin.
            messages[-1]["content"] = (
                "Mensaje entrante " + str(job[0]) + ":\n" + snapshot["question"][:4000]
            )
            if selection:
                from app.modules.agents.generation import require_provider

                require_provider(self.ai, selection["configuration"])
                self.guard(job, snapshot["binding"])
                with self.transaction(True) as cursor:
                    self.application.state.agents.reserve(
                        cursor, str(job[0]), selection, messages
                    )
            if selection:
                from app.modules.agents.generation import complete

                result = await complete(
                    self.ai,
                    selection,
                    policy,
                    messages,
                    lambda: self.guard(job, snapshot["binding"]),
                )
            else:
                result = await client.complete(
                    policy, messages, lambda: self.guard(job, snapshot["binding"])
                )
            reply, facts = validate_reply(result["content"], sources, history, response_metadata=result.get("response_metadata"))
            if selection:
                self.application.state.agents.settle(str(job[0]), result["usage"], result)
            self.finish(job, snapshot, reply, facts, {**result, "sources": sources})
        except AiError as error:
            if snapshot and snapshot.get("agent_selection"):
                execution = result or getattr(error, "agent_execution", None)
                self.application.state.agents.settle(str(job[0]), usage=(execution or {}).get("usage"), result=execution, error=error.code)
            if snapshot and error.status != 409:
                try:
                    self.finish(job, snapshot, reason=error.code)
                    return
                except AiError:
                    pass
            with self.transaction(True) as cursor:
                cursor.execute(
                    "UPDATE crm_ai.ResponseJob SET State='cancelled',LastError=?,LeaseId=NULL WHERE MessageId=? AND LeaseId=? AND State='processing'",
                    error.code,
                    job[0],
                    job[4],
                )


class AdmissionsWorker:
    def __init__(self, service):
        self.service, self.stopped = service, threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True, name="admissions-ai")
        self.thread.start()

    def stop(self):
        self.stopped.set()
        if self.thread:
            self.thread.join(timeout=45)

    def run(self):
        while not self.stopped.is_set():
            try:
                job = self.service.claim()
                if job:
                    asyncio.run(self.service.process(job))
            except Exception:
                # Durable leases retain retry ownership. Never log prompts/keys.
                pass
            self.stopped.wait(2)


def validate_dispatch(cursor, queue_id, account_revision):
    """Persisted generation frontier, checked immediately before provider POST."""
    if not cursor.execute("SELECT OBJECT_ID(N'crm_ai.ResponseJob')").fetchval():
        return
    job = cursor.execute("SELECT j.Result,j.ConversationId,m.Body FROM crm_ai.ResponseJob j JOIN crm_channels.outbound_queue q ON q.MessageId=j.ResponseMessageId JOIN crm.Message m ON m.MessageId=j.MessageId WHERE q.QueueId=? AND j.State='completed'", queue_id).fetchone()
    if not job:
        return
    binding = json.loads(job[0]).get("binding", [])
    current = cursor.execute("SELECT p.Revision,p.KnowledgeRevision,p.Enabled,c.Revision,x.Revision,x.Outbound,m.Generation,c.Document "
        "FROM crm_ai.AdmissionsPolicy p CROSS JOIN crm_ai.Configuration c CROSS JOIN crm_ai.Connection x "
        "JOIN crm_ai.ProspectMemory m ON m.ConversationId=? WHERE p.PolicyId=1 AND c.ConfigurationId=1 AND x.ConnectionId=1", str(job[1])).fetchone()
    newer_input = cursor.execute("SELECT COALESCE(MAX(Sequence),0) FROM crm.Message WHERE ConversationId=? AND Direction='incoming'", str(job[1])).fetchval()
    from app.modules.agents.service import managed_conversation, runtime_context

    try:
        selected = None
        if managed_conversation(cursor, str(job[1])):
            channel = cursor.execute("SELECT Channel FROM crm_channels.outbound_queue WHERE QueueId=?", queue_id).fetchval()
            selected = runtime_context(cursor, str(job[1]), job[2], channel)
        sql = selected["institutional"] if selected else read_context(cursor, job[2])
        agent_changed = (len(binding) != 11 or binding[10] != selected["binding"]) if selected else len(binding) != 10
    except AiError:
        agent_changed, sql = True, {"fingerprint": None}
    if agent_changed or len(binding) < 10 or binding[9] != sql["fingerprint"] or not current or not current[2] or not current[5] or not json.loads(current[7]).get("enabled") or newer_input > binding[8] or [current[0], current[1], account_revision, current[3], current[4], current[6]] != [binding[i] for i in (0, 1, 3, 4, 5, 6)]:
        from app.modules.channels.providers import ProviderFailure

        raise ProviderFailure("admissions_generation_obsolete")
