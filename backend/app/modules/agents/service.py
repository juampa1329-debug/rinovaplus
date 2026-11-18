"""Local SQL agent lifecycle and context. The existing AI runtime owns transport."""

import json
import logging
from datetime import date

from pydantic import Field

from app.modules.agents.domain import (
    Configuration,
    chain_for,
    digest,
    effective_configuration,
    resolve,
    validate_hierarchy,
)
from app.modules.agents.generation import (
    complete,
    provider_options,
    require_provider,
    validate_selection,
)
from app.modules.ai.application.admissions_prompt import (
    AdmissionsPolicy,
    assemble_prompt,
    validate_reply,
)
from app.modules.ai.infrastructure.providers import AiError
from app.modules.catalog.infrastructure.institutional_context import (
    programs as academic_programs,
    read_context as academic_context,
)
from app.modules.inbox.application.state import change_control


def programs(cursor, *args, **kwargs):
    adapter = getattr(cursor, "agent_catalog", None)
    return (
        adapter.programs(cursor, *args, **kwargs)
        if adapter
        else academic_programs(cursor, *args, **kwargs)
    )


def read_context(cursor, *args, **kwargs):
    adapter = getattr(cursor, "agent_catalog", None)
    return (
        adapter.read_context(cursor, *args, **kwargs)
        if adapter
        else academic_context(cursor, *args, **kwargs)
    )


def packed(value):
    return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))


def source_proof(sources):
    """Retrieval timestamps describe an observation, not a source revision."""
    return digest(
        [
            {key: value for key, value in source.items() if key != "retrieved_at"}
            for source in sources
        ]
    )


def identifier(value):
    return str(value).lower() if value is not None else None


def installed(cursor):
    if getattr(cursor, "dialect", None) == "postgresql":
        return cursor.native("SELECT to_regclass(%s)", "rinovaplus_crm.crmagenteperfil").fetchval() is not None
    return (
        cursor.execute("SELECT OBJECT_ID(N'crm_agents.Profile')").fetchval() is not None
    )


def require_schema(cursor):
    if not installed(cursor):
        raise AiError("agents_migration_required", 503)


def managed_conversation(cursor, conversation_id):
    return installed(cursor) and bool(
        cursor.execute(
            (
                "SELECT 1 FROM crm_agents.Assignment WHERE ConversationId=? UNION "
                "ALL SELECT 1 FROM crm_agents.Context WHERE ConversationId=?"
            ),
            conversation_id,
            conversation_id,
        ).fetchone()
    )


def load(cursor):
    require_schema(cursor)
    rows = cursor.execute(
        (
            "SELECT "
            "p.AgentId,a.Name,p.Level,p.ParentId,p.ProgramId,p.StageId,p.State,p.Vers"
            "ion,p.ApprovedVersion,p.Document,a.Enabled,p.Revision FROM crm_agents.Pr"
            "ofile p JOIN crm_inbox.Agent a ON a.AgentId=p.AgentId ORDER BY p.Level,a"
            ".Name,p.AgentId"
        )
    ).fetchall()
    agents = {}
    for row in rows:
        item = dict(
            zip(
                (
                    "id",
                    "name",
                    "level",
                    "parent_id",
                    "program_id",
                    "stage_id",
                    "state",
                    "version",
                    "approved_version",
                    "configuration",
                    "enabled",
                    "revision",
                ),
                row,
                strict=True,
            )
        )
        for key in ("id", "parent_id", "stage_id"):
            item[key] = identifier(item[key])
        item["configuration"] = json.loads(item["configuration"])
        item["enabled"] = bool(item["enabled"])
        agents[item["id"]] = item
    stages = {}
    for row in cursor.execute(
        (
            "SELECT "
            "StageId,ProgramId,Name,EntryRule,ExitRule,EvidenceRequired,Revision,Appr"
            "ovedRevision FROM crm_agents.Stage ORDER BY ProgramId,Name"
        )
    ).fetchall():
        item = dict(
            zip(
                (
                    "id",
                    "program_id",
                    "name",
                    "entry_rule",
                    "exit_rule",
                    "evidence_required",
                    "revision",
                    "approved_revision",
                ),
                row,
                strict=True,
            )
        )
        item["id"] = identifier(item["id"])
        item["approved"] = item["revision"] == item["approved_revision"]
        stages[item["id"]] = item
    return agents, stages


def check_program(cursor, program_id):
    if program_id is not None:
        read_context(cursor, "", program_id)


def check_available_scope(agent, agents):
    if agent["state"] == "archived":
        return
    for other in agents.values():
        if (
            other["id"] == agent["id"]
            or other["state"] == "archived"
            or other["level"] != agent["level"]
        ):
            continue
        if (
            agent["level"] == "guide"
            or agent["level"] == "program"
            and other["program_id"] == agent["program_id"]
            or agent["level"] == "stage"
            and other["stage_id"] == agent["stage_id"]
        ):
            raise AiError("agents_" + agent["level"] + "_scope_occupied", 409)


def replay(cursor, kind, key, request):
    document = request.model_dump(mode="json")
    if "configuration" in request.model_fields_set:
        # Additive defaults must not change the fingerprint of a legacy request.
        for field in (
            "provider",
            "description",
            "operating_style",
            "risk_posture",
            "escalation_policy",
            "instruction_template",
            "template_variables",
            "customized",
            "route",
            "global_enabled",
            "fallback_provider",
            "monthly_usd_limit",
            "usage_alert_percent",
            "hard_stop",
            "input_usd_per_million",
            "output_usd_per_million",
            "fallback_input_usd_per_million",
            "fallback_output_usd_per_million",
            "ab_enabled",
            "ab_variant",
            "ab_compare_version",
            "ab_traffic_percent",
            "industry_policies",
            "memories",
            "require_human_approval",
            "allow_safe_actions",
            "allow_crm_update",
        ):
            if field not in request.configuration.model_fields_set:
                document["configuration"].pop(field, None)
    payload = digest([kind, key, document])
    row = cursor.execute(
        "SELECT PayloadHash"
        + (",Actor" if isinstance(getattr(cursor, "agent_actor", None), str) else "")
        + " FROM crm_agents.History WHERE OperationId=?",
        str(request.operation_id),
    ).fetchone()
    if row and (
        row[0] != payload
        or isinstance(getattr(cursor, "agent_actor", None), str)
        and row[1] != cursor.agent_actor
    ):
        raise AiError("agents_operation_conflict", 409)
    return bool(row), payload


def history(cursor, kind, key, request, payload, document):
    if isinstance(getattr(cursor, "agent_actor", None), str):
        cursor.execute(
            "INSERT crm_agents.History(OperationId,EntityId,Kind,PayloadHash,Document,Note,Actor) VALUES(?,?,?,?,?,?,?)",
            str(request.operation_id),
            key,
            kind,
            payload,
            packed(document),
            getattr(request, "note", getattr(request, "evidence", "")),
            cursor.agent_actor,
        )
        return
    cursor.execute(
        (
            "INSERT "
            "crm_agents.History(OperationId,EntityId,Kind,PayloadHash,Document,Note) "
            "VALUES(?,?,?,?,?,?)"
        ),
        str(request.operation_id),
        key,
        kind,
        payload,
        packed(document),
        getattr(request, "note", getattr(request, "evidence", "")),
    )


