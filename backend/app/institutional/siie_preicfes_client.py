"""Current Pre-ICFES finance contract; no gateway, redirect or POST retry."""

import hashlib
import re
from datetime import datetime, timezone
from uuid import UUID

import httpx2 as httpx
from fastapi import HTTPException

from app.institutional import siie_environment, siie_api
from app.institutional.channel_ingress import strict_json

PATHS = {"registration": "Inscripcion", "binding": "Conversacion", "plans": "Plan",
         "assign": "Plan", "order": "Volante", "operation": "ConsultaOperacion",
         "pdf": "VolantePdf", "payment": "PagoEstado"}
WRITES = {"binding", "assign", "order"}
IDS = ("idInscripcion", "idEstudiante", "idOferta", "idPeriodo")
CONTEXT = (*IDS, "bindingId", "conversationId", "channelAccountId")
PDF_PATH = "Api/CRM/v1/PreIcfes/VolantePdf.aspx"
HEX = re.compile(r"[0-9a-f]{64}\Z")
MAX_PDF = 1048576


def positive(value):
    if type(value) is not int or not 1 <= value <= 2147483647:
        raise ValueError("invalid_positive_integer")
    return value


def uuid(value):
    return str(UUID(value))


def future(value):
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.tzinfo is None or instant <= datetime.now(timezone.utc):
        raise HTTPException(409, "siie_finance_expired")
    return instant


def parameters(kind, values):
    if kind not in PATHS:
        raise HTTPException(404, "siie_finance_route_not_found")
    required = set(IDS if kind == "registration" else CONTEXT)
    if kind == "binding":
        required = set(IDS) | {"waId", "eventId", "conversationId", "channelAccountId", "requestId"}
    if kind == "assign":
        required |= {"planId", "mode", "quoteRevisionId", "requestId"}
    if kind == "order":
        required |= {"assignmentId", "installmentId", "requestId"}
    if kind in {"pdf", "payment"}:
        required.add("orderId")
    if kind == "pdf":
        required.add("pdfVersion")
    if kind == "operation":
        required |= {"requestId", "operation"}
        if values.get("operation") == "Conversacion":
            required.discard("bindingId")
    if set(values) != required:
        raise HTTPException(422, "siie_finance_invalid_parameter")
    try:
        for name, value in values.items():
            if name in IDS or name in {"planId", "assignmentId", "installmentId"}:
                positive(value)
            elif name in {"bindingId", "requestId", "eventId", "orderId"}:
                uuid(value)
            elif name in {"quoteRevisionId", "pdfVersion"}:
                if not isinstance(value, str) or not HEX.fullmatch(value):
                    raise ValueError()
            elif name == "mode":
                if value not in {"CONTADO", "FINANCIADO"}:
                    raise ValueError()
            elif name == "operation":
                if value not in {"Conversacion", "Plan", "Volante"}:
                    raise ValueError()
            elif name == "waId":
                if not isinstance(value, str) or not re.fullmatch(r"\+?[1-9][0-9]{7,14}", value):
                    raise ValueError()
            elif not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", value):
                raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(422, "siie_finance_invalid_parameter") from None
    return dict(values)


def validate(kind, data, payload):
    if not isinstance(data, dict):
        raise ValueError()
    if kind != "payment":
        if positive(data.get("idInscripcion")) != payload["idInscripcion"]:
            raise ValueError()
    if kind == "registration":
        if any(data.get(k) != payload[k] for k in IDS) or data.get("status") != "registration_confirmed":
            raise ValueError()
        if not all(isinstance(data.get(k), str) and data[k] for k in ("documento", "celular", "studentName")):
            raise ValueError()
    elif kind == "binding":
        uuid(data["bindingId"]); future(data["expiresAtUtc"])
        if (data.get("verificationBasis") != "trusted_crm_sender_attestation_and_siie_phone_match" or
                any(data.get(k) != payload[k] for k in ("conversationId", "channelAccountId"))):
            raise ValueError()
    elif kind == "plans":
        if data.get("requiresConfiguration") is not False or data.get("canAssign") is not True:
            raise HTTPException(409, "siie_finance_configuration_required")
        if type(data.get("options")) is not list or not 1 <= len(data["options"]) <= 100:
            raise ValueError()
        for option in data["options"]:
            if any(option.get(k) != payload[k] for k in IDS) or option.get("currency") != "COP":
                raise ValueError()
            positive(option["planId"]); positive(option["amountCop"]); positive(option["level"])
            if option.get("mode") not in {"CONTADO", "FINANCIADO"} or not HEX.fullmatch(option["quoteRevisionId"]):
                raise ValueError()
            future(option["expiresAtUtc"])
            installments(option["installments"], native=False)
    elif kind == "assign":
        positive(data["assignmentId"])
        if data.get("state") != "plan_assigned" or data.get("academicEnrollmentApplied") is not False or data.get("paymentConfirmed") is not False:
            raise ValueError()
        plan = data["plan"]
        if any(plan.get(k) != payload[k] for k in ("planId", "mode", "quoteRevisionId")):
            raise ValueError()
        installments(plan["installments"], native=True)
    elif kind == "order":
        uuid(data["orderId"]); positive(data["amountCop"])
        if (data.get("state") != "issued" or data.get("currency") != "COP" or
                any(data.get(k) != payload[k] for k in ("assignmentId", "installmentId"))):
            raise ValueError()
        descriptor(data["pdf"])
    elif kind == "payment":
        if (data.get("state") not in {"pending", "partial", "paid", "requires_review"} or
                data.get("orderId") != payload["orderId"] or data.get("currency") != "COP" or
                type(data.get("paymentConfirmed")) is not bool or
                data["paymentConfirmed"] != (data["state"] == "paid") or
                data.get("verificationBasis") != "verified_non_void_receipts_with_exact_voucher_and_deposit_reference"):
            raise ValueError()
    return data


