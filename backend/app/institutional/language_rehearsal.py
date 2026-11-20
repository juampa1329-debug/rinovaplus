"""Operator-only P21 rehearsal: synthetic principal, capped real backup, no outbox."""

import asyncio
import json
import math
import re
from typing import Literal

from fastapi import HTTPException, Request
from pydantic import Field

from app.institutional import grounded_replies, language_resilience as resilience
from app.institutional.auth import authorize
from app.institutional.db import institution, one, record_operation, replay, uid
from app.institutional.models import Strict
from app.institutional.settings import setting
from app.institutional.store import transaction
from app.modules.agents.skill_policy import for_turn, instructions, prompt_trace
from app.modules.ai.infrastructure.providers import AiError, ProviderGateway

ACTION = "ai_resilience_rehearsal"
MAX_REHEARSAL_USD_MICROS = 50000


async def free_quota(gateway):
    """Expose request counts only, never the key label, credits or account IDs."""
    try:
        data = await gateway.request("openrouter", "GET", "key")
        value = data.get("data", {}).get("free_model_daily_requests", {})
        if not all(type(value.get(k)) is int for k in ("used", "limit", "remaining")):
            return None
        if value["used"] < 0 or value["limit"] < 0:
            return None
        return {"used": value["used"], "limit": value["limit"], "remaining": max(0, value["remaining"])}
    except (AiError, TypeError, AttributeError):
        return None


class Rehearsal(Strict):
    operation_id: str = Field(min_length=36, max_length=36)
    revision: int = Field(ge=0)
    case: Literal["unavailable", "rate_limited", "healthy", "human"] = "unavailable"
    audience: Literal["message", "comment"] = "message"
    allow_paid: bool = False


def context(audience):
    public = audience == "comment"
    question = "¿Cuánto dura el programa de esta publicación y en qué jornada se ofrece?" if public else "¿Recuerdas mi nombre, el programa que elegí y su duración y jornada?"
    history = [] if public else [{"direction": "incoming", "text": "Me llamo Alex. Me interesa el Programa Demostración P21 en jornada nocturna."}]
    skills = for_turn(question, history=history, public=public)
    system = (
        "Ensayo técnico aislado. Los siguientes datos son ficticios y no son oferta de CBN. "
        "Responde en español, brevemente y sólo según la fuente: Programa Demostración P21, "
        "duración 2 semestres, jornada nocturna. Precios y fechas por confirmar. "
        "No ejecutes acciones ni escribas en el CRM. Devuelve decision=responder y text. "
        + ("Es un comentario público: no uses nombres ni memoria privada." if public else "Es un mensaje privado ficticio: recuerda y utiliza el nombre Alex.")
        + instructions(skills)
    )
    return {"system": system, "query": json.dumps({"question": question, "history": history,
            "source": {"program": "Programa Demostración P21", "duration": "2 semestres", "schedule": "nocturna", "price": None},
            "synthetic": True}, ensure_ascii=False)}, prompt_trace(skills)


def checks(text, audience):
    lower = text.casefold()
    return {"program_preserved": "demostración p21" in lower or "demostracion p21" in lower,
            "duration_preserved": bool(re.search(r"(?:2|dos)\s+semestres", lower)),
            "schedule_preserved": "nocturn" in lower,
            "name_preserved_or_private_excluded": "alex" not in lower if audience == "comment" else "alex" in lower}


def recover(settings, authority, operation):
    with transaction(settings, anonymous=True) as c:
        actor = authorize(c, settings, authority, "settings.ai.read")
        row = one(c, "SELECT Result FROM crm_access.Operation WHERE InstitutionId=? AND OperationId=? "
                  "AND ActorId=? AND Action=?", institution(settings), uid(operation), actor["UserId"], ACTION)
        if not row:
            raise HTTPException(404, "language_rehearsal_not_found")
        return json.loads(row["Result"])


