"""SIIE ASPX contract: bounded server-to-server reads, no automatic writes."""

import json
import os
import re
from datetime import datetime, timezone

import httpx2 as httpx
from fastapi import HTTPException, Request

from app.institutional.program_commercial import approved_url

ROUTES = {
    "programs": ("catalog", "Commercial/Programs.aspx"),
    "offers": ("catalog", "Commercial/ProgramOffers.aspx"),
    "offer": ("catalog", "Commercial/Offer.aspx"),
    "periods": ("admissions", "Periodos.aspx"),
    "states": ("admissions", "EstadosSeguimiento.aspx"),
    "filters": ("admissions", "FiltrosAdmisiones.aspx"),
    "applicants": ("admissions", "Aspirantes.aspx"),
    "applicant": ("admissions", "Aspirante.aspx"),
    "history": ("admissions", "HistorialSeguimiento.aspx"),
    "students": ("admissions", "Estudiantes.aspx"),
    "student": ("admissions", "Estudiante.aspx"),
    "student_filters": ("admissions", "FiltrosEstudiantes.aspx"),
}
TOKEN = "SIIE_API_TOKEN"


def credential():
    # One authority for every CRM read. Presence, including an empty value,
    # overrides the old Catalog setting so a failed rotation cannot fall back.
    if TOKEN in os.environ:
        return os.environ[TOKEN].strip(), "unified"
    return os.getenv("SIIE_CATALOG_API_TOKEN", "").strip(), "legacy_catalog"


def configured(scope):
    if scope not in {"catalog", "admissions"}:
        raise ValueError("unknown SIIE scope")
    return bool(
        os.getenv("SIIE_API_BASE_URL", "").strip()
        and credential()[0]
    )


def status():
    return {
        "api_configured": configured("catalog"),
        "credential_mode": credential()[1],
        "catalog_configured": configured("catalog"),
        "admissions_configured": configured("admissions"),
        "read_only": True,
        "students_supported": True,
        "student_balances_supported": False,
        "followup_writes_enabled": False,
        "contract": "siie-crm-commercial-v1 / CRM ASPX / single-key 2026-11-19",
    }


def positive(value):
    if isinstance(value, bool) or not re.fullmatch(r"[1-9][0-9]{0,9}", str(value)):
        raise HTTPException(422, "siie_invalid_parameter")
    number = int(value)
    if number > 2147483647:
        raise HTTPException(422, "siie_invalid_parameter")
    return str(number)


def parameters(route, values):
    """Only documented parameters. Never accept a URL or repeated query keys."""
    allowed = {
        "programs": {"cursor", "period_id"},
        "offers": {"program_id", "period_id", "cursor"},
        "offer": {"offer_id"},
        "periods": {"incluirHistoricos"},
        "states": set(),
        "filters": {"idPeriodo"},
        "applicants": {"idPeriodo", "idPrograma", "idJornada", "q", "offset"},
        "applicant": {"idPeriodo", "idAspirante"},
        "history": {"idPeriodo", "idAspirante", "offset"},
        "students": {
            "idPeriodo",
            "idPrograma",
            "idJornada",
            "idEstadoMatricula",
            "q",
            "offset",
        },
        "student": {"idPeriodo", "idEstudiante"},
        "student_filters": {"idPeriodo"},
    }
    required = {
        "offers": {"program_id"},
        "offer": {"offer_id"},
        "applicant": {"idAspirante"},
        "history": {"idAspirante"},
        "student": {"idEstudiante"},
    }
    if route not in ROUTES or set(values) - allowed[route]:
        raise HTTPException(422, "siie_invalid_parameter")
    out = {k: v for k, v in values.items() if v is not None and v != ""}
    if required.get(route, set()) - set(out):
        raise HTTPException(422, "siie_invalid_parameter")
    for key, value in out.items():
        if key == "offer_id":
            match = re.fullmatch(r"([1-9][0-9]{0,9})-n([1-9][0-9]{0,3})", str(value))
            if not match:
                raise HTTPException(422, "siie_invalid_parameter")
            positive(match[1])
        elif key == "cursor":
            if (
                not isinstance(value, str)
                or len(value) > 128
                or any(ord(c) < 32 for c in value)
            ):
                raise HTTPException(422, "siie_invalid_parameter")
        elif key == "q":
            if not isinstance(value, str) or len(value.strip()) > 100:
                raise HTTPException(422, "siie_invalid_parameter")
            out[key] = value.strip()
        elif key == "incluirHistoricos":
            if isinstance(value, bool) or str(value) != "1":
                raise HTTPException(422, "siie_invalid_parameter")
        elif key in {"offset", "idEstadoMatricula"}:
            if (
                isinstance(value, bool)
                or not re.fullmatch(r"[0-9]{1,10}", str(value))
                or int(value) > (1000000 if key == "offset" else 2147483647)
            ):
                raise HTTPException(422, "siie_invalid_parameter")
            out[key] = str(int(value))
        else:
            out[key] = positive(value)
    return out


