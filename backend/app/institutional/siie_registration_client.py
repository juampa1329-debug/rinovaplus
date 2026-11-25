"""Four Registration 2 routes, one existing key, no automatic POST retries."""

import json
import logging
import os
import re
from contextlib import contextmanager
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx2 as httpx
from fastapi import HTTPException

from app.institutional import siie_api
from app.institutional.channel_ingress import strict_json
from app.institutional.program_commercial import approved_url

PATHS = {
    "applicant": "AspiranteRegistro.aspx",
    "registration": "Inscripcion.aspx",
    "documents": "Documentos.aspx",
    "requirements": "DocumentosRequeridos.aspx",
}
MAX_FILE = 10 * 1024 * 1024
MAX_TOTAL = 50 * 1024 * 1024
LOG = logging.getLogger("uvicorn.error")
UNCERTAIN = {
    "commit_outcome_unknown",
    "storage_outcome_unknown",
    "file_cleanup_required",
    "retry_operation",
}
KNOWN_ERRORS = UNCERTAIN | {
    "invalid_request",
    "offer_not_found",
    "student_not_in_offer",
    "offer_not_current",
    "applicant_exists",
    "registration_exists",
    "document_already_received",
    "document_file_exists",
    "file_too_large",
    "request_too_large",
    "unsupported_media_type",
    "unsupported_file_type",
    "unsupported_photo_type",
    "invalid_file_content",
    "initial_document_missing",
    "document_not_in_program",
    "document_not_applicable",
    "unsupported_document_type",
    "storage_not_configured",
    "unauthorized",
    "forbidden",
    "rate_limited",
}


def endpoint(kind):
    if not siie_api.configured("admissions"):
        raise HTTPException(409, "siie_not_configured")
    hosts = {
        v.strip().lower()
        for v in os.getenv("SIIE_API_HOSTS", "siieplus.online").split(",")
        if v.strip()
    }
    base = approved_url(os.environ["SIIE_API_BASE_URL"], hosts).rstrip("/")
    token, _ = siie_api.credential()
    if not 32 <= len(token) <= 8192 or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise HTTPException(409, "siie_credential_invalid")
    return base + "/Api/CRM/v1/" + PATHS[kind], {
        "X-API-Key": token,
        "Accept": "application/json",
    }


def file_type(identity, filename, content):
    if (
        type(identity) is not int
        or not 1 <= identity <= 18
        or not content
        or len(content) > MAX_FILE
    ):
        raise HTTPException(
            413 if len(content) > MAX_FILE else 422, "siie_document_invalid"
        )
    extension = filename.rsplit(".", 1)[-1].lower()
    valid = {
        "pdf": content.startswith(b"%PDF-"),
        "png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "jpg": content.startswith(b"\xff\xd8\xff"),
        "jpeg": content.startswith(b"\xff\xd8\xff"),
    }
    if (
        extension not in valid
        or not valid[extension]
        or identity == 5
        and extension == "pdf"
    ):
        raise HTTPException(415, "siie_document_invalid_type")
    return extension, {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }[extension]


def files_for(files):
    if (
        len(files) > 18
        or sum(len(v[2]) for v in files) > MAX_TOTAL
        or len({v[0] for v in files}) != len(files)
    ):
        raise HTTPException(413, "siie_document_limits")
    result = []
    for identity, filename, content in files:
        extension, mime = file_type(identity, filename, content)
        # Only a generated safe name/extension crosses the remote boundary.
        result.append(
            (
                f"documentos[{identity}]",
                (f"documento-{identity}.{extension}", content, mime),
            )
        )
    return result


def _reference(value):
    return value if re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value) else None


@contextmanager
def response_for(client, method, url, headers, kwargs):
    with client.stream(method, url, headers=headers, **kwargs) as response:
        if method == "GET" and response.status_code == 301:
            actual = urlsplit(str(response.url))
            target = urlsplit(
                urljoin(str(response.url), response.headers.get("Location", ""))
            )
            # ASP.NET Friendly URLs: same origin, exact extensionless path,
            # same query (or omitted query which we restore). No POST replay.
            if (
                actual.path.endswith(".aspx")
                and target.scheme == actual.scheme
                and target.netloc == actual.netloc
                and target.path == actual.path[:-5]
                and target.query in {"", actual.query}
                and not target.fragment
            ):
                response.close()
                destination = urlunsplit(
                    (actual.scheme, actual.netloc, target.path, "", "")
                )
                with client.stream(
                    method, destination, headers=headers, **kwargs
                ) as redirected:
                    yield redirected
                return
        yield response