def invalidate(cursor, conversation_id=None):
    if getattr(cursor, "agent_invalidate", None):
        cursor.agent_invalidate(cursor, conversation_id)
        return
    suffix = " AND j.ConversationId=?" if conversation_id else ""
    args = (conversation_id,) if conversation_id else ()
    cursor.execute(
        (
            "UPDATE q SET "
            "State='failed',LastError='agents_context_changed',LeaseId=NULL FROM "
            "crm_channels.outbound_queue q JOIN crm_ai.ResponseJob j ON "
            "j.ResponseMessageId=q.MessageId JOIN crm_channels.MessageRoute r ON "
            "r.QueueId=q.QueueId WHERE r.StartedAt IS NULL AND q.State "
            "IN('queued','sending')"
        )
        + suffix,
        *args,
    )


def source_rows(cursor):
    return [
        {
            "id": identifier(r[0]),
            "title": r[1],
            "state": r[2],
            "revision": r[3],
            "program_id": r[4],
            "stage_id": identifier(r[5]),
            "owner": r[6],
            "valid_until": str(r[7]) if r[7] else None,
            "scope_revision": r[8],
            "approved_document_revision": r[9],
        }
        for r in cursor.execute(
            (
                "SELECT "
                "d.DocumentId,d.Title,d.State,d.Revision,s.ProgramId,s.StageId,s.Owne"
                "r,s.ValidUntil,s.Revision,s.DocumentRevision FROM crm_ai.KnowledgeDo"
                "cument d LEFT JOIN crm_agents.SourceScope s ON s.DocumentId=d.Docume"
                "ntId WHERE d.State<>'deleted' ORDER BY d.Title"
            )
        ).fetchall()
    ]


def scoped_sources(cursor, question, selected, configuration):
    if getattr(cursor, "agent_knowledge", None):
        return cursor.agent_knowledge(question, selected, configuration)
    # SQL filters scope before reading bodies. An instruction/tag never grants scope.
    ids = list(dict.fromkeys(configuration["document_ids"]))
    if not ids:
        return []
    if "semantic" not in configuration.get("memories", ["semantic"]):
        marks = ",".join("?" for _ in ids)
        rows = cursor.execute(
            "SELECT TOP(2) c.ChunkId,c.DocumentId,d.Title,c.PageNumber,c.Body,d.Revision,s.Revision FROM crm_ai.KnowledgeChunk c JOIN crm_ai.KnowledgeDocument d ON d.DocumentId=c.DocumentId JOIN crm_agents.SourceScope s ON s.DocumentId=d.DocumentId WHERE d.State='published' AND d.DocumentId IN("
            + marks
            + ") AND s.ValidUntil>=CONVERT(date,SYSUTCDATETIME()) AND s.DocumentRevision=d.Revision AND (s.ProgramId IS NULL OR s.ProgramId=?) AND (s.StageId IS NULL OR s.StageId=?) ORDER BY c.DocumentId,c.Ordinal",
            *ids,
            selected.get("program_id"),
            selected.get("stage_id"),
        ).fetchall()
        return [
            {
                "id": identifier(r[0]),
                "document_id": identifier(r[1]),
                "title": r[2],
                "page": r[3],
                "text": r[4],
                "revision": r[5],
                "scope_revision": r[6],
                "source_kind": "document",
            }
            for r in rows
        ]
    from app.modules.knowledge.service import terms

    tokens = list(dict.fromkeys(terms(question)))[:24]
    if not tokens:
        return []
    placeholders = ",".join("?" for _ in ids)
    term_marks = ",".join("?" for _ in tokens)
    rows = cursor.execute(
        "SELECT TOP(2) c.ChunkId,c.DocumentId,d.Title,c.PageNumber,c.Body,"
        "d.Revision,s.Revision FROM crm_ai.KnowledgeChunk c "
        "JOIN crm_ai.KnowledgeDocument d ON d.DocumentId=c.DocumentId "
        "JOIN crm_agents.SourceScope s ON s.DocumentId=d.DocumentId "
        "JOIN crm_ai.KnowledgeTerm t ON t.ChunkId=c.ChunkId "
        f"WHERE d.State='published' AND d.DocumentId IN({placeholders}) "
        f"AND t.Term IN({term_marks}) "
        "AND s.ValidUntil>=CONVERT(date,SYSUTCDATETIME()) "
        "AND s.DocumentRevision=d.Revision "
        "AND (s.ProgramId IS NULL OR s.ProgramId=?) "
        "AND (s.StageId IS NULL OR s.StageId=?) GROUP BY "
        "c.ChunkId,c.DocumentId,d.Title,c.PageNumber,c.Body,"
        "d.Revision,s.Revision ORDER BY COUNT(*) DESC,c.ChunkId",
        *ids,
        *tokens,
        selected.get("program_id"),
        selected.get("stage_id"),
    ).fetchall()
    return [
        {
            "id": identifier(r[0]),
            "document_id": identifier(r[1]),
            "title": r[2],
            "page": r[3],
            "text": r[4],
            "revision": r[5],
            "scope_revision": r[6],
            "source_kind": "document",
        }
        for r in rows
    ]


def preflight(cursor, agent, agents, stages):
    problems = []
    try:
        validate_hierarchy(agent, agents, stages)
        check_program(cursor, agent["program_id"])
        config = effective_configuration(chain_for(agent, agents))
        if (
            not any(
                a["configuration"]["instructions"].strip()
                or not a["configuration"].get("customized", True)
                for a in chain_for(agent, agents)
            )
            or not config["primary_model"]
            or not config["channels"]
            or not config["monthly_token_limit"]
        ):
            problems.append("agents_incomplete_configuration")
        if agent["stage_id"] and not stages[agent["stage_id"]]["approved"]:
            problems.append("agents_stage_approval_required")
        scopes = (
            {s["id"]: s for s in source_rows(cursor)} if config["document_ids"] else {}
        )
        for doc_id in config["document_ids"]:
            source = scopes.get(doc_id)
            if (
                not source
                or source["state"] != "published"
                or source["approved_document_revision"] != source["revision"]
                or not source["owner"]
                or not source["valid_until"]
                or source["valid_until"] < date.today().isoformat()
                or source["program_id"] not in (None, agent["program_id"])
                or source["stage_id"] not in (None, agent["stage_id"])
            ):
                problems.append("agents_source_not_approved_for_scope")
        parents = chain_for(agent, agents)[:-1]
        if any(a["state"] != "active" or not a["enabled"] for a in parents):
            problems.append("agents_parent_or_agent_unavailable")
        if config["allow_reply"] and "conversation.reply" not in config["capabilities"]:
            problems.append("agents_reply_capability_required")
        policy_for({"configuration": config})
    except AiError as error:
        config = None
        problems.append(error.code)
    return {
        "ready": not problems,
        "checks": list(dict.fromkeys(problems)),
        "effective": config,
        "version": agent["version"],
        "academic_accuracy": "not_evaluated",
    }


