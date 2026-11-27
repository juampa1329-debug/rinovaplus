"""Reviewed local SIIE copies. Missing fields stay missing; manual edits survive refresh."""

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Literal

from fastapi import HTTPException
from pydantic import Field, ValidationError, model_validator

from app.institutional.db import institution, one
from app.institutional.models import Strict
from app.institutional.program_commercial import CommercialProfile, ExtractedProgram, FinancialPlan


class SiieSync(Strict):
    kind: Literal["program", "offer"]
    source_revision: str = Field(min_length=1, max_length=120)
    offer_id: str = Field(default="", max_length=80)
    program_id: str = Field(default="", pattern=r"^(?:[1-9][0-9]{0,9})?$")
    period_id: str = Field(default="", pattern=r"^(?:[1-9][0-9]{0,9})?$")
    cursor: str = Field(default="", max_length=128)
    environment: dict | None = None

    @model_validator(mode="after")
    def target(self):
        if (self.kind == "offer" and not self.offer_id) or (self.kind == "program" and not self.program_id):
            raise ValueError("siie_invalid_parameter")
        return self


def source_section(program_id, kind, environment=None):
    from app.institutional.siie_environment import current
    environment = environment or current().document()
    if kind not in {'program','offer'} or not re.fullmatch(r'[0-9a-f]{64}',environment['fingerprint']):
        raise ValueError('invalid_siie_source_environment')
    return f"siie-{environment['fingerprint'][:16]}-{kind[0]}-{program_id}"


def local_source(c, settings, program_id, kind="offer"):
    from app.institutional.siie_environment import configured, current
    if not configured():
        return None
    row = one(c, "SELECT Document FROM crm_access.Setting WHERE InstitutionId=? AND Section=?", institution(settings), source_section(program_id, kind))
    value = json.loads(row["Document"]) if row else None
    return value if value and value.get("environment") == current().document() else None


def mapped_programs(c, settings, source, *, detail=False):
    """A numeric SIIE ID alone never identifies a local program across environments."""
    from app.institutional.siie_environment import require
    environment = require(source.get("environment")).document()
    fields = "p.ProgramId,p.Name,p.School,p.Schedule,p.Active,p.Revision" if detail else "p.ProgramId"
    return c.execute(
        f"SELECT DISTINCT {fields} FROM crm_agents5.Program p JOIN crm_access.Setting s "
        "ON s.InstitutionId=p.InstitutionId AND (s.Section=CONCAT(?,p.ProgramId) OR s.Section=CONCAT(?,p.ProgramId)) "
        "WHERE p.InstitutionId=? AND JSON_VALUE(s.Document,'$.environment.fingerprint')=? "
        "AND JSON_VALUE(s.Document,'$.environment.base_url')=? AND JSON_VALUE(s.Document,'$.program_id')=?",
        source_section("", "program", environment), source_section("", "offer", environment),
        institution(settings), environment["fingerprint"], environment["base_url"], source["program_id"],
    ).fetchall()


def save_source(c, settings, program_id, revision, actor, source):
    # Separate from the operator-editable facts: this remains the actual last
    # received source. Same transaction and revision as the CRM program write.
    # Reuse the versioned Setting/SettingHistory storage without new DDL.
    from app.institutional.siie_environment import require
    require(source.get("environment"))
    ref = source_section(program_id, source["kind"],source["environment"])
    document = json.dumps(source, ensure_ascii=False)
    c.execute("UPDATE crm_access.Setting SET Document=?,Revision=?,UpdatedBy=?,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND Section=?", document, revision, actor, institution(settings), ref)
    if c.rowcount == 0:
        c.execute("INSERT crm_access.Setting(InstitutionId,Section,Document,Revision,UpdatedAt,UpdatedBy) VALUES(?,?,?,?,SYSUTCDATETIME(),?)", institution(settings), ref, document, revision, actor)
    c.execute("INSERT crm_access.SettingHistory(InstitutionId,Section,Revision,Document,RecordedAt,ActorId) VALUES(?,?,?,?,SYSUTCDATETIME(),?)", institution(settings), ref, revision, document, actor)