def request(kind, payload, files=(), *, transport=None):
    url, headers = endpoint(kind)
    method = "GET" if kind == "requirements" else "POST"
    file_parts = files_for(files)
    params = {k: str(v) for k, v in payload.items()} if method == "GET" else None
    kwargs = {"params": params} if method == "GET" else {"json": payload}
    if file_parts:
        kwargs = {
            "data": {"datos": json.dumps(payload, ensure_ascii=False)}
            if kind == "registration"
            else {k: str(v) for k, v in payload.items()},
            "files": file_parts,
        }
    read_status = None
    reference = None
    try:
        with httpx.Client(
            timeout=httpx.Timeout(30, connect=5),
            trust_env=False,
            follow_redirects=False,
            transport=transport,
        ) as client:
            with response_for(client, method, url, headers, kwargs) as response:
                read_status = response.status_code
                reference = _reference(response.headers.get("X-Correlation-ID", ""))
                if method == "GET" and response.status_code != 200:
                    detail = {
                        401: "siie_registration_access_rejected",
                        403: "siie_registration_access_rejected",
                        404: "siie_registration_route_not_found",
                        429: "siie_registration_rate_limited",
                        301: "siie_registration_read_redirect",
                        302: "siie_registration_read_redirect",
                    }.get(response.status_code, "siie_registration_source_unavailable")
                    LOG.warning(
                        "siie_registration_read_failed kind=%s status=%s reason=%s",
                        kind,
                        read_status,
                        detail,
                    )
                    raise HTTPException(
                        502,
                        detail,
                        headers={"X-SIIE-Correlation-ID": reference}
                        if reference
                        else None,
                    )
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 524288:
                        raise ValueError("oversized_response")
                value = strict_json(raw)
                if not isinstance(value, dict):
                    raise ValueError("invalid_response")
                if (
                    response.status_code == (200 if method == "GET" else 201)
                    and value.get("status") == "ok"
                    and isinstance(value.get("data"), dict)
                ):
                    data = value["data"]
                    if kind == "requirements":
                        if (
                            not isinstance(data.get("oferta"), dict)
                            or not isinstance(data.get("items"), list)
                            or len(data["items"]) > 200
                        ):
                            LOG.warning(
                                "siie_requirements_shape oferta_type=%s items_type=%s",
                                type(data.get("oferta")).__name__,
                                type(data.get("items")).__name__,
                            )
                            raise ValueError("invalid_requirements")
                        for item in data["items"]:
                            if not isinstance(item, dict):
                                raise ValueError("invalid_requirements")
                            siie_api.positive(item.get("idDocumento"))
                            if (
                                not isinstance(item.get("nombre"), str)
                                or not 1 <= len(item["nombre"]) <= 200
                                or any(
                                    type(item.get(k)) is not bool
                                    for k in (
                                        "obligatorioAlInscribir",
                                        "soportado",
                                    )
                                )
                                or any(
                                    item.get(k) is not None
                                    and type(item[k]) is not bool
                                    for k in ("recibido", "archivoExistente")
                                )
                                or item.get("aplica") is not None
                                and type(item["aplica"]) is not bool
                            ):
                                LOG.warning(
                                    "siie_requirements_item_types nombre=%s obligatorio=%s soportado=%s recibido=%s archivo=%s aplica=%s",
                                    type(item.get("nombre")).__name__,
                                    type(item.get("obligatorioAlInscribir")).__name__,
                                    type(item.get("soportado")).__name__,
                                    type(item.get("recibido")).__name__,
                                    type(item.get("archivoExistente")).__name__,
                                    type(item.get("aplica")).__name__,
                                )
                                raise ValueError("invalid_requirements")
                    else:
                        for name in ("idOferta", "idPeriodo") + (
                            ("idAspirante",)
                            if kind == "applicant"
                            else ("idEstudiante",)
                        ):
                            siie_api.positive(data.get(name))
                            if name in payload and str(data[name]) != str(
                                payload[name]
                            ):
                                raise ValueError("response_scope_changed")
                        if kind == "registration":
                            siie_api.positive(data.get("idInscripcion"))
                        if (
                            "documento" in payload
                            and data.get("documento") != payload["documento"]
                        ):
                            raise ValueError("response_document_changed")
                        if kind == "registration" and data.get(
                            "documento"
                        ) != payload.get("estudiante", {}).get("Id_DocEstudiante"):
                            raise ValueError("response_document_changed")
                    return {
                        "state": "confirmed",
                        "data": data,
                        "correlation_id": reference,
                        "code": "ok",
                    }
                code = (
                    value.get("code")
                    if value.get("code") in KNOWN_ERRORS
                    else "siie_registration_rejected"
                )
                if method == "GET":
                    raise HTTPException(
                        502,
                        "siie_registration_read_failed",
                        headers={"X-SIIE-Correlation-ID": reference}
                        if reference
                        else None,
                    )
                state = (
                    "conflict"
                    if response.status_code == 409
                    else "rejected"
                    if response.status_code in {400, 401, 403, 404, 413, 415, 422, 429}
                    else "uncertain"
                )
                if code in UNCERTAIN:
                    state = "uncertain"
                # No response body, file paths, database error or student data in errors.
                return {
                    "state": state,
                    "data": {},
                    "http_status": response.status_code,
                    "code": code,
                    "correlation_id": reference,
                }
    except (
        httpx.HTTPError,
        ValueError,
        TypeError,
        RecursionError,
        UnicodeError,
        HTTPException,
    ) as error:
        if method == "GET":
            if isinstance(error, HTTPException):
                raise
            reason = (
                str(error)
                if type(error) is ValueError
                and str(error)
                in {"invalid_requirements", "invalid_response", "oversized_response"}
                else type(error).__name__
            )
            LOG.warning(
                "siie_registration_read_failed kind=%s status=%s reason=%s",
                kind,
                read_status,
                reason,
            )
            raise HTTPException(
                502,
                "siie_registration_invalid_response"
                if read_status == 200
                else "siie_registration_read_failed",
            ) from None
        return {
            "state": "uncertain",
            "data": {},
            "code": "siie_write_outcome_unknown",
            "correlation_id": None,
        }


