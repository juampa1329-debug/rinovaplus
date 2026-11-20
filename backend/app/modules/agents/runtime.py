"""Scoped context, deterministic experiments and measured execution metadata."""

import json
from decimal import Decimal, ROUND_UP

from app.modules.agents.domain import Configuration, chain_for, digest, effective_configuration
from app.modules.ai.infrastructure.providers import AiError


# Usage owns reservations; a finished execution can also prove reported consumption.
REPORTED_TOKENS_SQL = (
    "COALESCE(CASE WHEN u.State='completed' THEN CONVERT(bigint,u.TokensUsed) END,"
    "CASE WHEN e.State IN('completed','failed') AND e.InputTokens>=0 AND e.OutputTokens>=0 "
    "THEN CONVERT(bigint,e.InputTokens)+CONVERT(bigint,e.OutputTokens) END)"
)


def execution_installed(cursor):
    rows = cursor.execute("SELECT OBJECT_ID(N'crm_agents.Execution')").fetchall()
    while cursor.nextset():
        if cursor.description is not None:
            cursor.fetchall()
    return bool(rows and rows[0][0] is not None)


def require_execution(cursor):
    if not execution_installed(cursor):
        raise AiError("agents_execution_migration_required", 503)


def historical_profile(cursor, agent, version):
    row = cursor.execute("SELECT TOP(1) Document FROM crm_agents.History WHERE EntityId=? AND Kind='agent_config' AND TRY_CONVERT(bigint,JSON_VALUE(Document,'$.version'))=? ORDER BY EventId DESC", agent["id"], version).fetchone()
    if not row:
        raise AiError("agents_ab_version_unavailable", 409)
    old = json.loads(row[0])
    if any(old.get(field) != agent.get(field) for field in ("id", "level", "parent_id", "program_id", "stage_id")):
        raise AiError("agents_assignment_conflict", 409)
    return old


def validate_experiment(cursor, agent):
    config = agent["configuration"]
    if config.get("ab_enabled"):
        version = config.get("ab_compare_version")
        if not version or version >= agent["version"]:
            raise AiError("agents_ab_version_unavailable", 409)
        historical_profile(cursor, agent, version)


def experiment(cursor, selection, agents, key, *, explicit_variant=None):
    current = selection["configuration"]
    variant = current.get("ab_variant", "A")
    selection["variant_version"] = selection["version"]
    selection["variant"] = variant
    if not current.get("ab_enabled"):
        return selection
    agent = agents[selection["agent_id"]]
    baseline = historical_profile(cursor, agent, current.get("ab_compare_version"))
    selected = explicit_variant == "comparison"
    if explicit_variant is None and selection["reason"] not in ("manual_protected", "simulation_selected"):
        bucket = int(digest([key, agent["id"], agent["version"], current["ab_compare_version"]])[:8], 16) % 100
        selected = bucket >= current["ab_traffic_percent"]
    if selected:
        old = Configuration.model_validate_json(json.dumps(baseline["configuration"])).model_dump(mode="json")
        for field in ("capabilities", "channels", "memories"):
            old[field] = [value for value in old[field] if value in current[field]]
        for field in ("allow_reply", "allow_safe_actions", "allow_crm_update", "global_enabled"):
            old[field] = old[field] and current[field]
        old["require_human_approval"] = old["require_human_approval"] or current["require_human_approval"]
        old["max_tokens"] = min(old["max_tokens"], current["max_tokens"])
        old["document_ids"] = [value for value in old["document_ids"] if value in current["document_ids"]]
        for field in ("monthly_token_limit", "monthly_usd_limit", "usage_alert_percent", "hard_stop"):
            old[field] = current[field]
        if not any(field in baseline["configuration"] for field in ("instruction_template", "template_variables")):
            old.pop("instruction_template", None)
            old.pop("template_variables", None)
        old_agent = {**agent, "configuration": old}
        selection["configuration"] = effective_configuration(chain_for(old_agent, {**agents, agent["id"]: old_agent}))
        selection["variant_version"] = baseline["version"]
        selection["variant"] = "Comparación v" + str(baseline["version"])
    selection["binding"] = digest([selection["binding"], selection["variant"], selection["variant_version"], current["ab_compare_version"]])
    return selection


