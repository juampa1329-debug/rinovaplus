"""Template components, explicit variable bindings and fixed-account Meta requests."""

import hashlib
import json
import re
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException

from app.institutional.db import institution, one, rows, uid
from app.institutional.models import public_url
from app.modules.channels import providers

TOKEN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


def binding_content(items):
    # Meta returns HEADER before BODY. Component order is independent; button
    # order and all actual text/format/URL fields remain significant.
    clean = [{k: v for k, v in item.items() if k != "example"} for item in items]
    return sorted(clean, key=lambda v: v.get("type", ""))


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def normalize(text):
    names = []

    def replace(match):
        name = match[1].strip()
        if name not in names:
            names.append(name)
        return "{{" + str(names.index(name) + 1) + "}}"

    normalized = TOKEN.sub(replace, text)
    if "{{" in TOKEN.sub("", normalized) or "}}" in TOKEN.sub("", normalized):
        raise HTTPException(422, "template_placeholder_invalid")
    return normalized, names


def definition(body):
    text, names = normalize(body.body_text)
    used_examples = {f"body.{n + 1}" for n in range(len(names))}
    result = [{"type": "BODY", "text": text}]
    if names:
        result[0]["example"] = {
            "body_text": [[body.examples.get(f"body.{n + 1}", "Ejemplo " + str(n + 1)) for n in range(len(names))]]
        }
    if body.header_type == "TEXT":
        if not body.header_text.strip():
            raise HTTPException(422, "template_header_required")
        value, names = normalize(body.header_text)
        used_examples.update(f"header.{n + 1}" for n in range(len(names)))
        if len(names) > 1:
            raise HTTPException(422, "template_header_one_variable")
        header = {"type": "HEADER", "format": "TEXT", "text": value}
        if names:
            header["example"] = {
                "header_text": [body.examples.get(f"header.{n + 1}", "Ejemplo " + str(n + 1)) for n in range(len(names))]
            }
        result.append(header)
    elif body.header_type:
        if not body.header_media_handle:
            raise HTTPException(422, "template_media_example_required")
        result.append(
            {
                "type": "HEADER",
                "format": body.header_type,
                "example": {"header_handle": [body.header_media_handle]},
            }
        )
    if body.footer_text:
        if TOKEN.search(body.footer_text):
            raise HTTPException(422, "template_footer_variables_unsupported")
        result.append({"type": "FOOTER", "text": body.footer_text})
    buttons = []
    for item in body.buttons:
        value = {"type": item.type, "text": item.text}
        if item.type == "URL":
            public_url(item.url.replace("{{1}}", "sample"))
            value["url"] = item.url
        elif item.type == "PHONE_NUMBER":
            if not item.phone_number:
                raise HTTPException(422, "template_button_phone_required")
            value["phone_number"] = item.phone_number
        buttons.append(value)
    if buttons:
        result.append({"type": "BUTTONS", "buttons": buttons})
    if not set(body.examples) <= used_examples:
        raise HTTPException(422, "template_example_unused")
    return result


def latest(c, settings, key, version=None):
    suffix = " AND VersionNo=?" if version is not None else ""
    value = one(
        c,
        (
            "SELECT TOP(1) * FROM crm_broadcast7.Te"
            "mplate WHERE InstitutionId=? AND Templ"
            "ateId=?"
        )
        + suffix
        + " ORDER BY VersionNo DESC",
        institution(settings),
        key,
        *([version] if version is not None else []),
    )
    if not value:
        raise HTTPException(404, "broadcast_template_not_found")
    return value