def context_row(cursor, conversation_id, context_id):
    if not context_id:
        return None
    row = cursor.execute(
        (
            "SELECT "
            "ContextId,ProgramId,ApplicantId,PeriodId,StageId,Revision,StageRevision,"
            "BaselineSequence FROM crm_agents.Context WHERE ContextId=? AND Conversat"
            "ionId=?"
        ),
        context_id,
        conversation_id,
    ).fetchone()
    if not row:
        raise AiError("agents_context_not_in_conversation", 409)
    item = dict(
        zip(
            (
                "id",
                "program_id",
                "applicant_id",
                "period_id",
                "stage_id",
                "revision",
                "stage_revision",
                "baseline_sequence",
            ),
            row,
            strict=True,
        )
    )
    item["id"], item["stage_id"] = identifier(item["id"]), identifier(item["stage_id"])
    if item["applicant_id"]:
        if getattr(cursor, "agent_catalog", None):
            raise AiError("agents_academic_mapping_required", 409)
        actual = cursor.execute(
            (
                "SELECT o.Id_Programa FROM dbo.ACAspirante a JOIN "
                "dbo.ACProgramaOfrecido o ON o.Id_PrgOfrecido=a.Id_PrgOfrecido WHERE "
                "a.Id_Aspirante=? AND a.Id_Periodo=?"
            ),
            item["applicant_id"],
            item["period_id"],
        ).fetchone()
        if not actual or actual[0] != item["program_id"]:
            raise AiError("agents_application_scope_changed", 409)
    if item["stage_id"]:
        stage = cursor.execute(
            "SELECT Revision,ApprovedRevision FROM crm_agents.Stage WHERE StageId=?",
            item["stage_id"],
        ).fetchone()
        if not stage or stage[0] != stage[1] or stage[0] != item["stage_revision"]:
            raise AiError("agents_stage_approval_required", 409)
    return item


def resolve_conversation(cursor, conversation_id, channel, *, for_draft=False):
    agents, stages = load(cursor)
    conversation = cursor.execute(
        "SELECT ControlMode,State FROM crm.Conversation WHERE ConversationId=?",
        conversation_id,
    ).fetchone()
    if not conversation or conversation[1] == "closed":
        raise AiError("agents_conversation_unavailable", 409)
    row = cursor.execute(
        (
            "SELECT "
            "x.Mode,x.ContextId,x.Revision,x.BaselineSequence,a.AiAgentId,a.HumanEmpl"
            "oyeeId FROM crm_agents.Assignment x LEFT JOIN crm_inbox.Assignment a ON "
            "a.ConversationId=x.ConversationId WHERE x.ConversationId=?"
        ),
        conversation_id,
    ).fetchone()
    legacy = cursor.execute(
        "SELECT AiAgentId FROM crm_inbox.Assignment WHERE ConversationId=?",
        conversation_id,
    ).fetchone()
    if not row and legacy and legacy[0]:
        raise AiError("agents_legacy_assignment_requires_review", 409)
    assignment = {
        "mode": row[0] if row else "automatic",
        "context_id": identifier(row[1]) if row else None,
        "revision": row[2] if row else 0,
        "baseline_sequence": row[3] if row else 0,
        "agent_id": identifier(row[4]) if row else None,
        "human_employee_id": row[5] if row else None,
    }
    context = context_row(cursor, conversation_id, assignment["context_id"])
    draft_assignment = assignment
    if for_draft and assignment["mode"] == "human":
        draft_assignment = {**assignment, "mode": "automatic"}
    # Only the explicit draft endpoint may resolve under human control. It has
    # no send path and binds the result to the real, unchanged control epoch.
    resolution = resolve(agents, stages, draft_assignment, context, channel, "ai" if for_draft else conversation[0])
    selected = agents[resolution["agent_id"]]
    check = preflight(cursor, selected, agents, stages)
    if not check["ready"]:
        raise AiError(check["checks"][0], 409)
    resolution["context"] = context
    resolution["assignment"] = assignment
    return resolution


def runtime_context(cursor, conversation_id, question, channel):
    selection = resolve_conversation(cursor, conversation_id, channel)
    from app.modules.agents.runtime import experiment, scoped_memory

    selection = experiment(cursor, selection, load(cursor)[0], conversation_id)
    selection["conversation_id"] = conversation_id
    config = selection["configuration"]
    if not config["allow_reply"] or "conversation.reply" not in config["capabilities"]:
        raise AiError("agents_reply_not_allowed", 409)
    context = selection["context"]
    # An unconfirmed program never becomes confirmed by a keyword in a question.
    program_id = context["program_id"] if context else None
    institutional, sources = public_sources(
        cursor, question, program_id, context["stage_id"] if context else None, config
    )
    if getattr(cursor, "agent_composition", None):
        cursor.agent_composition(selection, program_id, context["stage_id"] if context else None)
    memory = {}
    if context and "customer_profile" in config["memories"] and not getattr(cursor, "agent_composition", None):
        row = cursor.execute(
            "SELECT MemoryJson FROM crm_agents.Context WHERE ContextId=?", context["id"]
        ).fetchone()
        memory = json.loads(row[0])
    selection["sources"] = sources
    selection["institutional"] = institutional
    selection["facts"] = {
        **memory,
        "operational_context": scoped_memory(cursor, selection, conversation_id),
    }
    selection["binding"] = digest(
        [
            selection["binding"],
            institutional["fingerprint"],
            [[s["id"], s.get("revision"), s.get("scope_revision")] for s in sources],
            selection["facts"],
        ]
    )
    return selection


def public_sources(cursor, question, program_id, stage_id, config):
    institutional = read_context(cursor, question if program_id or getattr(cursor, "agent_catalog", None) else "", program_id)
    documents = (
        scoped_sources(
            cursor, question, {"program_id": program_id, "stage_id": stage_id}, config
        )
        if "sources.read" in config["capabilities"]
        and set(config.get("memories", ["knowledge"])) & {"knowledge", "collective"}
        else []
    )
    return institutional, [
        *institutional["sources"],
        *documents,
    ] if "program.read" in config["capabilities"] and "vertical" in config.get(
        "memories", ["vertical"]
    ) else documents


class AgentPolicy(AdmissionsPolicy):
    system_prompt: str = Field(min_length=1)