def scoped_memory(cursor, selection, conversation_id=None):
    """Return bounded data for this conversation/agent; never another applicant."""
    config = selection["configuration"]
    enabled = set(config["memories"])
    result = {"selected_scopes": sorted(enabled), "route": config["route"], "industry_policies": config["industry_policies"]}
    agent_id = selection["agent_id"]
    program = (selection.get("context") or {}).get("program_id")
    if not program:
        row = cursor.execute("SELECT ProgramId FROM crm_agents.Profile WHERE AgentId=?", agent_id).fetchone()
        program = row[0] if row else None
    if "business_summary" in enabled:
        result["business_summary"] = {"scope": "admisiones", "program_id": program, "source": "oferta institucional del período activo"}
    if "regulated" in enabled:
        result["regulated"] = "No confirmar pagos, matrícula, becas o admisión. Preservar datos personales y transferir solicitudes humanas."
    if "vertical" in enabled:
        result["vertical"] = {"program_id": program, "source": "contexto institucional suministrado", "authority": "SQL institucional"}
    if "collective" in enabled:
        result["collective"] = {"policy": config["industry_policies"], "knowledge": "Sólo documentos publicados y autorizados para este ámbito; no memorias de otros aspirantes."}
    if "workflows" in enabled:
        rows = cursor.execute("SELECT TOP(5) Kind,CreatedAt FROM crm_agents.History WHERE EntityId=? AND Kind IN('agent_state','reindex','action_draft','action_execute') ORDER BY EventId DESC", agent_id).fetchall()
        result["workflows"] = [{"kind": r[0], "at": str(r[1])} for r in rows]
    if "campaigns" in enabled or "campaigns.suggest" in config["capabilities"]:
        rows = cursor.execute("SELECT TOP(5) Kind,Status,ScheduledAtUtc FROM crm_marketing.Campaign WHERE ? IS NOT NULL AND EXISTS(SELECT 1 FROM OPENJSON(SegmentJson,'$.program_ids') x WHERE TRY_CONVERT(int,x.value)=?) ORDER BY UpdatedAtUtc DESC", program, program).fetchall()
        result["campaigns"] = [{"kind": r[0], "state": r[1], "scheduled_at": str(r[2]) if r[2] else None} for r in rows]
    if "compliance.check" in config["capabilities"]:
        result["compliance_check"] = {"program_scope": program, "policies": config["industry_policies"], "institutional_changes_allowed": False, "payment_confirmation_allowed": False, "human_control_overrides_agent": True}
    if (config["global_enabled"] or conversation_id) and ("analytics.read" in config["capabilities"] or "analytics.report" in config["capabilities"]):
        row = cursor.execute("SELECT COUNT(*),SUM(CASE WHEN c.State='open' THEN 1 ELSE 0 END) FROM crm_agents.Context x JOIN crm.Conversation c ON c.ConversationId=x.ConversationId WHERE ? IS NOT NULL AND x.ProgramId=?", program, program).fetchone()
        result["analytics"] = {"contexts": row[0], "open_contexts": row[1] or 0, "program_id": program, "no_personal_records": True}
    if conversation_id:
        if "customer_profile" in enabled:
            row = cursor.execute("SELECT p.Interests,p.Stage,c.Priority,c.State FROM crm.Conversation c JOIN crm.Contact p ON p.ContactId=c.ContactId WHERE c.ConversationId=?", conversation_id).fetchone()
            result["customer_profile"] = {"declared_interests": row[0], "stage": row[1], "priority": row[2], "state": row[3], "authority": "declaración CRM, no matrícula verificada"} if row else None
        if "incidents" in enabled:
            rows = cursor.execute("SELECT TOP(5) Title,Priority,Status FROM crm_inbox.Task WHERE ConversationId=? ORDER BY CreatedAt DESC", conversation_id).fetchall()
            result["incidents"] = [{"title": r[0], "priority": r[1], "state": r[2]} for r in rows]
    else:
        for scope in ("customer_profile", "incidents"):
            if scope in enabled:
                result[scope] = {"available": False, "reason": "Sin conversación seleccionada"}
    if getattr(cursor, "agent_memory", None):
        reviewed = cursor.agent_memory(selection, conversation_id)
        # policy_for embeds these exact reviewed DNA versions in the system role.
        # Do not resend their bodies as user evidence; retain their references.
        embedded = {(v["id"], v["version"]) for v in selection.get("institution_dna", [])}
        shared = reviewed.get("shared", [])
        result["reviewed_memory"] = {**reviewed,
            "shared": [v for v in shared if (v["id"], v["version"]) not in embedded],
            "dna_in_system": [{"id": v["id"], "version": v["version"]} for v in shared if (v["id"], v["version"]) in embedded]}

    return result