def append(
    c, settings, item, raw, credential, origin, *, key=None, paused=None, observed=None
):
    provider = str(raw["id"])
    name = raw.get("name", "")
    language = raw.get("language", "")
    if (
        not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", provider)
        or not re.fullmatch(r"[a-z][a-z0-9_]{0,127}", name)
        or not re.fullmatch(r"[a-zA-Z_]{2,20}", language)
    ):
        raise HTTPException(502, "template_provider_shape_invalid")
    old = one(
        c,
        (
            "SELECT TOP(1) * FROM crm_broadcast7.Te"
            "mplate WHERE InstitutionId=? AND Integ"
            "rationId=? AND (ProviderId=? OR Name=?"
            " AND Language=?) ORDER BY VersionNo DE"
            "SC"
        ),
        institution(settings),
        item["IntegrationId"],
        provider,
        name,
        language,
    )
    key = key or (uid(str(old["TemplateId"])) if old else str(uuid4()))
    by_key = one(
        c,
        (
            "SELECT TOP(1) * FROM crm_broadcast7.Te"
            "mplate WHERE InstitutionId=? AND Templ"
            "ateId=? ORDER BY VersionNo DESC"
        ),
        institution(settings),
        key,
    )
    old = by_key or old
    paused = bool(old["Paused"]) if paused is None and old else bool(paused)
    version = (old["VersionNo"] if old else 0) + 1
    components = raw.get("components")
    if (
        not isinstance(components, list)
        or len(components) > 10
        or len(encoded(components)) > 50000
    ):
        raise HTTPException(502, "template_provider_shape_invalid")
    material = {
        "definition": components,
        "status": str(raw.get("status", "UNKNOWN")).upper()[:40],
        "name": name,
        "language": language,
        "category": str(raw.get("category", "MARKETING")).upper()[:40],
        "paused": paused,
        "account": bytes(item["RowVersion"]).hex(),
        "credential": uid(str(credential["SecretId"])) if credential else None,
        "origin": origin,
    }
    previous = json.loads(old["ProviderMetadata"]) if old else {}
    epoch = previous.get("material_revision", 0) + (
        previous.get("material_fingerprint") != fingerprint(material)
    )
    quality = raw.get("quality_score", "")
    if isinstance(quality, dict):
        quality = quality.get("score", "")
    rejection = raw.get("rejected_reason", raw.get("rejection_reason", ""))
    rejection = "" if str(rejection).strip().upper() in {"", "NONE", "NULL", "N/A"} else str(rejection)[:1000]
    default_bindings = raw.get("variable_bindings", {})
    recovered_from = None
    if "variable_bindings" not in raw and old:
        old_components = json.loads(old["Definition"])
        if binding_content(old_components) == binding_content(components):
            default_bindings = previous.get("variable_bindings", {})
            if not default_bindings and old["VersionNo"] > 1:
                history = rows(c, "SELECT TOP(20) VersionNo,Definition,ProviderMetadata FROM crm_broadcast7.Template WHERE InstitutionId=? AND IntegrationId=? AND TemplateId=? AND VersionNo<? ORDER BY VersionNo DESC", institution(settings), item["IntegrationId"], key, old["VersionNo"])
                for prior in history:
                    if binding_content(json.loads(prior["Definition"])) != binding_content(components):
                        break
                    candidate = json.loads(prior["ProviderMetadata"]).get("variable_bindings", {})
                    if candidate:
                        default_bindings = candidate
                        recovered_from = prior["VersionNo"]
                        break
    metadata = {
        "material_revision": epoch,
        "material_fingerprint": fingerprint(material),
        "quality_score": str(quality)[:80],
        "rejection_reason": rejection,
        "variable_bindings": default_bindings,
    }
    metadata["allow_category_change"] = raw.get("allow_category_change", True)
    if recovered_from is not None:
        metadata["binding_recovered_from_version"] = recovered_from
    c.execute(
        (
            "INSERT crm_broadcast7.Template(Institu"
            "tionId,TemplateId,VersionNo,Integratio"
            "nId,ProviderId,Name,Language,Category,"
            "ProviderStatus,Origin,Paused,Definitio"
            "n,ProviderMetadata,AccountVersion,Cred"
            "entialId,ObservedAt) VALUES(?,?,?,?,?,"
            "?,?,?,?,?,?,?,?,?,?,?)"
        ),
        institution(settings),
        key,
        version,
        item["IntegrationId"],
        provider,
        name,
        language,
        material["category"],
        material["status"],
        origin,
        paused,
        encoded(components),
        encoded(metadata),
        item["RowVersion"],
        credential["SecretId"] if credential else None,
        observed or datetime.utcnow(),
    )
    return {
        "id": key,
        "version": version,
        "provider_status": material["status"],
        "origin": origin,
    }


def approved(c, settings, campaign, item, *, controlled=False):
    pinned = latest(
        c, settings, str(campaign["TemplateId"]), campaign["TemplateVersion"]
    )
    current = latest(c, settings, str(campaign["TemplateId"]))
    if str(current["IntegrationId"]).lower() != str(item["IntegrationId"]).lower():
        raise HTTPException(409, "broadcast_template_account_mismatch")
    if (
        current["ProviderStatus"] != "APPROVED"
        or current["Paused"]
        or current["Origin"]
        not in ({"provider", "controlled"} if controlled else {"provider"})
    ):
        raise HTTPException(409, "broadcast_provider_approved_template_required")
    if current["ObservedAt"] < datetime.utcnow() - timedelta(hours=1):
        raise HTTPException(409, "broadcast_template_refresh_required")
    if json.loads(pinned["ProviderMetadata"])["material_revision"] != json.loads(
        current["ProviderMetadata"]
    )["material_revision"] or bytes(current["AccountVersion"]) != bytes(
        item["RowVersion"]
    ):
        raise HTTPException(409, "broadcast_template_changed_review_required")
    from app.institutional.channel_provider import provider_account

    _, credential = provider_account(c, settings, item)
    if not same_id(current["CredentialId"], credential["SecretId"]):
        raise HTTPException(409, "broadcast_template_credential_changed")
    return current


def same_id(a, b):
    return str(a).lower() == str(b).lower()


