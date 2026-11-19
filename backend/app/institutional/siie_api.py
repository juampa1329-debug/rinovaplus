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
}
TOKENS = {
    "catalog": "SIIE_CATALOG_API_TOKEN",
    "admissions": "SIIE_ADMISSIONS_API_TOKEN",
}


def configured(scope):
    return bool(
        os.getenv("SIIE_API_BASE_URL", "").strip()
        and os.getenv(TOKENS[scope], "").strip()
    )


def status():
    return {
        "catalog_configured": configured("catalog"),
        "admissions_configured": configured("admissions"),
        "read_only": True,
        "students_supported": False,
        "student_balances_supported": False,
        "followup_writes_enabled": False,
        "contract": "siie-crm-commercial-v1 / Admisiones ASPX",
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
        "programs": {"cursor"},
        "offers": {"program_id", "period_id", "cursor"},
        "offer": {"offer_id"},
        "periods": set(),
        "states": set(),
        "filters": {"idPeriodo"},
        "applicants": {"idPeriodo", "idPrograma", "idJornada", "q", "offset"},
        "applicant": {"idPeriodo", "idAspirante"},
        "history": {"idPeriodo", "idAspirante", "offset"},
    }
    required = {
        "offers": {"program_id"},
        "offer": {"offer_id"},
        "filters": {"idPeriodo"},
        "applicants": {"idPeriodo"},
        "applicant": {"idPeriodo", "idAspirante"},
        "history": {"idPeriodo", "idAspirante"},
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
        elif key == "offset":
            if (
                isinstance(value, bool)
                or not re.fullmatch(r"[0-9]{1,7}", str(value))
                or int(value) > 1000000
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
        if route == "offers" and (
            value.get("program_id") != query["program_id"]
            or value.get("period_id") != query.get("period_id")
        ):
            raise HTTPException(409, "siie_catalog_stale_or_mismatched")
        return value
    data = value.get("data")
    if value.get("status") != "ok" or not isinstance(data, dict):
        _invalid()
    if route == "applicant":
        item = data.get("aspirante")
        if (
            not isinstance(item, dict)
            or str(item.get("idAspirante")) != query["idAspirante"]
            or str(item.get("idPeriodo")) != query["idPeriodo"]
        ):
            raise HTTPException(409, "siie_catalog_stale_or_mismatched")
    else:
        items = data.get("items")
        if (
            not isinstance(items, list)
            or len(items) > (25 if route in {"applicants", "history"} else 10000)
            or any(not isinstance(x, dict) for x in items)
        ):
            _invalid()
        if route in {"applicants", "history"}:
            if (
                type(data.get("hasMore")) is not bool
                or type(data.get("limit")) is not int
                or data["limit"] != 25
                or data.get("offset") != int(query.get("offset", 0))
            ):
                _invalid()
        if route == "applicants" and any(
            str(x.get("idPeriodo")) != query["idPeriodo"] for x in items
        ):
            raise HTTPException(409, "siie_catalog_stale_or_mismatched")
    return data


def read(route, values=None, *, transport=None):
    query = parameters(route, values or {})
    scope, path = ROUTES[route]
    if not configured(scope):
        raise HTTPException(409, "siie_" + scope + "_not_configured")
    hosts = {
        v.strip().lower()
        for v in os.getenv("SIIE_API_HOSTS", "siieplus.online").split(",")
        if v.strip()
    }
    try:
        base = approved_url(os.environ["SIIE_API_BASE_URL"], hosts).rstrip("/")
    except HTTPException:
        raise HTTPException(409, "siie_catalog_endpoint_invalid") from None
    key = os.environ[TOKENS[scope]].strip()
    if any(ord(c) < 33 or ord(c) > 126 for c in key) or (
        scope == "catalog" and len(key) < 32
    ):
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
                    {200, 422} if route == "offer" else {200}
                ):
                    raise HTTPException(502, "siie_catalog_unavailable")
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 524288:
                        _invalid()
                value = json.loads(raw, parse_constant=lambda _: _invalid())
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