def installments(values, *, native):
    if not isinstance(values, list) or not 1 <= len(values) <= 100:
        raise ValueError()
    seen = set()
    for item in values:
        positive(item["amountCop"])
        datetime.strptime(item["dueDate"], "%Y-%m-%d")
        if not isinstance(item.get("concept"), str) or not item["concept"]:
            raise ValueError()
        if native:
            identity = positive(item["installmentId"])
            if identity in seen:
                raise ValueError()
            seen.add(identity)


def descriptor(data):
    if (not isinstance(data, dict) or data.get("mime") != "application/pdf" or
            data.get("endpoint") != PDF_PATH or data.get("requiresBinding") is not True or
            data.get("maximumBytes") != MAX_PDF or type(data.get("sizeBytes")) is not int or
            not 1 <= data["sizeBytes"] <= MAX_PDF or not HEX.fullmatch(data.get("sha256", "")) or
            data.get("version") != data["sha256"]):
        raise ValueError("invalid_pdf_descriptor")


def request(kind, values, environment, *, pdf=None, transport=None):
    payload = parameters(kind, values)
    env = siie_environment.require(environment)
    token, _ = siie_api.credential()
    if not 32 <= len(token) <= 8192 or any(not 33 <= ord(c) <= 126 for c in token):
        raise HTTPException(409, "siie_credential_invalid")
    method = "POST" if kind in WRITES else "GET"
    try:
        with httpx.Client(timeout=httpx.Timeout(30, connect=5), trust_env=False,
                          follow_redirects=False, transport=transport) as client:
            with client.stream(method, env.endpoint("Api/CRM/v1/PreIcfes/" + PATHS[kind] + ".aspx"),
                               headers={"X-API-Key": token, "Accept": "application/pdf" if pdf else "application/json"},
                               **({"json": payload} if method == "POST" else {"params": payload})) as response:
                if response.status_code != 200:
                    code = "siie_finance_rejected" if response.status_code in {400,401,403,404,405,409,413,415,422} else "siie_finance_unavailable"
                    if method == "POST":
                        return {"state": "rejected" if code.endswith("rejected") else "uncertain", "http_status": response.status_code, "code": code}
                    raise HTTPException(429 if response.status_code == 429 else 502, code,
                        headers={"Retry-After": response.headers["Retry-After"]} if re.fullmatch(r"[0-9]{1,8}",response.headers.get("Retry-After","")) else None)
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > (MAX_PDF if pdf else 524288):
                        raise ValueError()
                if pdf:
                    descriptor(pdf)
                    digest = hashlib.sha256(raw).hexdigest()
                    if (response.headers.get("Content-Type", "").split(";")[0].lower() != "application/pdf" or
                            not response.headers.get("Content-Disposition", "").lower().startswith("attachment") or
                            response.headers.get("Content-Length") != str(len(raw)) or len(raw) != pdf["sizeBytes"] or
                            not raw.startswith(b"%PDF-") or digest != pdf["sha256"] or
                            response.headers.get("X-Content-SHA256") != digest or response.headers.get("X-PDF-Version") != pdf["version"]):
                        raise ValueError()
                    return bytes(raw)
                value = strict_json(raw)
                if (value.get("status") != "ok" or type(value.get("schemaVersion")) is not int or
                        value["schemaVersion"] != 1 or type(value.get("data")) is not dict):
                    raise ValueError()
                data = value["data"]
                if kind == "operation":
                    if (data.get("state") != "confirmed" or data.get("requestId") != payload["requestId"] or
                            data.get("operation") != payload["operation"]):
                        raise ValueError()
                    data = data["result"]
                    original_kind = {"Conversacion":"binding","Plan":"assign","Volante":"order"}[payload["operation"]]
                    # Full validation against the original intent is done by the durable caller.
                    if not isinstance(data, dict) or original_kind not in WRITES:
                        raise ValueError()
                else:
                    validate(kind, data, payload)
                return {"state": "confirmed", "data": data}
    except HTTPException:
        raise
    except (ValueError, KeyError, TypeError, AttributeError, UnicodeError, RecursionError, httpx.HTTPError):
        if method == "POST":
            return {"state": "uncertain", "code": "siie_finance_outcome_unknown"}
        raise HTTPException(502, "siie_finance_invalid_response") from None