def _invalid():
    raise HTTPException(502, "siie_catalog_invalid_response")


def _fresh(value):
    if (
        value.get("schema_version") != "siie-crm-commercial-v1"
        or value.get("source_system") != "DBSIIE"
        or not re.fullmatch(
            r"sha256:[0-9a-fA-F]{64}", str(value.get("source_revision", ""))
        )
    ):
        _invalid()
    try:
        generated = datetime.fromisoformat(value["generated_at"].replace("Z", "+00:00"))
        if (
            generated.tzinfo is None
            or abs((datetime.now(timezone.utc) - generated).total_seconds()) > 86400
        ):
            raise ValueError("stale")
    except (ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(409, "siie_catalog_stale_or_mismatched") from None


def _quality(value):
    if not isinstance(value, list) or len(value) > 200:
        _invalid()
    for item in value:
        if not isinstance(item, dict) or any(
            not isinstance(item.get(k), str) or len(item[k]) > 2000
            for k in ("field", "code", "message")
        ):
            _invalid()
    return value


def period_binding(actual, requested=None):
    if actual is None:
        raise HTTPException(409, "siie_period_contract_required")
    try:
        canonical = positive(actual)
    except HTTPException:
        _invalid()
    if requested is not None and canonical != str(requested):
        raise HTTPException(409, "siie_catalog_stale_or_mismatched")
    return canonical


def normalize(route, query, value, code):
    if not isinstance(value, dict):
        _invalid()
    if route in {"programs", "offers", "offer"}:
        if code == 422:
            if (
                route != "offer"
                or value.get("code") != "source_data_incomplete"
                or value.get("quotable") is not False
            ):
                raise HTTPException(502, "siie_source_incomplete")
            partial = value.get("partial_offer")
            if (
                not isinstance(partial, dict)
                or partial.get("offer_id") != query["offer_id"]
                or partial.get("quotable") is not False
            ):
                _invalid()
            _fresh(partial)
            _quality(value.get("data_quality"))
            return {
                "complete": False,
                "quotable": False,
                "offer": partial,
                "data_quality": value["data_quality"],
                "saved": False,
                "siie_written": False,
                "review_required": True,
            }
        _fresh(value)
        if route == "offer":
            if value.get("offer_id") != query["offer_id"]:
                raise HTTPException(409, "siie_catalog_stale_or_mismatched")
            # Inspection is deliberately separate from approved CRM program facts.
            return {
                "complete": True,
                "quotable": value.get("quotable") is True,
                "offer": value,
                "data_quality": _quality(value.get("data_quality", [])),
                "saved": False,
                "siie_written": False,
                "review_required": True,
            }
        if (
            not isinstance(value.get("items"), list)
            or len(value["items"]) > 25
            or any(not isinstance(x, dict) for x in value["items"])
        ):
            _invalid()
        cursor = value.get("next_cursor")
        if cursor is not None and (
            not isinstance(cursor, str) or not cursor or len(cursor) > 128
        ):
            _invalid()
        if value.get("pagination") != "keyset_live_catalog":
            _invalid()
        period_binding(value.get("period_id"), query.get("period_id"))
        if route == "offers" and value.get("program_id") != query["program_id"]:
            raise HTTPException(409, "siie_catalog_stale_or_mismatched")
        return value
    data = value.get("data")
    if value.get("status") != "ok" or not isinstance(data, dict):
        _invalid()
    if route == "student_filters":
        for name in ("programas", "jornadas", "estadosMatricula"):
            values = data.get(name)
            if (
                not isinstance(values, list)
                or len(values) > 10000
                or any(not isinstance(v, dict) for v in values)
            ):
                _invalid()
        if not isinstance(data.get("niveles"), list) or len(data["niveles"]) > 1000:
            _invalid()
        if data.get("idPeriodo") is not None:
            period_binding(data["idPeriodo"], query.get("idPeriodo"))
    elif route == "student":
        item = data.get("estudiante")
        enrollments = data.get("matriculas")
        if (
            not isinstance(item, dict)
            or str(item.get("idEstudiante")) != query["idEstudiante"]
            or not isinstance(enrollments, list)
            or not enrollments
            or len(enrollments) > 1000
        ):
            _invalid()
        effective = data.get(
            "idPeriodo",
            enrollments[0].get("idPeriodo")
            if isinstance(enrollments[0], dict)
            else None,
        )
        period_binding(effective, query.get("idPeriodo"))
        for enrollment in enrollments:
            if (
                not isinstance(enrollment, dict)
                or str(enrollment.get("idPeriodo")) != str(effective)
                or (
                    "idEstudiante" in enrollment
                    and str(enrollment["idEstudiante"]) != query["idEstudiante"]
                )
            ):
                raise HTTPException(409, "siie_catalog_stale_or_mismatched")
    elif route == "applicant":
        item = data.get("aspirante")
        if (
            not isinstance(item, dict)
            or str(item.get("idAspirante")) != query["idAspirante"]
        ):
            raise HTTPException(409, "siie_catalog_stale_or_mismatched")
        period_binding(item.get("idPeriodo"), query.get("idPeriodo"))
    else:
        items = data.get("items")
        if (
            not isinstance(items, list)
            or len(items)
            > (25 if route in {"applicants", "history", "students"} else 10000)
            or any(not isinstance(x, dict) for x in items)
        ):
            _invalid()
        if route in {"applicants", "history", "students"}:
            if (
                type(data.get("hasMore")) is not bool
                or type(data.get("limit")) is not int
                or data["limit"] != 25
                or data.get("offset") != int(query.get("offset", 0))
            ):
                _invalid()
        if route == "students":
            effective = period_binding(data.get("idPeriodo"), query.get("idPeriodo"))
            seen = set()
            for item in items:
                identity = (
                    positive(item.get("idEstudiante")),
                    positive(item.get("idMatricula")),
                )
                if (
                    identity in seen
                    or str(item.get("idPeriodo", effective)) != effective
                ):
                    raise HTTPException(409, "siie_catalog_stale_or_mismatched")
                seen.add(identity)
        if route == "applicants":
            expected = query.get("idPeriodo") or data.get("idPeriodo")
            for item in items:
                actual = period_binding(item.get("idPeriodo"), expected)
                expected = expected or actual
    return data


def read(route, values=None, *, transport=None):
    query = parameters(route, values or {})
    scope, path = ROUTES[route]
    if not configured(scope):
        raise HTTPException(409, "siie_not_configured")
    hosts = {
        v.strip().lower()
        for v in os.getenv("SIIE_API_HOSTS", "siieplus.online").split(",")
        if v.strip()
    }
    try:
        base = approved_url(os.environ["SIIE_API_BASE_URL"], hosts).rstrip("/")
    except HTTPException:
        raise HTTPException(409, "siie_catalog_endpoint_invalid") from None
    key, _ = credential()
    if len(key) < 32 or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise HTTPException(409, "siie_credential_invalid")
    try:
        with httpx.Client(
            timeout=httpx.Timeout(15, connect=5),
            trust_env=False,
            follow_redirects=False,
            transport=transport,
        ) as client:
            with client.stream(
                "GET",
                base + "/Api/CRM/v1/" + path,
                params=query,
                headers={"X-API-Key": key, "Accept": "application/json"},
            ) as response:
                if response.status_code in {401, 403}:
                    raise HTTPException(502, "siie_catalog_access_rejected")
                if response.status_code == 404:
                    raise HTTPException(404, "siie_reference_not_found")
                if response.status_code == 429:
                    wait = response.headers.get("Retry-After", "60")
                    wait = str(min(max(int(wait), 1), 3600)) if wait.isdigit() else "60"
                    raise HTTPException(
                        429, "siie_rate_limited", headers={"Retry-After": wait}
                    )
                if response.status_code not in (
                    {200, 422, 400, 503} if route == "offer" else {200, 400, 503}
                ):
                    raise HTTPException(502, "siie_catalog_unavailable")
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 524288:
                        _invalid()
                value = json.loads(raw, parse_constant=lambda _: _invalid())
                if response.status_code in {400, 503}:
                    source_code = value.get("code") if isinstance(value, dict) else None
                    known = {
                        "offered_period_unavailable": "siie_offered_period_unavailable",
                        "invalid_cursor": "siie_cursor_changed",
                        "students_unavailable": "siie_students_unavailable",
                        "api_credential_not_configured": "siie_source_credential_configuration",
                        "api_credential_config_invalid": "siie_source_credential_configuration",
                        "api_credential_config_conflict": "siie_source_credential_configuration",
                    }
                    raise HTTPException(
                        502, known.get(source_code, "siie_catalog_unavailable")
                    )
                result = normalize(route, query, value, response.status_code)
                correlation = response.headers.get("X-Correlation-ID", "")
                correlation = (
                    correlation
                    if re.fullmatch(r"[A-Za-z0-9_-]{1,100}", correlation)
                    else None
                )
                return {
                    "data": result,
                    "correlation_id": correlation,
                    "read_only": True,
                    "source": "SIIE",
                    "saved": False,
                }
    except (ValueError, RecursionError, UnicodeError):
        raise HTTPException(502, "siie_catalog_invalid_response") from None
    except httpx.HTTPError:
        raise HTTPException(502, "siie_catalog_unavailable") from None


def install(app, service):
    """agents.manage and current SQL/module checks precede every outbound read."""
    prefix = "/api/v1/agents/siie"

    @app.get(prefix + "/status")
    def connection_status():
        with service.transaction():
            return status()

    @app.get(prefix + "/{route}")
    def query_source(route: str, request: Request):
        if route not in ROUTES:
            raise HTTPException(404, "siie_reference_not_found")
        pairs = list(request.query_params.multi_items())
        if len({key for key, _ in pairs}) != len(pairs):
            raise HTTPException(422, "siie_invalid_parameter")
        with service.transaction():
            pass
        result = read(route, dict(pairs))
        # Recheck authority after IO, before exposing remote personal information.
        with service.transaction():
            pass
        return result