def prices(config):
    return {"input": config.get("input_usd_per_million"), "output": config.get("output_usd_per_million"), "fallback_input": config.get("fallback_input_usd_per_million"), "fallback_output": config.get("fallback_output_usd_per_million"), "basis": "operator_estimate_per_million_tokens_not_billing"}


def reserve_cost(config, tokens):
    values = prices(config)
    required = ("input", "output", "fallback_input", "fallback_output") if config["fallback_model"] else ("input", "output")
    if any(values[key] is None for key in required):
        if config["monthly_usd_limit"] and config["hard_stop"]:
            raise AiError("agents_pricing_required", 409)
        return None
    return (Decimal(tokens) * max(Decimal(str(values[key])) for key in required) / Decimal(1000000)).quantize(Decimal("0.00000001"), rounding=ROUND_UP)


def reserve_execution(cursor, request_id, selection, tokens):
    require_execution(cursor)
    config = selection["configuration"]
    reserved = reserve_cost(config, tokens)
    for agent_id in selection["chain_ids"]:
        row = cursor.execute("SELECT Document FROM crm_agents.Profile WHERE AgentId=?", agent_id).fetchone()
        owner = Configuration.model_validate_json(row[0]).model_dump(mode="json")
        if owner["monthly_usd_limit"] and owner["hard_stop"]:
            usage = cursor.execute("SELECT SUM(COALESCE(e.CostEstimated,e.CostReserved)),SUM(CASE WHEN e.CostEstimated IS NULL AND e.CostReserved IS NULL THEN 1 ELSE 0 END) FROM crm_agents.Execution e JOIN crm_agents.Usage u ON u.RequestId=e.RequestId WHERE e.CreatedAt>=DATEFROMPARTS(YEAR(SYSUTCDATETIME()),MONTH(SYSUTCDATETIME()),1) AND EXISTS(SELECT 1 FROM OPENJSON(u.ChainJson) j WHERE j.value=?)", agent_id).fetchone()
            if reserved is None:
                raise AiError("agents_pricing_required", 409)
            if usage[1]:
                raise AiError("agents_cost_uncertain", 409)
            if Decimal(str(usage[0] or 0)) + reserved > Decimal(str(owner["monthly_usd_limit"])):
                raise AiError("agents_budget_exhausted", 409)
    cursor.execute("INSERT crm_agents.Execution(RequestId,AgentId,AgentVersion,ConversationId,Provider,ModelId,Route,Variant,PricingJson,CostReserved,State,SourceFingerprint) VALUES(?,?,?,?,?,?,?,?,?,?,'reserved',?)", request_id, selection["agent_id"], selection.get("variant_version", selection["version"]), selection.get("conversation_id"), config["provider"], config["primary_model"], config["route"], selection.get("variant", config["ab_variant"]), json.dumps(prices(config)), reserved, selection["binding"])