def offer_context(selection):
    programs = siie_api.read(
        "programs", {"cursor": selection.get("program_cursor", "")}
    )["data"]
    program = next(
        (
            v
            for v in programs["items"]
            if str(v.get("program_id")) == str(selection["program_id"])
        ),
        None,
    )
    if not program:
        raise HTTPException(409, "siie_offer_selection_changed")
    period = str(programs.get("period_id") or "")
    offers = siie_api.read(
        "offers",
        {
            "program_id": str(selection["program_id"]),
            "period_id": period,
            "cursor": selection.get("offer_cursor", ""),
        },
    )["data"]
    offer = next(
        (v for v in offers["items"] if v.get("offer_id") == selection["offer_ref"]),
        None,
    )
    if (
        not offer
        or offer.get("active") is not True
        or str(offer.get("period_id")) != str(offers.get("offered_period_id"))
    ):
        raise HTTPException(409, "siie_offer_selection_changed")
    return {
        "idOferta": int(siie_api.positive(offer.get("source_offer_id"))),
        "idPeriodo": int(siie_api.positive(offer.get("period_id"))),
        "program_name": str(program.get("name", "")),
        "schedule": str(offer.get("schedule") or ""),
        "shift_id": offer.get("shift_id"),
        "selection": selection,
    }


def document_types(*, transport=None):
    """The one additional catalog route documented in API_INVENTORY.md."""
    url, headers = endpoint("requirements")
    url = (
        url.rsplit("/Api/CRM/v1/", 1)[0]
        + "/Api/Preinscripciones/v1/TiposDocumento.aspx"
    )
    try:
        with httpx.Client(
            timeout=httpx.Timeout(15, connect=5),
            trust_env=False,
            follow_redirects=False,
            transport=transport,
        ) as client:
            for attempt in range(2):
                with client.stream("GET", url, headers=headers) as response:
                    # The inventory documents ASP.NET Friendly URL's same-path
                    # 301. Never follow a different host/path with the API key.
                    if attempt == 0 and response.status_code == 301:
                        from urllib.parse import urljoin

                        target = urljoin(url, response.headers.get("Location", ""))
                        if target != url.removesuffix(".aspx"):
                            raise ValueError("catalog_redirect_rejected")
                        url = target
                        continue
                    if response.status_code != 200:
                        raise ValueError("catalog_unavailable")
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 524288:
                            raise ValueError("catalog_too_large")
                    value = strict_json(raw)
                    data = value.get("data") if isinstance(value, dict) else None
                    items = data.get("items") if isinstance(data, dict) else data
                    if (
                        value.get("status") != "ok"
                        or not isinstance(items, list)
                        or len(items) > 500
                    ):
                        raise ValueError("catalog_invalid")
                    result = []
                    for item in items:
                        # Native labels verified in SIIE's public catalog; still
                        # read the authoritative list through its protected API.
                        identity, label = (
                            item.get("Identificacion", item.get("id")),
                            item.get("Abreviatura", item.get("nombre")),
                        )
                        if (
                            str(identity) == "0"
                            and isinstance(label, str)
                            and label.startswith("SELECCIONE")
                        ):
                            continue
                        siie_api.positive(identity)
                        if not isinstance(label, str) or not 1 <= len(label) <= 100:
                            raise ValueError("catalog_invalid")
                        result.append({"value": int(identity), "label": label})
                    if len({v["value"] for v in result}) != len(result):
                        raise ValueError("catalog_duplicate_identity")
                    return result
    except (ValueError, TypeError, AttributeError, HTTPException, httpx.HTTPError):
        raise HTTPException(502, "siie_registration_catalog_unavailable") from None
    raise HTTPException(502, "siie_registration_catalog_unavailable")