def policy_for(selection):
    config = selection["configuration"]
    instructions = (
        config["instructions"]
        + "\nTono: "
        + config["tone"]
        + "\nObjetivos:\n"
        + "\n".join(config["objectives"])
        + "\nReglas heredadas:\n"
        + "\n".join(config["rules"])
    )
    instructions += (
        "\nPrograma y etapa sólo cambian por confirmación humana. No declares "
        "cambios institucionales."
    )
    instructions += "\nRuta operativa: " + config.get("route", "admissions")
    instructions += "\nPolíticas complementarias: " + ", ".join(
        config.get("industry_policies", ["academy"])
    )
    if selection.get("institution_dna"):
        instructions = (
            "ADN institucional revisado (subordinado a seguridad, privacidad y autoridad SIIE; "
            "no concede permisos ni confirma datos académicos):\n"
            + json.dumps([{"id":v["id"],"version":v["version"],"dna":v["content"]["dna"]} for v in selection["institution_dna"]], ensure_ascii=False)
            + "\nRestricciones del perfil del agente:\n" + instructions
        )
    if "privacy" in config.get("industry_policies", []):
        instructions += (
            "\nSolicita sólo datos mínimos y no reveles datos de otros aspirantes."
        )
    if "payments" in config.get("industry_policies", []):
        instructions += (
            "\nUn comprobante no acredita conciliación; deriva dudas de pago al asesor."
        )
    if "minors" in config.get("industry_policies", []):
        instructions += "\nConserva requisitos condicionados a minoría de edad; deriva dudas de representación."
    if config.get("route") == "analytics":
        instructions += "\nPrioriza indicadores agregados suministrados, sin inferir porcentajes ni identidades."
    elif config.get("route") == "followup":
        instructions += "\nPrioriza próximos pasos, sin afirmar seguimientos enviados o acciones no ejecutadas."
    elif config.get("route") == "institutional":
        instructions += "\nPrioriza orientación general y comparación de oferta, sin elegir programa por el aspirante."
    return AgentPolicy(
        primary_model=config["primary_model"],
        fallback_model=config["fallback_model"],
        max_tokens=config["max_tokens"],
        system_prompt=instructions,
    )