def draft_from_source(value, *, kind="offer", request=None, environment=None):
    """Whitelist source facts; never promote an incomplete offer to a firm quote."""
    request = request or {}

    program_id = str(value.get('program_id') or '')
    if not re.fullmatch(r'[1-9][0-9]{0,9}', program_id) or int(program_id) > 2147483647:
        raise HTTPException(502, 'siie_catalog_invalid_response')
    if kind == "offer" and value.get("currency") != "COP":
        raise HTTPException(502, "siie_catalog_invalid_response")
    commercial = value.get("commercial") or {}
    if not isinstance(commercial, dict):
        raise HTTPException(502, "siie_catalog_invalid_response")
    issues = []
    fields = set(CommercialProfile.model_fields) - {"financial_plans"}
    values = {k: v for k, v in commercial.items() if k in fields and v is not None}
    values.update({
        "siie_program_id": str(value.get("program_id") or ""),
        "siie_offer_id": str(value.get("offer_id") or ""),
        "siie_period_id": str(value.get("period_id") or ""),
        "siie_campus_id": str(value.get("campus_id") or ""),
        "siie_shift_id": str(value.get("shift_id") or ""),
        "siie_source_revision": value["source_revision"],
        "source_checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "siie_offer_active": value.get("active") if kind == "offer" and type(value.get("active")) is bool else None,
        "source_note": "Catálogo base de programas. La disponibilidad de una oferta o período debe confirmarse." if kind == "program" else "Importes informados por SIIE, sujetos a las fechas y condiciones conocidas. Los datos ausentes están por confirmar con un asesor.",
    })
    if kind == "program":
        for key in ("duration", "modality"):
            if value.get(key):
                values[key] = str(value[key])
        if value.get("duration_levels") is not None:
            values["duration"] = f"{value['duration_levels']} niveles"
    if value.get("code"):
        values["aliases"] = str(value["code"])
    if (values.get("price_cop") is not None or values.get("full_cost_cash_cop") is not None) and not values.get("price_concept"):
        values["price_concept"] = "Enseñanza del nivel" if commercial.get("price_scope") == "semester_tuition_only" else "Tarifa informada; alcance por confirmar"
    plans = []
    for i, raw in enumerate(commercial.get("financial_plans") or []):
        if not isinstance(raw, dict):
            issues.append(f"Plan {i + 1}: información por confirmar")
            continue
        selected = {k: v for k, v in raw.items() if k in FinancialPlan.model_fields and v is not None}
        if isinstance(selected.get("installments"), list):
            selected["installments"] = [{k: v for k, v in part.items() if k in {"number", "amount_cop", "due_date"}} for part in selected["installments"] if isinstance(part, dict)]
        try:
            plans.append(FinancialPlan.model_validate(selected).model_dump())
        except ValidationError:
            issues.append(f"Plan {i + 1}: importes, fechas o numeración requieren revisión; no se publican sus valores contradictorios")
    values["financial_plans"] = plans
    try:
        profile = CommercialProfile.model_validate(values)
        draft = ExtractedProgram(name=value.get("name") or "", school=value.get("school") or "", schedule=value.get("schedule") or "", commercial=profile)
    except ValidationError:
        raise HTTPException(502, "siie_catalog_invalid_response") from None
    if not draft.name.strip() or not profile.siie_program_id:
        raise HTTPException(502, "siie_catalog_invalid_response")
    return {
        "environment": environment,
        "kind": kind, "program_id": profile.siie_program_id, "offer_id": profile.siie_offer_id,
        "source_revision": value["source_revision"], "period_id": profile.siie_period_id,
        "checked_at": values["source_checked_at"], "values": draft.model_dump(),
        "quality": value.get("data_quality", []), "issues": issues,
        "provider_quotable": value.get("quotable") is True,
        "request": request,
    }


def merge_reviewed(current, previous, incoming, path=""):
    """Three-way merge, including plan/instalment keys. Never overwrite manual edits."""
    if current == previous:
        return deepcopy(incoming), []
    if isinstance(current, dict) and isinstance(previous, dict) and isinstance(incoming, dict):
        merged, manual = {}, []
        for key in current.keys() | previous.keys() | incoming.keys():
            value, kept = merge_reviewed(current.get(key), previous.get(key), incoming.get(key), f"{path}.{key}".strip("."))
            if value is not None or key in incoming or key in current:
                merged[key] = value
            manual.extend(kept)
        return merged, manual
    if all(isinstance(v, list) for v in (current, previous, incoming)):
        key = "external_id" if path.endswith("financial_plans") else "number" if path.endswith("installments") else None
        if key and all(isinstance(item, dict) and key in item for values in (current, previous, incoming) for item in values):
            maps = [{str(v[key]): v for v in values} for values in (current, previous, incoming)]
            order = list(dict.fromkeys([str(v[key]) for v in incoming + current]))
            result, kept = [], []
            for identity in order:
                v, m = merge_reviewed(*(values.get(identity) for values in maps), f"{path}[{identity}]")
                if v is not None:
                    result.append(v)
                kept.extend(m)
            return result, kept
    if current == incoming:
        return deepcopy(current), []
    # New empty fields are filled. An intentional null after a previous source
    # value is a local edit and remains null until explicitly changed.
    if previous in (None, "", []) and current in (None, "", []):
        return deepcopy(incoming), []
    return deepcopy(current), [path]


def reviewed_draft(current, previous, source):
    current = ExtractedProgram.model_validate(current).model_dump()
    incoming = deepcopy(source["values"])
    if source["kind"] == "offer" and current["commercial"].get("siie_offer_id") not in (None, "", source["offer_id"]):
        # A date approved for a different level/period is not an override here.
        return ExtractedProgram.model_validate(incoming), []
    if source["kind"] == "program":
        # Refreshing names/schools must not clear financial facts of an offer.
        for key in list(incoming["commercial"]):
            if key not in {"aliases", "duration", "modality", "siie_program_id", "siie_source_revision", "source_checked_at"}:
                incoming["commercial"][key] = current.get("commercial", {}).get(key)
        if current['commercial'].get('siie_offer_id'):
            for key in ('siie_source_revision', 'source_checked_at'):
                incoming['commercial'][key] = current['commercial'][key]
    baseline = ExtractedProgram.model_validate(previous["values"]).model_dump() if previous else ExtractedProgram().model_dump()
    merged, manual = merge_reviewed(current, baseline, incoming)
    for key in ("siie_program_id", "siie_offer_id", "siie_period_id", "siie_campus_id", "siie_shift_id", "siie_source_revision", "source_checked_at"):
        if source["kind"] == "offer" or key in {"siie_program_id", "siie_source_revision", "source_checked_at"}:
            merged["commercial"][key] = incoming["commercial"][key]
    try:
        result = ExtractedProgram.model_validate(merged)
    except ValidationError:
        raise HTTPException(409, "siie_local_finance_conflict") from None
    return result, [v for v in manual if not v.startswith("commercial.siie_") and v != "commercial.source_checked_at"]