def run(settings, authority, body, *, gateway=None):
    operation = uid(body.operation_id)
    payload = body.model_dump(exclude={"operation_id"})
    resource = "p21:" + body.audience + ":" + body.case
    with transaction(settings, True, anonymous=True) as c:
        actor = authorize(c, settings, authority, "settings.ai.write", recent=True)
        authorize(c, settings, authority, "settings.providers.read")
        digest, prior = replay(c, settings, actor["UserId"], operation, ACTION, resource, payload)
        if prior is not None:
            return prior  # Never perform provider IO again, even after a lost response.
        ai = setting(c, settings, "ai")
        if ai["revision"] != body.revision:
            raise HTTPException(409, "revision_conflict")
        if not ai["document"]["enabled"]:
            raise HTTPException(409, "language_rehearsal_ai_disabled")
        saved = resilience.snapshot(c, settings)
        if not saved["routes"] or any(r["provider"] != "openrouter" for r in saved["routes"]):
            raise HTTPException(409, "language_rehearsal_free_backup_required")
        paid = any(not r["model"].endswith(":free") or r["input_usd_per_million"] != 0
                   or r["output_usd_per_million"] != 0 for r in saved["routes"])
        if paid and body.case not in {"healthy", "human"} and not body.allow_paid:
            raise HTTPException(409, "language_rehearsal_paid_confirmation_required")
        result = {"operation_id": operation, "state": "running", "case": body.case, "audience": body.audience,
                  "synthetic_primary": True, "real_backup": False, "provider_calls": 0, "reservations": [],
                  "published_configuration_changed": False, "crm_written": False, "delivered": False, "trace": {},
                  "cost_cap_usd_micros": MAX_REHEARSAL_USD_MICROS, "reserved_usd_micros": 0}
        record_operation(c, settings, actor["UserId"], operation, ACTION, resource, digest, result)

    def guard():
        if body.case == "human":
            raise HTTPException(409, "language_rehearsal_human_control")
        with transaction(settings, anonymous=True) as c:
            authorize(c, settings, authority, "settings.ai.write")
            resilience.assert_snapshot(c, settings, saved)
            if not one(c, "SELECT OperationId FROM crm_access.Operation WHERE InstitutionId=? AND OperationId=? "
                       "AND ActorId=? AND Action=? AND JSON_VALUE(Result,'$.state')='running' "
                       "AND CreatedAt>=DATEADD(minute,-3,SYSUTCDATETIME())",
                       institution(settings), operation, actor["UserId"], ACTION):
                raise HTTPException(409, "language_rehearsal_claim_changed")

    def reserve(route, incoming, outgoing):
        micros = max(1, math.ceil(incoming * route["input_usd_per_million"] + outgoing * route["output_usd_per_million"]))
        if result["reserved_usd_micros"] + micros > MAX_REHEARSAL_USD_MICROS:
            raise HTTPException(429, "language_rehearsal_cost_limit")
        resilience.reservation(settings, saved, route, incoming, outgoing)
        result["reserved_usd_micros"] += micros
        result["reservations"].append({"provider": route["provider"], "model": route["model"], "tokens": incoming + outgoing,
                                       "usd_micros": micros})

    async def primary():
        if body.case == "healthy":
            return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps({
                "decision": "responder", "text": ("" if body.audience == "comment" else "Alex, ") + "Programa Demostración P21: 2 semestres en jornada nocturna."})}]}}]}
        status = 429 if body.case == "rate_limited" else 503
        raise AiError("provider_rate_limited" if status == 429 else "provider_temporary_failure", 502, True, status)

    value, skills = context(body.audience)
    result["skill_policy"] = skills
    delegate = gateway or ProviderGateway(saved["keys"])

    class ObservedGateway:
        @property
        def catalog_details(self):
            return delegate.catalog_details

        async def models(self, *args, **kwargs):
            return await delegate.models(*args, **kwargs)

        async def request(self, *args, **kwargs):
            if args[1] == "POST":
                result["provider_calls"] += 1
            return await delegate.request(*args, **kwargs)

    try:
        response = asyncio.run(resilience.execute(primary, ai["document"]["provider"], ai["document"]["model"],
            grounded_replies.request_body(value, 700), saved, guard, reserve, result["trace"], gateway=ObservedGateway()))
        result["usage"] = {k: v for k, v in response.get("usageMetadata", {}).items() if type(v) is int and 0 <= v <= 10000000}
        text = grounded_replies.parse(response, public=body.audience == "comment")
        if not text:
            raise ValueError("rehearsal_handoff")
        result.update(text=text, checks=checks(text, body.audience))
        result["state"] = "passed" if all(result["checks"].values()) else "review_required"
    except HTTPException as error:
        result.update(state="passed" if error.detail == "language_rehearsal_human_control" else "blocked", code=error.detail)
    except AiError as error:
        result.update(state="uncertain" if result["provider_calls"] and error.status >= 500 and not resilience.can_failover(error) else "failed", code=error.code)
    except Exception:
        result.update(state="uncertain", code="language_rehearsal_result_unknown")
    if any(a.get("code") == "provider_rate_limited" and a.get("provider") == "openrouter"
           and a.get("model", "").endswith(":free") for a in result["trace"].get("attempts", [])):
        try:
            guard()
            quota = asyncio.run(free_quota(delegate))
        except HTTPException:
            quota = None
        if quota is not None:
            result["free_quota"] = quota
            if result["state"] != "passed" and quota["remaining"] == 0:
                result["code"] = "openrouter_free_daily_limit"
    result["real_backup"] = bool(result["provider_calls"])
    with transaction(settings, True, anonymous=True) as c:
        c.execute("UPDATE crm_access.Operation SET Result=? WHERE InstitutionId=? AND OperationId=? AND ActorId=? "
                  "AND Action=? AND PayloadHash=? AND JSON_VALUE(Result,'$.state')='running'",
                  json.dumps(result, ensure_ascii=False), institution(settings), operation, actor["UserId"], ACTION, digest)
        if c.rowcount != 1:
            raise HTTPException(409, "language_rehearsal_claim_changed")
    return result


def install(app, settings):
    @app.post("/api/institution/language-rehearsals")
    def rehearse(request: Request, body: Rehearsal):
        return run(settings, request.state.authority, body)

    @app.get("/api/institution/language-rehearsals/{operation}")
    def existing(request: Request, operation: str):
        return recover(settings, request.state.authority, operation)