class AgentsService:
    def __init__(self, application):
        self.application = application
        self.admissions = application.state.admissions_ai
        self.ai = application.state.ai_service

    def transaction(self, write=False):
        if self.application.state.settings.mode != "local_sql_copy":
            raise AiError("local_sql_copy_required", 503)
        return self.admissions.transaction(write)

    def catalog(self):
        with self.transaction() as cursor:
            if not installed(cursor):
                return {"installed": False}
            agents, stages = load(cursor)
            catalog = programs(cursor, 0, 300)
            dimensions = (
                []
                if getattr(cursor, "agent_catalog", None)
                else cursor.execute(
                    "SELECT DISTINCT p.Id_Programa,p.Id_Escuela,e.NomEsla,"
                    "p.Id_Jornada,j.DetalleJornada FROM dbo.ACProgramaOfrecido o "
                    "JOIN dbo.ACProgramas p ON p.Id_Programa=o.Id_Programa "
                    "LEFT JOIN dbo.ACEscuela e ON e.Id_Escuela=p.Id_Escuela "
                    "LEFT JOIN dbo.ACJornada j ON j.Id_Jornada=p.Id_Jornada "
                    "WHERE o.Id_Periodo=?",
                    catalog["period"]["id"],
                ).fetchall()
            )
            by_program = {
                r[0]: {"school_id": r[1], "school": r[2], "schedule_id": r[3]}
                for r in dimensions
            }
            if getattr(cursor, "agent_catalog", None):
                by_program = {
                    v["program_id"]: {
                        "school_id": v["program_id"],
                        "school": v.get("school", ""),
                        "schedule_id": v["program_id"],
                    }
                    for v in catalog["items"]
                }
            catalog["items"] = [
                {**item, **by_program.get(item["program_id"], {})}
                for item in catalog["items"]
            ]
            legacy = [
                {"id": identifier(r[0]), "name": r[1]}
                for r in cursor.execute(
                    (
                        "SELECT a.AgentId,a.Name FROM crm_inbox.Agent a LEFT JOIN "
                        "crm_agents.Profile p ON p.AgentId=a.AgentId WHERE p.AgentId "
                        "IS NULL ORDER BY a.Name"
                    )
                ).fetchall()
            ]
            counts = {
                "total": len(agents),
                "active": sum(a["state"] == "active" for a in agents.values()),
                "programs": len(
                    {
                        a["program_id"]
                        for a in agents.values()
                        if a["level"] == "program" and a["state"] != "archived"
                    }
                ),
            }
            counts["pending_reviews"] = 0
            counts["paused"] = sum(a["state"] == "paused" for a in agents.values())
            return {
                "installed": True,
                "agents": list(agents.values()),
                "stages": list(stages.values()),
                "sources": source_rows(cursor),
                "programs": catalog,
                "legacy_agents": legacy,
                "counts": counts,
                "external_capabilities": False,
                "authorization": "local_operator_only",
                "academic_accuracy": "not_evaluated",
            }

    def save_agent(self, key, request, *, restore_version=None, restore_request=None):
        options = provider_options(self.ai)
        with self.transaction(True) as cursor:
            agents, stages = load(cursor)
            kind = (
                "agent_config"
                if restore_version is None
                else "agent_restore_" + str(restore_version)
            )
            repeated, payload = replay(cursor, kind, key, restore_request or request)
            if repeated:
                return {"confirmed": True, "replayed": True}
            old = agents.get(key)
            previous_configuration = old["configuration"] if old else None
            if restore_version is not None:
                from app.modules.agents.runtime import historical_profile

                if not old:
                    raise AiError("agents_not_found", 404)
                prior = historical_profile(cursor, old, restore_version)
                previous_configuration = prior["configuration"]
                request = request.model_copy(
                    update={
                        "configuration": Configuration.model_validate(
                            previous_configuration
                        )
                    }
                )
            if old and old["state"] == "archived":
                raise AiError("agents_archived_read_only", 409)
            if request.revision != (old["revision"] if old else 0):
                raise AiError("agents_revision_conflict", 409)
            if not request.name.strip():
                raise AiError("agents_name_required")
            check_program(cursor, request.program_id)
            item = {
                "id": key,
                "name": request.name.strip(),
                "level": request.level,
                "parent_id": identifier(request.parent_id),
                "program_id": request.program_id,
                "stage_id": identifier(request.stage_id),
                "state": "paused"
                if restore_version is not None or old and old["state"] == "paused"
                else "active",
                "version": old["version"] + 1 if old else 1,
                "revision": request.revision + 1,
                "approved_version": old["version"] + 1 if old else 1,
                "configuration": request.configuration.model_dump(mode="json"),
                "enabled": restore_version is None
                and (not old or old["state"] != "paused"),
            }
            validate_selection(item["configuration"], options, previous_configuration)
            if old and any(
                old[k] != item[k]
                for k in ("level", "parent_id", "program_id", "stage_id")
            ):
                raise AiError("agents_scope_immutable", 409)
            validate_hierarchy(item, agents, stages)
            check_available_scope(item, agents)
            updated = {**agents, key: item}
            check = preflight(cursor, item, updated, stages)
            if not check["ready"]:
                raise AiError(check["checks"][0], 409)
            from app.modules.agents.runtime import validate_experiment

            validate_experiment(cursor, item)
            for child in agents.values():
                if (
                    restore_version is None
                    and child["state"] == "active"
                    and key in [a["id"] for a in chain_for(child, updated)]
                ):
                    effective_configuration(chain_for(child, updated))
            if cursor.execute(
                "SELECT 1 FROM crm_inbox.Agent WHERE AgentId=?", key
            ).fetchone():
                cursor.execute(
                    "UPDATE crm_inbox.Agent SET Name=?,Enabled=? WHERE AgentId=?",
                    item["name"],
                    item["enabled"],
                    key,
                )
            else:
                cursor.execute(
                    (
                        "INSERT crm_inbox.Agent(AgentId,Name,Description,Enabled) "
                        "VALUES(?,?,?,?)"
                    ),
                    key,
                    item["name"],
                    "",
                    item["enabled"],
                )
            if old:
                cursor.execute(
                    (
                        "UPDATE crm_agents.Profile SET "
                        "Document=?,Version=Version+1,Revision=Revision+1,ApprovedVersion=Version+1,"
                        "State=?,UpdatedAt=SYSUTCDATETIME() WHERE AgentId=?"
                    ),
                    packed(item["configuration"]),
                    item["state"],
                    key,
                )
            else:
                cursor.execute(
                    (
                        "INSERT "
                        "crm_agents.Profile(AgentId,Level,ParentId,ProgramId,StageId,"
                        "Version,ApprovedVersion,State,Document) VALUES(?,?,?,?,?,1,1,'active',?)"
                    ),
                    key,
                    item["level"],
                    item["parent_id"],
                    item["program_id"],
                    item["stage_id"],
                    packed(item["configuration"]),
                )
            history(
                cursor,
                "agent_config",
                key,
                restore_request or request,
                payload,
                {**item, "restored_from_version": restore_version},
            )
            if not old and callable(getattr(cursor, "agent_email_event", None)):
                cursor.agent_email_event("agents.create", key)
            invalidate(cursor)
        return {"confirmed": True, "version": item["version"]}

    def review_agent(self, key, request, state=None):
        """Direct availability controls; profile approval is no longer required."""
        state = "active" if state is None else state
        with self.transaction(True) as cursor:
            agents, stages = load(cursor)
            repeated, payload = replay(cursor, "agent_state", key, request)
            if repeated:
                return {"confirmed": True, "replayed": True}
            item = agents.get(key)
            if not item or item["revision"] != request.revision:
                raise AiError("agents_revision_conflict", 409)
            if state in ("paused", "archived") and any(
                a["parent_id"] == key and a["state"] == "active"
                for a in agents.values()
            ):
                raise AiError("agents_active_children_require_pause", 409)
            check_available_scope({**item, "state": state}, agents)
            if state == "active":
                check = preflight(cursor, item, agents, stages)
                if not check["ready"]:
                    raise AiError(check["checks"][0], 409)
            cursor.execute(
                "UPDATE crm_agents.Profile SET State=?,ApprovedVersion=CASE WHEN ?='active' THEN Version ELSE ApprovedVersion END,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE AgentId=?",
                state,
                state,
                key,
            )
            cursor.execute(
                "UPDATE crm_inbox.Agent SET Enabled=? WHERE AgentId=?",
                state == "active",
                key,
            )
            history(
                cursor,
                "agent_state",
                key,
                request,
                payload,
                {"version": item["version"], "state": state},
            )
            invalidate(cursor)
        return {"confirmed": True}

    def save_stage(self, key, request):
        with self.transaction(True) as cursor:
            _, stages = load(cursor)
            repeated, payload = replay(cursor, "stage_config", key, request)
            if repeated:
                return {"confirmed": True, "replayed": True}
            old = stages.get(key)
            if (
                request.revision != (old["revision"] if old else 0)
                or old
                and old["program_id"] != request.program_id
            ):
                raise AiError("agents_revision_conflict", 409)
            if not all(
                value.strip()
                for value in (
                    request.name,
                    request.entry_rule,
                    request.exit_rule,
                    request.evidence_required,
                )
            ):
                raise AiError("agents_stage_conditions_required")
            check_program(cursor, request.program_id)
            if old:
                cursor.execute(
                    (
                        "UPDATE crm_agents.Stage SET "
                        "Name=?,EntryRule=?,ExitRule=?,EvidenceRequired=?,Revision=Re"
                        "vision+1,ApprovedRevision=NULL,ApprovedAt=NULL WHERE StageId"
                        "=?"
                    ),
                    request.name,
                    request.entry_rule,
                    request.exit_rule,
                    request.evidence_required,
                    key,
                )
            else:
                cursor.execute(
                    (
                        "INSERT "
                        "crm_agents.Stage(StageId,ProgramId,Name,EntryRule,ExitRule,E"
                        "videnceRequired,Revision) VALUES(?,?,?,?,?,?,1)"
                    ),
                    key,
                    request.program_id,
                    request.name,
                    request.entry_rule,
                    request.exit_rule,
                    request.evidence_required,
                )
            history(
                cursor,
                "stage_config",
                key,
                request,
                payload,
                request.model_dump(mode="json"),
            )
            invalidate(cursor)
            return {"confirmed": True}

    def approve_stage(self, key, request):
        if not request.confirmed or not request.note.strip():
            raise AiError("agents_human_confirmation_required", 409)
        with self.transaction(True) as cursor:
            require_schema(cursor)
            repeated, payload = replay(cursor, "stage_approval", key, request)
            if repeated:
                return {"confirmed": True, "replayed": True}
            cursor.execute(
                (
                    "UPDATE crm_agents.Stage SET "
                    "ApprovedRevision=Revision,ApprovedAt=SYSUTCDATETIME() WHERE "
                    "StageId=? AND Revision=?"
                ),
                key,
                request.revision,
            )
            if cursor.rowcount != 1:
                raise AiError("agents_revision_conflict", 409)
            history(
                cursor,
                "stage_approval",
                key,
                request,
                payload,
                {"revision": request.revision},
            )
            invalidate(cursor)
        return {"confirmed": True}

    def source_scope(self, key, request):
        if (
            not request.confirmed
            or not request.note.strip()
            or not request.owner.strip()
            or date.fromisoformat(request.valid_until) < date.today()
        ):
            raise AiError("agents_source_approval_required", 409)
        with self.transaction(True) as cursor:
            _, stages = load(cursor)
            repeated, payload = replay(cursor, "source_scope", key, request)
            if repeated:
                return {"confirmed": True, "replayed": True}
            check_program(cursor, request.program_id)
            stage = stages.get(identifier(request.stage_id))
            if request.stage_id and (
                not stage
                or stage["program_id"] != request.program_id
                or not stage["approved"]
            ):
                raise AiError("agents_stage_approval_required", 409)
            document = cursor.execute(
                (
                    "SELECT Revision FROM crm_ai.KnowledgeDocument WHERE "
                    "DocumentId=? AND State='published'"
                ),
                key,
            ).fetchone()
            if not document:
                raise AiError("agents_source_publication_required", 409)
            old = cursor.execute(
                "SELECT Revision FROM crm_agents.SourceScope WHERE DocumentId=?", key
            ).fetchone()
            if request.revision != (old[0] if old else 0):
                raise AiError("agents_revision_conflict", 409)
            if old:
                cursor.execute(
                    (
                        "UPDATE crm_agents.SourceScope SET "
                        "ProgramId=?,StageId=?,Owner=?,ValidUntil=?,Revision=Revision"
                        "+1,DocumentRevision=?,ApprovedAt=SYSUTCDATETIME() WHERE Docu"
                        "mentId=?"
                    ),
                    request.program_id,
                    identifier(request.stage_id),
                    request.owner,
                    request.valid_until,
                    document[0],
                    key,
                )
            else:
                cursor.execute(
                    (
                        "INSERT "
                        "crm_agents.SourceScope(DocumentId,ProgramId,StageId,Owner,Va"
                        "lidUntil,Revision,DocumentRevision) VALUES(?,?,?,?,?,1,?)"
                    ),
                    key,
                    request.program_id,
                    identifier(request.stage_id),
                    request.owner,
                    request.valid_until,
                    document[0],
                )
            history(
                cursor,
                "source_scope",
                key,
                request,
                payload,
                request.model_dump(mode="json"),
            )
            invalidate(cursor)
        return {"confirmed": True}

    def conversation(self, key):
        with self.transaction() as cursor:
            require_schema(cursor)
            if not cursor.execute(
                "SELECT 1 FROM crm.Conversation WHERE ConversationId=?", key
            ).fetchone():
                raise AiError("conversation_not_found", 404)
            row = cursor.execute(
                (
                    "SELECT Mode,ContextId,Revision,Reason FROM "
                    "crm_agents.Assignment WHERE ConversationId=?"
                ),
                key,
            ).fetchone()
            contexts = [
                {
                    "id": identifier(r[0]),
                    "program_id": r[1],
                    "applicant_id": r[2],
                    "period_id": r[3],
                    "stage_id": identifier(r[4]),
                    "revision": r[5],
                    "evidence": r[6],
                }
                for r in cursor.execute(
                    (
                        "SELECT "
                        "ContextId,ProgramId,ApplicantId,PeriodId,StageId,Revision,Ev"
                        "idence FROM crm_agents.Context WHERE ConversationId=? ORDER "
                        "BY ApprovedAt DESC"
                    ),
                    key,
                ).fetchall()
            ]
            selection, blocked = None, None
            try:
                selection = resolve_conversation(cursor, key, "local")
            except AiError as error:
                blocked = error.code
            return {
                "mode": row[0] if row else "automatic",
                "context_id": identifier(row[1]) if row else None,
                "revision": row[2] if row else 0,
                "reason": row[3] if row else "",
                "contexts": contexts,
                "selection": selection,
                "blocked": blocked,
            }

    def save_context(self, conversation_id, key, request):
        if not request.confirmed or not request.evidence.strip():
            raise AiError("agents_human_confirmation_required", 409)
        if (request.applicant_id is None) != (request.period_id is None):
            raise AiError("agents_application_period_required")
        with self.transaction(True) as cursor:
            _, stages = load(cursor)
            repeated, payload = replay(cursor, "context_approval", key, request)
            if repeated:
                return {"confirmed": True, "replayed": True}
            check_program(cursor, request.program_id)
            if not cursor.execute(
                "SELECT 1 FROM crm.Conversation WHERE ConversationId=?", conversation_id
            ).fetchone():
                raise AiError("conversation_not_found", 404)
            stage = stages.get(identifier(request.stage_id))
            if request.stage_id and (
                not stage
                or not stage["approved"]
                or stage["program_id"] != request.program_id
            ):
                raise AiError("agents_stage_approval_required", 409)
            if request.applicant_id:
                actual = cursor.execute(
                    (
                        "SELECT o.Id_Programa FROM dbo.ACAspirante a JOIN "
                        "dbo.ACProgramaOfrecido o ON "
                        "o.Id_PrgOfrecido=a.Id_PrgOfrecido WHERE a.Id_Aspirante=? "
                        "AND a.Id_Periodo=?"
                    ),
                    request.applicant_id,
                    request.period_id,
                ).fetchone()
                if not actual or actual[0] != request.program_id:
                    raise AiError("agents_application_scope_mismatch", 409)
                # This explicit human-confirmed context is the link. No document,
                # name or phone matching creates a relationship automatically.
            old = cursor.execute(
                (
                    "SELECT Revision,ConversationId,ProgramId,ApplicantId,PeriodId "
                    "FROM crm_agents.Context WHERE ContextId=?"
                ),
                key,
            ).fetchone()
            if (
                request.revision != (old[0] if old else 0)
                or old
                and (
                    identifier(old[1]) != conversation_id
                    or old[2] != request.program_id
                    or old[3] != request.applicant_id
                    or old[4] != request.period_id
                )
            ):
                raise AiError("agents_context_scope_immutable", 409)
            baseline = cursor.execute(
                (
                    "SELECT COALESCE(MAX(Sequence),0) FROM crm.Message WHERE "
                    "ConversationId=?"
                ),
                conversation_id,
            ).fetchval()
            if old:
                cursor.execute(
                    (
                        "UPDATE crm_agents.Context SET "
                        "StageId=?,StageRevision=?,Revision=Revision+1,Evidence=?,App"
                        "rovedAt=SYSUTCDATETIME(),BaselineSequence=? WHERE ContextId="
                        "?"
                    ),
                    identifier(request.stage_id),
                    stage["revision"] if stage else None,
                    request.evidence,
                    baseline,
                    key,
                )
            else:
                cursor.execute(
                    (
                        "INSERT "
                        "crm_agents.Context(ContextId,ConversationId,ProgramId,Applic"
                        "antId,PeriodId,StageId,StageRevision,Revision,Evidence,Basel"
                        "ineSequence) VALUES(?,?,?,?,?,?,?,1,?,?)"
                    ),
                    key,
                    conversation_id,
                    request.program_id,
                    request.applicant_id,
                    request.period_id,
                    identifier(request.stage_id),
                    stage["revision"] if stage else None,
                    request.evidence,
                    baseline,
                )
            history(
                cursor,
                "context_approval",
                key,
                request,
                payload,
                {"conversation_id": conversation_id, **request.model_dump(mode="json")},
            )
            invalidate(cursor, conversation_id)
        return {"confirmed": True, "context_id": key}

    def assign(self, key, request):
        if (
            not request.confirmed
            or not request.note.strip()
            or request.mode == "manual"
            and not request.agent_id
            or request.mode != "manual"
            and request.agent_id
        ):
            raise AiError("agents_human_confirmation_required", 409)
        with self.transaction(True) as cursor:
            agents, stages = load(cursor)
            repeated, payload = replay(cursor, "assignment", key, request)
            if repeated:
                return {"confirmed": True, "replayed": True}
            current = cursor.execute(
                "SELECT ControlMode,State FROM crm.Conversation WHERE ConversationId=?",
                key,
            ).fetchone()
            if not current:
                raise AiError("conversation_not_found", 404)
            old = cursor.execute(
                "SELECT Revision FROM crm_agents.Assignment WHERE ConversationId=?", key
            ).fetchone()
            if request.revision != (old[0] if old else 0):
                raise AiError("agents_revision_conflict", 409)
            context = context_row(cursor, key, identifier(request.context_id))
            selection = None
            if request.mode != "human":
                selection = resolve(
                    agents,
                    stages,
                    {"mode": request.mode, "agent_id": identifier(request.agent_id)},
                    context,
                    "local",
                )
            baseline = cursor.execute(
                (
                    "SELECT COALESCE(MAX(Sequence),0) FROM crm.Message WHERE "
                    "ConversationId=?"
                ),
                key,
            ).fetchval()
            if old:
                cursor.execute(
                    (
                        "UPDATE crm_agents.Assignment SET "
                        "Mode=?,ContextId=?,Revision=Revision+1,Reason=?,BaselineSequ"
                        "ence=? WHERE ConversationId=?"
                    ),
                    request.mode,
                    identifier(request.context_id),
                    request.note,
                    baseline,
                    key,
                )
            else:
                cursor.execute(
                    (
                        "INSERT "
                        "crm_agents.Assignment(ConversationId,Mode,ContextId,Revision"
                        ",Reason,BaselineSequence) VALUES(?,?,?,1,?,?)"
                    ),
                    key,
                    request.mode,
                    identifier(request.context_id),
                    request.note,
                    baseline,
                )
            agent_id = selection["agent_id"] if selection else None
            cursor.execute(
                (
                    "IF EXISTS(SELECT 1 FROM crm_inbox.Assignment WHERE "
                    "ConversationId=?) UPDATE crm_inbox.Assignment SET AiAgentId=? "
                    "WHERE ConversationId=? ELSE INSERT "
                    "crm_inbox.Assignment(ConversationId,AiAgentId) VALUES(?,?)"
                ),
                key,
                agent_id,
                key,
                key,
                agent_id,
            )
            mode = "human" if request.mode == "human" else "ai"
            change_control(cursor, key, (current[0], current[1]), (mode, current[1]))
            cursor.execute(
                (
                    "UPDATE crm.Conversation SET "
                    "ControlMode=?,UpdatedAt=SYSUTCDATETIME() WHERE ConversationId=?"
                ),
                mode,
                key,
            )
            history(
                cursor,
                "assignment",
                key,
                request,
                payload,
                {
                    "mode": request.mode,
                    "context_id": identifier(request.context_id),
                    "agent_id": agent_id,
                    "reason": selection["reason"] if selection else "human_control",
                },
            )
            invalidate(cursor, key)
        return {"confirmed": True}

    def reserve(self, cursor, request_id, selection, messages):
        # One reservation shared by all ancestors; uncertain billing stays reserved.
        from app.modules.agents.runtime import REPORTED_TOKENS_SQL, require_execution

        require_execution(cursor)
        if cursor.execute(
            "SELECT 1 FROM crm_agents.Usage WHERE RequestId=?", request_id
        ).fetchone():
            raise AiError("agents_request_already_consumed", 409)
        attempts = 3 * (1 + bool(selection["configuration"]["fallback_model"]))
        estimate = attempts * (
            sum(len(m["content"].encode("utf-8")) for m in messages)
            + selection["configuration"]["max_tokens"]
            + 256
        )
        agents, _ = load(cursor)
        for key in selection["chain_ids"]:
            cap = agents[key]["configuration"]["monthly_token_limit"]
            used = cursor.execute(
                (
                    f"SELECT COALESCE(SUM(COALESCE({REPORTED_TOKENS_SQL},CONVERT(bigint,u.TokensReserved))),0) FROM "
                    "crm_agents.Usage u LEFT JOIN crm_agents.Execution e ON e.RequestId=u.RequestId WHERE "
                    "u.CreatedAt>=DATEFROMPARTS(YEAR(SYSUTCDATETIME()),MONTH(SYSUTCDA"
                    "TETIME()),1) AND EXISTS(SELECT 1 FROM OPENJSON(u.ChainJson) j WH"
                    "ERE j.value=?)"
                ),
                key,
            ).fetchval()
            if (
                not cap
                or used + estimate > cap
                and agents[key]["configuration"].get("hard_stop", True)
            ):
                raise AiError("agents_budget_exhausted", 409)
        cursor.execute(
            (
                "INSERT "
                "crm_agents.Usage(RequestId,AgentId,ChainJson,TokensReserved,State) "
                "VALUES(?,?,?,?,'reserved')"
            ),
            request_id,
            selection["agent_id"],
            packed(selection["chain_ids"]),
            estimate,
        )
        from app.modules.agents.runtime import reserve_execution

        reserve_execution(cursor, request_id, selection, estimate)

    def settle(self, request_id, usage=None, result=None, error=None):
        with self.transaction(True) as cursor:
            tokens = sum(
                v
                for k, v in (usage or {}).items()
                if k in ("prompt_tokens", "completion_tokens")
                and type(v) is int
                and v >= 0
            )
            known = all(
                type((usage or {}).get(k)) is int and usage[k] >= 0
                for k in ("prompt_tokens", "completion_tokens")
            )
            expected_state = "completed" if known else "uncertain"
            expected_tokens = tokens if known else None
            token_update = "TokensUsed=?" if known else "TokensUsed=NULL"
            parameters = (
                [expected_state, tokens, request_id]
                if known
                else [expected_state, request_id]
            )
            update = (
                f"UPDATE crm_agents.Usage SET State=?,{token_update} "
                "WHERE RequestId=? AND State='reserved'"
            )
            if getattr(cursor, "dialect", None) == "postgresql":
                rows = cursor.execute(
                    update + " RETURNING State,TokensUsed", *parameters
                ).fetchall()
            else:
                rows = cursor.execute(
                    "SET NOCOUNT ON; " + update + "; "
                    "SELECT State,TokensUsed FROM crm_agents.Usage WHERE RequestId=?",
                    *parameters,
                    request_id,
                ).fetchall()
            while cursor.nextset():
                if cursor.description is not None:
                    cursor.fetchall()
            settled = rows[0] if len(rows) == 1 else None
            if (
                settled is None
                or settled[0] != expected_state
                or settled[1] != expected_tokens
            ):
                logging.getLogger(__name__).warning(
                    "AGENT_USAGE_SETTLEMENT stage=initial expected_state=%s expected_tokens=%s actual_state=%s actual_tokens=%s",
                    expected_state,
                    expected_tokens,
                    settled[0]
                    if settled and settled[0] in ("reserved", "completed", "uncertain")
                    else "missing",
                    settled[1] if settled else None,
                )
                raise AiError("agents_usage_settlement_initial_conflict", 503)
            from app.modules.agents.runtime import settle_execution

            settle_execution(cursor, request_id, usage, result, error)
            rows = cursor.execute(
                "SELECT State,TokensUsed FROM crm_agents.Usage WHERE RequestId=?",
                request_id,
            ).fetchall()
            while cursor.nextset():
                if cursor.description is not None:
                    cursor.fetchall()
            confirmed = rows[0] if len(rows) == 1 else None
            if (
                confirmed is None
                or confirmed[0] != expected_state
                or confirmed[1] != expected_tokens
            ):
                logging.getLogger(__name__).warning(
                    "AGENT_USAGE_SETTLEMENT stage=final expected_state=%s expected_tokens=%s actual_state=%s actual_tokens=%s",
                    expected_state,
                    expected_tokens,
                    confirmed[0]
                    if confirmed
                    and confirmed[0] in ("reserved", "completed", "uncertain")
                    else "missing",
                    confirmed[1] if confirmed else None,
                )
                raise AiError("agents_usage_settlement_final_conflict", 503)

    async def simulate(self, request):
        key = str(request.agent_id)
        with self.transaction() as cursor:
            agents, stages = load(cursor)
            selected = agents.get(key)
            if not selected or selected["version"] != request.config_version:
                raise AiError("agents_revision_conflict", 409)
            if selected["state"] == "archived":
                raise AiError("agents_archived_read_only", 409)
            selection = resolve(
                agents,
                stages,
                {},
                {
                    "program_id": request.program_id,
                    "stage_id": identifier(request.stage_id),
                },
                request.channel,
                simulation_id=key,
                require_active=request.call_provider,
            )
            from app.modules.agents.runtime import experiment, scoped_memory

            selection = experiment(
                cursor, selection, agents, key, explicit_variant=request.variant
            )
            check_program(cursor, request.program_id)
            institutional, sources = public_sources(
                cursor,
                request.question + (" " + " ".join(v.content for v in request.history if v.role == "user")
                    if getattr(cursor, "agent_catalog", None) else ""),
                request.program_id,
                identifier(request.stage_id),
                selection["configuration"],
            )
            if getattr(cursor, "agent_composition", None):
                cursor.agent_composition(selection, request.program_id, identifier(request.stage_id))
            policy = policy_for(selection)
            history = [
                {
                    "id": f"assistant-history:{index}",
                    "role": item.role,
                    "text": item.content,
                }
                for index, item in enumerate(request.history)
            ]
            if "short" not in selection["configuration"]["memories"]:
                history = []
            messages = assemble_prompt(
                policy,
                request.question,
                {"operational_context": scoped_memory(cursor, selection)},
                sources,
                history,
            )
            messages[0]["content"] += (
                "\nEsta es una prueba manual sin escritura de memoria del aspirante. No hay UUID de mensaje entrante admisible: devuelve memory=[] y no inventes identificadores ni hechos declarados."
            )
            proof = digest(
                [
                    selection["binding"],
                    institutional["fingerprint"],
                    source_proof(sources),
                ]
            )
        response = {
            "agent_id": key,
            "config_version": request.config_version,
            "program_id": request.program_id,
            "stage_id": identifier(request.stage_id),
            "supervisor_id": selection["supervisor_id"],
            "reason": "simulation_selected",
            "sources": [{k:s[k] for k in ("id","title","document_id","page","revision","source_kind") if k in s} for s in sources],
            "network_called": False,
            "crm_written": False,
            "delivered": False,
            "messages": messages,
            "usage": None,
            "provider": selection["configuration"].get("provider", "openrouter"),
            "variant": selection.get("variant"),
            **({"effective_context": {"fingerprint":selection["knowledge_context"]["fingerprint"],"versions":[{"id":v["id"],"version":v["version"],"kind":v["kind"]} for v in selection["knowledge_context"]["shared"]]}} if "knowledge_context" in selection else {}),
        }
        if not request.call_provider:
            return response
        if not request.acknowledge_consumption:
            raise AiError("agents_consumption_confirmation_required", 409)
        self.ai.refresh_credentials()
        config = self.ai.repository.read()
        credentials = self.ai.credentials.read()
        if not config.settings.enabled or not credentials.outbound:
            raise AiError("agents_global_ai_gate_closed", 409)
        require_provider(self.ai, selection["configuration"])
        binding = (config.revision, credentials.revision)

        def guard():
            if (
                self.ai.repository.read().revision,
                self.ai.credentials.read().revision,
            ) != binding:
                raise AiError("agents_configuration_changed", 409)
            with self.transaction() as cursor:
                fresh_agents, fresh_stages = load(cursor)
                fresh = resolve(
                    fresh_agents,
                    fresh_stages,
                    {},
                    {
                        "program_id": request.program_id,
                        "stage_id": identifier(request.stage_id),
                    },
                    request.channel,
                    simulation_id=str(request.agent_id),
                    require_active=True,
                )
                fresh = experiment(
                    cursor,
                    fresh,
                    fresh_agents,
                    str(request.agent_id),
                    explicit_variant=request.variant,
                )
                sql, new_sources = public_sources(
                    cursor,
                    request.question,
                    request.program_id,
                    identifier(request.stage_id),
                    fresh["configuration"],
                )
                if getattr(cursor, "agent_composition", None):
                    cursor.agent_composition(fresh, request.program_id, identifier(request.stage_id))
                if (
                    digest(
                        [
                            fresh["binding"],
                            sql["fingerprint"],
                            source_proof(new_sources),
                        ]
                    )
                    != proof
                ):
                    raise AiError("agents_configuration_changed", 409)

        with self.transaction(True) as cursor:
            self.reserve(cursor, str(request.request_id), selection, messages)
        result = None
        try:
            result = await complete(
                self.ai, selection, policy, messages, guard, preview=True
            )
            reply, _ = validate_reply(
                result["content"],
                sources,
                [],
                response_metadata=result.get("response_metadata"),
                allow_memory=False,
            )
            guard()
            self.settle(str(request.request_id), result["usage"], result)
            return {
                **response,
                "network_called": True,
                "text": reply.answer,
                "references": reply.references,
                "handoff": reply.handoff,
                "model": result["model"],
                "usage": result["usage"],
                "provider": result["provider"],
                "messages": None,
            }
        except BaseException as error:
            execution = result or getattr(error, "agent_execution", None)
            metadata = (execution or {}).get("response_metadata", {})
            usage = (execution or {}).get("usage", {})
            logging.getLogger(__name__).warning(
                "AGENT_GENERATION_FAILURE code=%s finish_reason=%s thought_tokens=%s input_tokens=%s output_tokens=%s",
                error.code if isinstance(error, AiError) else "generation_interrupted",
                metadata.get("finish_reason"),
                metadata.get("thought_tokens"),
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
            )
            self.settle(
                str(request.request_id),
                usage=(execution or {}).get("usage"),
                result=execution,
                error=error.code
                if isinstance(error, AiError)
                else "generation_interrupted",
            )
            raise