def parameters(template, document, person, campaign_name, *, allowed_custom_fields=()):
    definition = json.loads(template["Definition"])
    bindings = document.get("variables", {})
    used = set()
    body_preview = ""
    values = {
        "customer_name": person["Name"],
        "customer_first_name": person["Name"].split(" ")[0],
        "customer_email": json.loads(person["CustomValues"]).get("email", ""),
        "customer_city": person["City"],
        "customer_phone": person["Phone"],
        "program": person["Program"],
        "stage": person["Stage"],
        "schedule": person["Schedule"],
        "campaign_name": campaign_name,
    }

    def render(text, group):
        params = []
        indexes = sorted(
            set(TOKEN.findall(text)), key=lambda v: int(v) if v.isdigit() else 999
        )
        if indexes and indexes != [str(n + 1) for n in range(len(indexes))]:
            raise HTTPException(409, "broadcast_template_numeric_variables_required")
        rendered = text
        for index in indexes:
            key = group + "." + index
            used.add(key)
            mapping = bindings.get(key)
            if not mapping:
                raise HTTPException(409, "broadcast_variable_required")
            value = (
                mapping.get("value", "")
                if mapping.get("source") == "literal"
                else values.get(mapping.get("source"), "")
            )
            if mapping.get("source") == "custom_field":
                field = mapping.get("field_key", "")
                if field not in allowed_custom_fields:
                    raise HTTPException(409, "broadcast_crm_field_unavailable")
                value = json.loads(person["CustomValues"]).get(field, "")
                if isinstance(value, bool):
                    value = "Sí" if value else "No"
                elif isinstance(value, (int, float)):
                    value = str(value)
            if (
                not isinstance(value, str)
                or not value.strip()
                or len(value.encode("utf-16-le")) > 2000
            ):
                raise HTTPException(409, "broadcast_variable_value_missing")
            params.append({"type": "text", "text": value})
            rendered = re.sub(
                r"\{\{\s*" + re.escape(index) + r"\s*\}\}", lambda _: value, rendered
            )
        return rendered, params

    components = []
    for component in definition:
        kind = component.get("type", "").upper()
        if kind in {"BODY", "HEADER"}:
            media = component.get("format", "TEXT").upper()
            if kind == "HEADER" and media in {"IMAGE", "VIDEO", "DOCUMENT"}:
                link = document.get("header_media_url", "")
                if not link:
                    raise HTTPException(409, "broadcast_header_media_required")
                public_url(link)
                components.append(
                    {
                        "type": "header",
                        "parameters": [
                            {"type": media.lower(), media.lower(): {"link": link}}
                        ],
                    }
                )
            else:
                rendered, params = render(component.get("text", ""), kind.lower())
                if kind == "BODY":
                    body_preview = rendered
                if params:
                    components.append({"type": kind.lower(), "parameters": params})
        elif kind == "BUTTONS":
            for index, button in enumerate(component.get("buttons", [])):
                if button["type"] == "URL" and TOKEN.search(button.get("url", "")):
                    _, params = render(button["url"], "button." + str(index))
                    components.append(
                        {
                            "type": "button",
                            "sub_type": "url",
                            "index": str(index),
                            "parameters": params,
                        }
                    )
                elif button["type"] == "QUICK_REPLY":
                    # Static quick replies need no personalized payload.
                    pass
    if set(bindings) != used:
        raise HTTPException(409, "broadcast_unused_variable_binding")
    return {
        "name": template["Name"],
        "language": {"code": template["Language"]},
        "components": components,
    }, body_preview


def fetch(adapter, request=providers.request):
    found = []
    after = None
    seen = set()
    for page in range(5):
        params = {
            "limit": 100,
            "fields": (
                "id,name,language,category,status,compo"
                "nents,quality_score,rejected_reason"
            ),
        }
        if after:
            params["after"] = after
        result = request(
            adapter,
            "GET",
            adapter["configuration"]["wabaId"] + "/message_templates",
            params=params,
        )
        if not isinstance(result.get("data"), list):
            raise HTTPException(502, "template_provider_shape_invalid")
        found.extend(result["data"])
        paging = result.get("paging", {})
        if not paging.get("next"):
            return found
        after = paging.get("cursors", {}).get("after")
        if (
            not isinstance(after, str)
            or not re.fullmatch(r"[A-Za-z0-9_=+-]{1,512}", after)
            or after in seen
        ):
            raise HTTPException(502, "template_provider_cursor_invalid")
        seen.add(after)
    raise HTTPException(413, "template_catalog_scope_limit")


def send(adapter, payload, *, before_send, request=providers.request, **_):
    # An authenticated, account-scoped read immediately precedes the frontier.
    current = fetch(adapter, request)
    expected = payload["broadcastTemplate"]
    row = next(
        (
            v
            for v in current
            if str(v.get("id")) == expected["provider_id"]
            and v.get("name") == expected["name"]
            and v.get("language") == expected["language"]
        ),
        None,
    )
    if (
        not row
        or row.get("status") != "APPROVED"
        or fingerprint(row.get("components", [])) != expected["components_fingerprint"]
    ):
        raise providers.ProviderFailure("broadcast_provider_template_changed")
    before_send()
    result = request(
        adapter,
        "POST",
        adapter["configuration"]["phoneNumberId"] + "/messages",
        {
            "messaging_product": "whatsapp",
            "to": payload["target"],
            "type": "template",
            "template": payload["template"],
        },
    )
    external = (result.get("messages") or [{}])[0].get("id")
    if not external:
        raise providers.ProviderFailure(
            "provider_acceptance_not_confirmed", uncertain=True
        )
    return str(external)