def settle_execution(cursor, request_id, usage=None, result=None, error=None):
    if not execution_installed(cursor):
        return
    rows = cursor.execute("SELECT PricingJson,Provider FROM crm_agents.Execution WHERE RequestId=? AND State='reserved'", request_id).fetchall()
    while cursor.nextset():
        if cursor.description is not None:
            cursor.fetchall()
    row = rows[0] if rows else None
    if not row:
        return
    result = result or {}
    rates = json.loads(row[0])
    prefix = "fallback_" if result.get("fallback_used") else ""
    incoming, outgoing = (usage or {}).get("prompt_tokens"), (usage or {}).get("completion_tokens")
    cost = None
    if type(incoming) is int and type(outgoing) is int and rates[prefix + "input"] is not None and rates[prefix + "output"] is not None:
        cost = (Decimal(incoming) * Decimal(str(rates[prefix + "input"])) + Decimal(outgoing) * Decimal(str(rates[prefix + "output"]))) / Decimal(1000000)
    known_usage = type(incoming) is int and type(outgoing) is int and incoming >= 0 and outgoing >= 0
    state = "failed" if error and known_usage else "completed" if known_usage else "uncertain"
    attempts = json.dumps(result.get("attempts", []))
    # Fixed columns only; NULL literals avoid nullable-parameter discovery in ODBC.
    updates = ["State=?", "FallbackUsed=?", "AttemptsJson=?", "FinishedAt=SYSUTCDATETIME()"]
    parameters = [state, bool(result.get("fallback_used")), attempts]
    for column, value, preserve in (
        ("Provider", result.get("provider"), True), ("ModelId", result.get("model"), True),
        ("InputTokens", incoming, False), ("OutputTokens", outgoing, False),
        ("CostEstimated", cost, False), ("LatencyMs", result.get("latency_ms"), False),
        ("ErrorCode", error, False),
    ):
        if value is not None:
            updates.append(column + "=?")
            parameters.append(value)
        elif not preserve:
            updates.append(column + "=NULL")
    cursor.execute("UPDATE crm_agents.Execution SET " + ",".join(updates) + " WHERE RequestId=? AND State='reserved'", *parameters, request_id)
    while cursor.nextset():
        if cursor.description is not None:
            cursor.fetchall()


def observation(cursor, agent_id):
    if not execution_installed(cursor):
        return {"installed": False, "runs": [], "metrics": None}
    rows = cursor.execute("SELECT TOP(25) RequestId,AgentVersion,Provider,ModelId,Variant,FallbackUsed,InputTokens,OutputTokens,CostEstimated,CostReserved,LatencyMs,State,ErrorCode,CreatedAt,AttemptsJson FROM crm_agents.Execution WHERE AgentId=? ORDER BY CreatedAt DESC", agent_id).fetchall()
    keys = ("request_id", "version", "provider", "model", "variant", "fallback", "input_tokens", "output_tokens", "cost_usd_estimate", "cost_usd_reserved", "latency_ms", "state", "error", "created_at", "attempts_json")
    items = [{k: float(v) if isinstance(v, Decimal) else str(v) if k in ("request_id", "created_at") else v for k, v in zip(keys, r, strict=True)} for r in rows]
    row = cursor.execute("SELECT COUNT(*),SUM(CASE WHEN State='completed' THEN 1 ELSE 0 END),SUM(CASE WHEN State IN('failed','uncertain') THEN 1 ELSE 0 END),SUM(CONVERT(int,FallbackUsed)),AVG(LatencyMs) FROM crm_agents.Execution WHERE AgentId=? AND CreatedAt>=DATEADD(day,-7,SYSUTCDATETIME())", agent_id).fetchone()
    month = cursor.execute(f"SELECT COALESCE(SUM(CONVERT(bigint,u.TokensReserved)),0),SUM({REPORTED_TOKENS_SQL}),SUM(e.CostEstimated),SUM(e.CostReserved),SUM(CASE WHEN e.CostEstimated IS NULL THEN 1 ELSE 0 END),COALESCE(SUM(COALESCE({REPORTED_TOKENS_SQL},CONVERT(bigint,u.TokensReserved))),0) FROM crm_agents.Usage u LEFT JOIN crm_agents.Execution e ON e.RequestId=u.RequestId WHERE u.AgentId=? AND u.CreatedAt>=DATEFROMPARTS(YEAR(SYSUTCDATETIME()),MONTH(SYSUTCDATETIME()),1)", agent_id).fetchone()
    versions = cursor.execute("SELECT DISTINCT TRY_CONVERT(bigint,JSON_VALUE(Document,'$.version')) FROM crm_agents.History WHERE EntityId=? AND Kind='agent_config' ORDER BY 1 DESC", agent_id).fetchall()
    return {"installed": True, "runs": items, "versions": [v[0] for v in versions if v[0]], "metrics": {"runs_7d": row[0], "successes_7d": row[1] or 0, "errors_7d": row[2] or 0, "fallbacks_7d": row[3] or 0, "latency_ms": row[4], "health": round(100 * (row[1] or 0) / row[0]) if row[0] else None, "tokens_reserved": month[0], "tokens_reported": month[1], "tokens_budget_used": month[5], "usd_estimate": float(month[2]) if month[2] is not None else None, "usd_reserved": float(month[3]) if month[3] is not None else None, "unknown_cost_runs": month[4] or 0, "billing": False}}
