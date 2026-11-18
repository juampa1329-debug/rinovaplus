"""Native PostgreSQL mail domain. Explicit operator migration; SMTP outside SQL locks."""

import base64
import hashlib
import io
import json
import os
import re
import smtplib
import ssl
from html import unescape
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.policy import SMTP as SMTP_POLICY
from email.utils import format_datetime
from uuid import uuid4

from fastapi import HTTPException, Request
from PIL import Image
from pydantic import Field

from app.institutional.auth import authorize, rate
from app.institutional.crypto import seal, unseal
from app.institutional.db import (
    audit,
    institution,
    key,
    one,
    record_operation,
    replay,
    rows,
    uid,
)
from app.institutional.email_policy import (
    DEFAULT_HTML,
    EVENTS,
    VARIABLES,
    address,
    fail,
    header,
    next_run,
    render,
    template,
)
from app.institutional.models import Strict
from app.institutional.store import transaction

KINDS = {"transport", "template", "rule", "group", "schedule", "preference"}
DEFAULT_TRANSPORT = {
    "enabled": False,
    "sender": "notificaciones@rinovaplus.com",
    "name": "RinovaPlus · CBN",
    "reply_to": "",
    "daily_limit": 100,
    "recovery_enabled": False,
}


def enabled(s):
    return bool(
        getattr(s, "postgres_deployment", False)
        and os.environ.get("CRM_EMAIL_SCHEMA_ENABLED") == "1"
    )


def native(c, sql, *params):
    c.native(sql, *params)
    names = [v[0].lower() for v in c.description]
    return [dict(zip(names, row)) for row in c.fetchall()]


def documents(c, s, kind=None):
    return native(
        c,
        "SELECT kind,id,revision,body,updated_at FROM rinova_notify.document WHERE institution=%s "
        + ("AND kind=%s " if kind else "")
        + "ORDER BY kind,id",
        institution(s),
        *((kind,) if kind else ()),
    )


def document(c, s, kind, identity):
    found = native(
        c,
        "SELECT kind,id,revision,body FROM rinova_notify.document WHERE institution=%s AND kind=%s AND id=%s",
        institution(s),
        kind,
        identity,
    )
    return (
        found[0] if found else {"kind": kind, "id": identity, "revision": 0, "body": {}}
    )


def transport(c, s):
    return {**DEFAULT_TRANSPORT, **document(c, s, "transport", "main")["body"]}


def users(c, s):
    return rows(
        c,
        "SELECT u.UserId,u.Login,u.DisplayName,u.Active,u.RoleKey,r.Actions FROM crm_access.AccessUser u JOIN crm_access.Role r ON r.InstitutionId=u.InstitutionId AND r.RoleKey=u.RoleKey WHERE u.InstitutionId=? AND r.Active=1",
        institution(s),
    )


def permitted(person, action):
    return bool(
        person
        and person["Active"]
        and (action == "self" or action in json.loads(person["Actions"]))
    )


def validate(kind, body):
    body = dict(body)
    fields = {
        "transport": {
            "enabled",
            "sender",
            "name",
            "reply_to",
            "daily_limit",
            "recovery_enabled",
        },
        "template": {"name", "subject", "html", "published", "signature"},
        "rule": {
            "name",
            "event",
            "enabled",
            "users",
            "roles",
            "groups",
            "template",
            "severity",
            "channel",
            "account",
            "module",
        },
        "group": {"name", "users"},
        "schedule": {
            "name",
            "enabled",
            "frequency",
            "time",
            "zone",
            "weekday",
            "users",
            "roles",
            "groups",
            "template",
        },
        "preference": {"disabled_events"},
    }
    if kind not in fields or set(body) - fields[kind]:
        fail("email_invalid_configuration")
    for field in ("enabled", "published", "recovery_enabled"):
        if field in body and type(body[field]) is not bool:
            fail("email_invalid_configuration")
    for field in ("name", "subject"):
        if field in body:
            header(body[field])
    for field in ("users", "roles", "groups", "disabled_events"):
        if field in body and (
            not isinstance(body[field], list)
            or len(body[field]) > 100
            or any(not isinstance(x, str) or len(x) > 100 for x in body[field])
        ):
            fail("email_invalid_configuration")
    if kind == "transport":
        body = {**DEFAULT_TRANSPORT, **body}
        address(body["sender"])
        if body["reply_to"]:
            address(body["reply_to"])
        if (
            type(body["daily_limit"]) is not int
            or not 1 <= body["daily_limit"] <= 10000
        ):
            fail("email_invalid_daily_limit")
    if kind == "template":
        header(body.get("subject", ""))
        body["html"] = template(body.get("html", ""))
        body["signature"] = template(
            body.get("signature", "<p>Corporación Bolivariana del Norte — CBN</p>")
        )
        if set(re.findall(r"{{\s*([a-z_]+)\s*}}", body["subject"])) - VARIABLES:
            fail("email_unknown_variable")
    if kind == "rule" and body.get("event") not in EVENTS:
        fail("email_unknown_event")
    if kind == "preference" and set(body.get("disabled_events", [])) - EVENTS.keys():
        fail("email_unknown_event")
    if kind == "schedule":
        if (
            any(not isinstance(body.get(k), str) for k in ("zone", "time", "frequency"))
            or type(body.get("weekday", 0)) is not int
        ):
            fail("email_invalid_schedule")
        next_run(
            datetime.now(timezone.utc),
            body.get("zone", ""),
            body.get("time", ""),
            body.get("frequency", ""),
            body.get("weekday", 0),
        )
    return body


def selected_users(c, s, rule, action, event):
    ids = set(rule.get("users", []))
    for group in documents(c, s, "group"):
        if group["id"] in rule.get("groups", []):
            ids.update(group["body"].get("users", []))
    prefs = {v["id"]: v["body"] for v in documents(c, s, "preference")}
    return [
        v
        for v in users(c, s)
        if permitted(v, action)
        and (v["UserId"] in ids or v["RoleKey"] in rule.get("roles", []))
        and event not in prefs.get(v["UserId"], {}).get("disabled_events", [])
    ]


def recipient_allowed(person, action, recipient, event):
    return permitted(person, action) and (
        event == "mail.test" or address(person["Login"]) == recipient
    )


def validate_activation(c, s, kind, value):
    if kind not in {"rule", "schedule"} or not value.get("enabled"):
        return
    source = document(c, s, "template", value.get("template", ""))["body"]
    if not source.get("published"):
        fail("email_template_not_published")
    if not any(value.get(field) for field in ("users", "roles", "groups")):
        fail("email_recipient_selection_required")


def enqueue(
    c, s, event, dedup, recipient, values, *, user_id=None, source=None, expires=86400
):
    """Payload (including one-time links) is AES-GCM bound to DB, institution and ID."""
    recipient = address(recipient)
    identity = str(uuid4())
    cfg = transport(c, s)
    source = source or {
        "subject": "{{evento}} · RinovaPlus",
        "html": DEFAULT_HTML.replace(
            "Abrir RinovaPlus",
            {
                "user.invited": "Activar mi cuenta",
                "password.reset": "Crear nueva contraseña",
            }.get(event, "Abrir RinovaPlus"),
        ),
        "signature": "<p>Corporación Bolivariana del Norte — CBN</p>",
    }
    values = {
        "nombre": "equipo CBN",
        "evento": EVENTS[event][0],
        "detalle": "Hay una novedad en RinovaPlus. Consulta el CRM con tu cuenta personal.",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "enlace": s.public_origin + "/#/settings/notifications",
        "institucion": "Corporación Bolivariana del Norte — CBN",
        "periodo": "",
        **values,
    }
    html = render(source["html"] + source.get("signature", ""), values)
    subject = re.sub(
        r"{{\s*([a-z_]+)\s*}}", lambda m: str(values[m[1]]), source["subject"]
    )
    header(subject)
    payload = {
        "html": html,
        "subject": subject,
        "sender": cfg["sender"],
        "name": cfg["name"],
        "reply_to": cfg["reply_to"],
    }
    nonce, cipher = seal(
        key(s),
        {
            "db": s.connection["database"],
            "institution": institution(s),
            "mail": identity,
        },
        json.dumps(payload),
    )
    c.native(
        "INSERT INTO rinova_notify.outbox(institution,id,dedup,event,recipient,user_id,required_action,nonce,ciphertext,state,message_id,expires_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'queued',%s,now()+%s*interval '1 second') ON CONFLICT(institution,dedup,recipient) DO NOTHING",
        institution(s),
        identity,
        dedup,
        event,
        recipient,
        user_id,
        EVENTS[event][1],
        nonce,
        cipher,
        f"<{identity}@{cfg['sender'].split('@')[1]}>",
        expires,
    )
    return identity if c.rowcount else None


def emit(c, s, action, resource="", **context):
    """Same transaction as product audit: no provider IO and no historical replay."""
    if not enabled(s):
        return
    if action.startswith("settings.") and action.endswith(".write"):
        context["module"] = resource
        action = "settings.save"
    context.setdefault("severity", "info")
    if action == "channels.create":
        account = one(
            c,
            "SELECT Channel FROM crm_channels2.Integration WHERE InstitutionId=? AND IntegrationId=?",
            institution(s),
            resource,
        )
        if account:
            context.update(
                channel=account["Channel"], account=resource, module="channels"
            )
    if action not in EVENTS or action in {
        "mail.test",
        "password.reset",
        "user.invited",
    }:
        return
    for rule in documents(c, s, "rule"):
        value = rule["body"]
        if not value.get("enabled") or value.get("event") != action:
            continue
        if any(
            value.get(k) and value[k] != context.get(k)
            for k in ("channel", "account", "module", "severity")
        ):
            continue
        source = document(c, s, "template", value.get("template", ""))["body"]
        if not source.get("published"):
            continue
        stamp = str(uuid4())
        for person in selected_users(c, s, value, EVENTS[action][1], action):
            enqueue(
                c,
                s,
                action,
                f"event:{stamp}:{rule['id']}",
                person["Login"],
                {
                    "nombre": person["DisplayName"],
                    "detalle": f"{EVENTS[action][0]}. Área: {context.get('module', 'institución')}. Revisa el detalle y las acciones disponibles en RinovaPlus.",
                },
                user_id=person["UserId"],
                source=source,
            )


def observe_service(c, s, scope, *, failed, module="ai", channel="", account=""):
    """Notify only failure/recovery transitions, rather than every failing request."""
    if not enabled(s):
        return
    cursor_key = "service:" + scope
    previous = c.native(
        "SELECT value FROM rinova_notify.cursor WHERE institution=%s AND key=%s",
        institution(s),
        cursor_key,
    ).fetchval()
    was_failed = bool(previous and previous.get("failed"))
    if failed != was_failed:
        emit(
            c,
            s,
            "operations.failure" if failed else "operations.recovered",
            scope,
            module=module,
            channel=channel,
            account=account,
            severity="error" if failed else "info",
        )
    c.native(
        "INSERT INTO rinova_notify.cursor(institution,key,value) VALUES(%s,%s,%s::jsonb) ON CONFLICT(institution,key) DO UPDATE SET value=EXCLUDED.value",
        institution(s),
        cursor_key,
        json.dumps({"failed": failed}),
    )


def smtp_configuration():
    host = os.environ.get("CRM_SMTP_HOST", "")
    if not re.fullmatch(
        r"smtp\.email\.[a-z0-9-]+\.oci\.oraclecloud\.com", host
    ) or not all(os.environ.get(v) for v in ("CRM_SMTP_USERNAME", "CRM_SMTP_PASSWORD")):
        raise HTTPException(503, "email_provider_not_configured")
    return host, os.environ["CRM_SMTP_USERNAME"], os.environ["CRM_SMTP_PASSWORD"]


def smtp_send(message, recipient):
    """No debug output. SMTP accepted is deliberately not called inbox delivery."""
    host, username, password = smtp_configuration()
    phase = "connect"
    try:
        with smtplib.SMTP(host, 587, timeout=20) as client:
            client.ehlo()
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
            client.login(username, password)
            code, _ = client.mail(str(message["From"].addresses[0].addr_spec))
            if code != 250:
                return (
                    "retry" if 400 <= code < 500 else "failed"
                ), f"smtp_sender_{code}"
            code, _ = client.rcpt(recipient)
            if code not in (250, 251):
                return (
                    "retry" if 400 <= code < 500 else "failed"
                ), f"smtp_recipient_{code}"
            phase = "data"
            code, _ = client.data(message.as_bytes(policy=SMTP_POLICY))
            phase = "accepted" if code == 250 else "rejected"
            return (
                ("accepted", None)
                if code == 250
                else (("retry" if 400 <= code < 500 else "failed"), f"smtp_data_{code}")
            )
    except smtplib.SMTPResponseException as error:
        if phase == "accepted":
            return "accepted", None
        return (
            "retry" if 400 <= error.smtp_code < 500 else "failed"
        ), f"smtp_{error.smtp_code}"
    except (OSError, smtplib.SMTPException):
        if phase == "accepted":
            return "accepted", None
        return (
            "uncertain" if phase == "data" else "retry"
        ), "smtp_result_unknown" if phase == "data" else "smtp_connection_failed"


def build_message(c, s, item):
    payload = json.loads(
        unseal(
            key(s),
            {
                "db": s.connection["database"],
                "institution": institution(s),
                "mail": item["id"],
            },
            item["nonce"],
            item["ciphertext"],
        )
    )
    from email.headerregistry import Address

    message = EmailMessage()
    message["From"] = Address(
        display_name=header(payload["name"]), addr_spec=address(payload["sender"])
    )
    message["To"] = address(item["recipient"])
    message["Subject"] = header(payload["subject"])
    message["Message-ID"] = item["message_id"]
    message["Date"] = format_datetime(datetime.now(timezone.utc))
    message["X-Rinova-Mail-ID"] = item["id"]
    if payload["reply_to"]:
        message["Reply-To"] = address(payload["reply_to"])
    plain = re.sub(
        r'<a\b[^>]*\bhref="([^"]+)"[^>]*>(.*?)</a>',
        lambda match: match[2] + "\n" + match[1],
        payload["html"],
        flags=re.DOTALL,
    )
    message.set_content(unescape(re.sub(r"<[^>]*>", " ", plain)))
    message.add_alternative(payload["html"], subtype="html")
    for asset in set(re.findall(r"cid:([a-f0-9-]{36})", payload["html"])):
        found = native(
            c,
            "SELECT mime,content FROM rinova_notify.asset WHERE institution=%s AND id=%s",
            institution(s),
            asset,
        )
        if not found:
            fail("email_asset_not_found")
        message.get_payload()[1].add_related(
            found[0]["content"],
            maintype="image",
            subtype=found[0]["mime"].split("/")[1],
            cid=f"<{asset}>",
        )
    if len(message.as_bytes(policy=SMTP_POLICY)) > 2_000_000:
        fail("email_message_too_large")
    return message


class Worker:
    def __init__(self, settings, send=smtp_send):
        self.s, self.send = settings, send

    def once(self):
        s = self.s
        if not enabled(s):
            return False
        with transaction(s, True, anonymous=True) as c:
            c.native(
                "UPDATE rinova_notify.outbox SET state='uncertain',error='worker_interrupted',updated_at=now() WHERE institution=%s AND state='sending' AND lease_until<now()",
                institution(s),
            )
            cfg = transport(c, s)
            if not cfg["enabled"] or os.environ.get("CRM_EMAIL_ENABLED") != "1":
                return False
            smtp_configuration()
            due_reports(c, s)
            c.native(
                "UPDATE rinova_notify.outbox SET state='failed',error='expired',updated_at=now() WHERE institution=%s AND state IN('queued','retry') AND expires_at<now()",
                institution(s),
            )
            used = c.native(
                "SELECT count(*) FROM rinova_notify.outbox WHERE institution=%s AND attempts>0 AND updated_at>date_trunc('day',now())",
                institution(s),
            ).fetchval()
            if used >= cfg["daily_limit"]:
                return False
            items = native(
                c,
                "SELECT * FROM rinova_notify.outbox WHERE institution=%s AND state IN('queued','retry') AND next_at<=now() ORDER BY next_at,id LIMIT 1 FOR UPDATE SKIP LOCKED",
                institution(s),
            )
            if not items:
                return False
            item = items[0]
            person = next(
                (v for v in users(c, s) if v["UserId"] == item["user_id"]), None
            )
            suppressed = c.native(
                "SELECT count(*) FROM rinova_notify.outbox WHERE institution=%s AND recipient=%s AND state='bounced'",
                institution(s),
                item["recipient"],
            ).fetchval()
            allowed = recipient_allowed(
                person, item["required_action"], item["recipient"], item["event"]
            )
            prefs = document(c, s, "preference", item["user_id"] or "")["body"]
            if (
                suppressed
                or not allowed
                or (
                    item["event"] in prefs.get("disabled_events", [])
                    and item["event"] not in {"password.reset", "user.invited"}
                )
            ):
                c.native(
                    "UPDATE rinova_notify.outbox SET state='suppressed',error='recipient_not_authorized',updated_at=now() WHERE id=%s",
                    item["id"],
                )
                return True
            try:
                message = build_message(c, s, item)
            except Exception:
                # An invalid/corrupt payload must not block every subsequent mail.
                # Do not log decrypted contents or token-bearing links.
                c.native(
                    "UPDATE rinova_notify.outbox SET state='failed',error='email_payload_invalid',updated_at=now() WHERE id=%s AND institution=%s",
                    item["id"],
                    institution(s),
                )
                return True
            c.native(
                "UPDATE rinova_notify.outbox SET state='sending',attempts=attempts+1,lease_until=now()+interval '5 minutes',updated_at=now() WHERE id=%s",
                item["id"],
            )
        state, error = self.send(message, item["recipient"])
        if state == "retry" and item["attempts"] >= 4:
            state = "failed"
        with transaction(s, True, anonymous=True) as c:
            c.native(
                "UPDATE rinova_notify.outbox SET state=%s,error=%s,next_at=now()+%s*interval '1 second',lease_until=NULL,updated_at=now() WHERE id=%s AND institution=%s AND state='sending'",
                state,
                error,
                min(3600, 60 * 2 ** item["attempts"]),
                item["id"],
                institution(s),
            )
        return True


def due_reports(c, s):
    now = datetime.now(timezone.utc)
    for value in documents(c, s, "schedule"):
        body = value["body"]
        if not body.get("enabled"):
            continue
        key_name = "schedule:" + value["id"] + ":" + str(value["revision"])
        previous = c.native(
            "SELECT value FROM rinova_notify.cursor WHERE institution=%s AND key=%s",
            institution(s),
            key_name,
        ).fetchval()
        if not previous:
            due = next_run(
                now,
                body["zone"],
                body["time"],
                body["frequency"],
                body.get("weekday", 0),
            )
        else:
            due = datetime.fromisoformat(previous["next"])
        if due <= now:
            event = "report." + body["frequency"]
            source = document(c, s, "template", body.get("template", ""))["body"]
            if source.get("published"):
                start = due - timedelta(days=7 if body["frequency"] == "weekly" else 1)
                totals = c.execute(
                    "SELECT COUNT(*) FROM crm_access.Audit WHERE InstitutionId=? AND OccurredAt>=? AND OccurredAt<?",
                    institution(s),
                    start,
                    due,
                ).fetchval()
                for person in selected_users(c, s, body, "users.manage", event):
                    enqueue(
                        c,
                        s,
                        event,
                        f"report:{key_name}:{due.isoformat()}",
                        person["Login"],
                        {
                            "nombre": person["DisplayName"],
                            "periodo": f"{start.isoformat()} / {due.isoformat()}",
                            "detalle": f"Actividad institucional registrada en el período: {totals} eventos de auditoría. Consulta los detalles con tus permisos en RinovaPlus.",
                        },
                        user_id=person["UserId"],
                        source=source,
                    )
            due = next_run(
                now,
                body["zone"],
                body["time"],
                body["frequency"],
                body.get("weekday", 0),
            )
        c.native(
            "INSERT INTO rinova_notify.cursor(institution,key,value) VALUES(%s,%s,%s::jsonb) ON CONFLICT(institution,key) DO UPDATE SET value=EXCLUDED.value",
            institution(s),
            key_name,
            json.dumps({"next": due.isoformat()}),
        )


class Save(Strict):
    revision: int = Field(ge=0)
    body: dict


class Test(Strict):
    operation_id: str
    recipient: str
    template: str = ""


class Preview(Strict):
    html: str = Field(max_length=100000)
    values: dict[str, str]


class Recovery(Strict):
    email: str = Field(max_length=254)


class Receipt(Strict):
    id: str = Field(max_length=200)
    mail_id: str
    action: str
    observed_at: str = Field(max_length=40)


class Asset(Strict):
    name: str = Field(max_length=120)
    content: str = Field(max_length=1400000)


class Invite(Strict):
    operation_id: str


class Audience(Strict):
    rule: dict


def install(app, s):
    def require():
        if not enabled(s):
            raise HTTPException(503, "email_migration_required")

    @app.get("/api/institution/notifications/preferences")
    def preferences(request: Request):
        with transaction(s, anonymous=True) as c:
            actor = authorize(c, s, request.state.authority, "self")
            current = (
                document(c, s, "preference", actor["UserId"])
                if enabled(s)
                else {"body": {}, "revision": 0}
            )
            return {
                **current,
                "available": enabled(s),
                "events": {
                    k: v[0]
                    for k, v in EVENTS.items()
                    if k not in {"password.reset", "user.invited", "mail.test"}
                },
            }

    @app.post("/api/institution/notifications/audience")
    def audience(request: Request, body: Audience):
        require()
        rule = validate("rule", body.rule)
        with transaction(s, anonymous=True) as c:
            authorize(c, s, request.state.authority, "users.manage")
            values = selected_users(c, s, rule, EVENTS[rule["event"]][1], rule["event"])
            return {
                "items": [
                    {"name": v["DisplayName"], "email": v["Login"]} for v in values
                ],
                "count": len(values),
            }

    @app.get("/api/institution/notifications")
    def read(request: Request):
        with transaction(s, anonymous=True) as c:
            authorize(c, s, request.state.authority, "users.manage")
            if not enabled(s):
                return {
                    "available": False,
                    "documents": [],
                    "history": [],
                    "users": [],
                    "assets": [],
                    "events": EVENTS,
                    "configured": False,
                }
            result = {
                "available": True,
                "documents": documents(c, s),
                "events": EVENTS,
                "variables": sorted(VARIABLES),
                "users": [
                    {
                        "id": v["UserId"],
                        "name": v["DisplayName"],
                        "email": v["Login"],
                        "role": v["RoleKey"],
                        "active": bool(v["Active"]),
                    }
                    for v in users(c, s)
                ],
                "history": native(
                    c,
                    "SELECT id,event,recipient,state,attempts,error,message_id,created_at,updated_at FROM rinova_notify.outbox WHERE institution=%s ORDER BY created_at DESC LIMIT 100",
                    institution(s),
                ),
                "assets": native(
                    c,
                    "SELECT id,name,mime,sha256 FROM rinova_notify.asset WHERE institution=%s ORDER BY created_at DESC LIMIT 100",
                    institution(s),
                ),
                "enabled": os.environ.get("CRM_EMAIL_ENABLED") == "1",
                "transport": transport(c, s),
            }
            try:
                smtp_configuration()
                result["configured"] = True
            except HTTPException:
                result["configured"] = False
            return result

    @app.put("/api/institution/notifications/documents/{kind}/{identity}")
    def save(request: Request, kind: str, identity: str, body: Save):
        require()
        if kind not in KINDS or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", identity):
            fail("email_invalid_configuration")
        value = validate(kind, body.body)
        with transaction(s, True, anonymous=True) as c:
            actor = authorize(
                c,
                s,
                request.state.authority,
                "self" if kind == "preference" else "users.manage",
                recent=kind != "preference",
            )
            if kind == "preference" and identity != actor["UserId"]:
                raise HTTPException(403, "permission_denied")
            if kind == "transport" and identity != "main":
                fail("email_invalid_configuration")
            current = document(c, s, kind, identity)
            if current["revision"] != body.revision:
                raise HTTPException(409, "revision_conflict")
            revision = body.revision + 1
            validate_activation(c, s, kind, value)
            if kind == "template":
                for asset in set(
                    re.findall(
                        r"cid:([a-f0-9-]{36})", value["html"] + value["signature"]
                    )
                ):
                    if not c.native(
                        "SELECT 1 FROM rinova_notify.asset WHERE institution=%s AND id=%s",
                        institution(s),
                        asset,
                    ).fetchval():
                        fail("email_asset_not_found")
            encoded = json.dumps(value)
            c.native(
                "INSERT INTO rinova_notify.document(institution,kind,id,revision,body,actor) VALUES(%s,%s,%s,%s,%s::jsonb,%s) ON CONFLICT(institution,kind,id) DO UPDATE SET revision=EXCLUDED.revision,body=EXCLUDED.body,actor=EXCLUDED.actor,updated_at=now()",
                institution(s),
                kind,
                identity,
                revision,
                encoded,
                actor["UserId"],
            )
            c.native(
                "INSERT INTO rinova_notify.history(institution,kind,id,revision,body,actor) VALUES(%s,%s,%s,%s,%s::jsonb,%s)",
                institution(s),
                kind,
                identity,
                revision,
                encoded,
                actor["UserId"],
            )
            audit(
                c,
                s,
                actor["UserId"],
                "notifications.configure",
                identity,
                kind=kind,
                revision=revision,
            )
        return {"revision": revision}

    @app.get("/api/institution/notifications/documents/{kind}/{identity}/history")
    def versions(request: Request, kind: str, identity: str):
        require()
        with transaction(s, anonymous=True) as c:
            authorize(c, s, request.state.authority, "users.manage")
            return {
                "items": native(
                    c,
                    "SELECT revision,body,created_at FROM rinova_notify.history WHERE institution=%s AND kind=%s AND id=%s ORDER BY revision DESC LIMIT 50",
                    institution(s),
                    kind,
                    identity,
                )
            }

    @app.post("/api/institution/notifications/preview")
    def preview(request: Request, body: Preview):
        with transaction(s, anonymous=True) as c:
            authorize(c, s, request.state.authority, "users.manage")
            html = render(body.html, body.values)
            for asset_id in set(re.findall(r"cid:([a-f0-9-]{36})", html)):
                require()
                found = native(
                    c,
                    "SELECT content FROM rinova_notify.asset WHERE institution=%s AND id=%s",
                    institution(s),
                    asset_id,
                )
                if not found:
                    fail("email_asset_not_found")
                html = html.replace(
                    "cid:" + asset_id,
                    "data:image/png;base64,"
                    + base64.b64encode(found[0]["content"]).decode(),
                )
        return {"html": html}

    @app.post("/api/institution/notifications/test")
    def test(request: Request, body: Test):
        require()
        with transaction(s, True, anonymous=True) as c:
            actor = authorize(
                c, s, request.state.authority, "users.manage", recent=True
            )
            digest, prior = replay(
                c,
                s,
                actor["UserId"],
                uid(body.operation_id),
                "notifications.test",
                "mail",
                body.model_dump(),
            )
            if prior:
                return prior
            cfg = transport(c, s)
            if not cfg["enabled"] or os.environ.get("CRM_EMAIL_ENABLED") != "1":
                raise HTTPException(409, "email_sending_paused")
            smtp_configuration()
            source = (
                document(c, s, "template", body.template)["body"]
                if body.template
                else None
            )
            if body.template and not source:
                fail("email_template_not_found")
            identity = enqueue(
                c,
                s,
                "mail.test",
                "test:" + uid(body.operation_id),
                body.recipient,
                {
                    "detalle": "Prueba autorizada de P15. Este correo comprueba el transporte y la identidad visual de RinovaPlus; no contiene información de estudiantes ni claves de acceso."
                },
                source=source,
                user_id=actor["UserId"],
            )
            audit(
                c, s, actor["UserId"], "notifications.test", identity or "deduplicated"
            )
            result = {"queued": True, "id": identity}
            record_operation(
                c,
                s,
                actor["UserId"],
                uid(body.operation_id),
                "notifications.test",
                "mail",
                digest,
                result,
            )
            return result

    @app.post("/api/institution/notifications/outbox/{identity}/cancel")
    def cancel(request: Request, identity: str):
        require()
        with transaction(s, True, anonymous=True) as c:
            actor = authorize(
                c, s, request.state.authority, "users.manage", recent=True
            )
            c.native(
                "UPDATE rinova_notify.outbox SET state='cancelled',updated_at=now() WHERE institution=%s AND id=%s AND state IN('queued','retry')",
                institution(s),
                uid(identity),
            )
            if c.rowcount != 1:
                raise HTTPException(409, "email_not_cancellable")
            audit(c, s, actor["UserId"], "notifications.cancel", identity)
        return {"cancelled": True}

    @app.post("/api/institution/notifications/receipts")
    def receipt(request: Request, body: Receipt):
        # Explicit operator observation, never presented as an automatic provider webhook.
        require()
        try:
            observed_at = datetime.fromisoformat(
                body.observed_at.replace("Z", "+00:00")
            )
        except ValueError:
            fail("email_invalid_receipt")
        if (
            body.action not in {"relayed", "bounced"}
            or observed_at.tzinfo is None
            or observed_at > datetime.now(timezone.utc) + timedelta(minutes=5)
        ):
            fail("email_invalid_receipt")
        with transaction(s, True, anonymous=True) as c:
            actor = authorize(
                c, s, request.state.authority, "users.manage", recent=True
            )
            item = native(
                c,
                "SELECT id,created_at FROM rinova_notify.outbox WHERE institution=%s AND id=%s AND state IN('accepted','uncertain','relayed','bounced')",
                institution(s),
                uid(body.mail_id),
            )
            if not item or observed_at < item[0]["created_at"]:
                fail("email_invalid_receipt")
            c.native(
                "INSERT INTO rinova_notify.receipt(institution,id,mail_id,action,observed_at) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                institution(s),
                body.id,
                body.mail_id,
                body.action,
                observed_at,
            )
            if c.rowcount:
                c.native(
                    "UPDATE rinova_notify.outbox SET state=%s,updated_at=now() WHERE institution=%s AND id=%s AND state<>'bounced'",
                    body.action,
                    institution(s),
                    body.mail_id,
                )
            audit(
                c,
                s,
                actor["UserId"],
                "notifications.receipt_observed",
                body.mail_id,
                kind=body.action,
            )
        return {"recorded": True, "source": "operator_observation"}

    @app.post("/api/institution/notifications/assets")
    def asset(request: Request, body: Asset):
        require()
        header(body.name)
        try:
            raw = base64.b64decode(body.content, validate=True)
            if len(raw) > 1_000_000:
                raise ValueError
            with Image.open(io.BytesIO(raw)) as image:
                if (
                    image.format not in {"PNG", "JPEG", "WEBP"}
                    or max(image.size) > 2048
                    or image.n_frames != 1
                ):
                    raise ValueError
                image.load()
                clean = io.BytesIO()
                image.convert("RGBA").save(clean, format="PNG")
                raw = clean.getvalue()
                if len(raw) > 1_000_000:
                    raise ValueError
        except Exception:
            fail("email_invalid_image")
        with transaction(s, True, anonymous=True) as c:
            actor = authorize(
                c, s, request.state.authority, "users.manage", recent=True
            )
            total = c.native(
                "SELECT coalesce(sum(octet_length(content)),0) FROM rinova_notify.asset WHERE institution=%s",
                institution(s),
            ).fetchval()
            if total + len(raw) > 20_000_000:
                fail("email_asset_quota")
            identity = str(uuid4())
            c.native(
                "INSERT INTO rinova_notify.asset(institution,id,name,mime,content,sha256,actor) VALUES(%s,%s,%s,'image/png',%s,%s,%s)",
                institution(s),
                identity,
                body.name,
                raw,
                hashlib.sha256(raw).hexdigest(),
                actor["UserId"],
            )
            return {"id": identity, "src": "cid:" + identity}

    @app.post("/api/institution/auth/recover-email")
    def recover(body: Recovery, request: Request):
        # Same result for absent/disabled accounts and disabled transport; no reset token in response.
        if enabled(s):
            with transaction(s, True, anonymous=True) as c:
                ip = request.client.host if request.client else "unknown"
                ip_ok = rate(c, s, "email-recovery-ip:" + ip, 5, 900)
                account_ok = rate(
                    c,
                    s,
                    "email-recovery-account:" + body.email.strip().lower(),
                    3,
                    3600,
                )
                cfg = transport(c, s)
                if (
                    ip_ok
                    and account_ok
                    and cfg["enabled"]
                    and cfg["recovery_enabled"]
                    and os.environ.get("CRM_EMAIL_ENABLED") == "1"
                ):
                    target = one(
                        c,
                        "SELECT * FROM crm_access.AccessUser WHERE InstitutionId=? AND NormalizedLogin=? AND Active=1",
                        institution(s),
                        body.email.strip().lower(),
                    )
                    if target:
                        from app.institutional.management import challenge

                        raw = challenge(c, s, target["UserId"], "reset")
                        enqueue(
                            c,
                            s,
                            "password.reset",
                            "reset:" + str(uuid4()),
                            target["Login"],
                            {
                                "nombre": target["DisplayName"],
                                "detalle": "Solicitaste recuperar tu acceso. El enlace vence en una hora y sólo puede utilizarse una vez. Si no lo solicitaste, ignora este correo. El autenticador sigue siendo necesario si está habilitado.",
                                "enlace": s.public_origin
                                + "/access/redeem#token="
                                + raw,
                            },
                            user_id=target["UserId"],
                            expires=3600,
                        )
        return {
            "message": "Si la cuenta está habilitada y tiene correo configurado, recibirás las instrucciones de recuperación."
        }

    @app.post("/api/institution/notifications/users/{identity}/invite")
    def invite(request: Request, identity: str, body: Invite):
        require()
        with transaction(s, True, anonymous=True) as c:
            actor = authorize(
                c, s, request.state.authority, "users.manage", recent=True
            )
            digest, prior = replay(
                c,
                s,
                actor["UserId"],
                uid(body.operation_id),
                "notifications.invite",
                uid(identity),
                {"user": identity},
            )
            if prior:
                return prior
            target = one(
                c,
                "SELECT * FROM crm_access.AccessUser WHERE InstitutionId=? AND UserId=? AND Active=1",
                institution(s),
                uid(identity),
            )
            from app.institutional.management import challenge, manageable

            if not target:
                raise HTTPException(404, "user_not_found")
            manageable(c, s, actor, target)
            if target["RoleKey"] == "owner" and actor["RoleKey"] != "owner":
                raise HTTPException(403, "owner_required")
            if target["PasswordHash"] is not None:
                raise HTTPException(409, "email_user_already_activated")
            if (
                not transport(c, s)["enabled"]
                or os.environ.get("CRM_EMAIL_ENABLED") != "1"
            ):
                raise HTTPException(409, "email_sending_paused")
            smtp_configuration()
            if not rate(c, s, "mail-invite:" + identity, 3, 3600):
                raise HTTPException(429, "rate_limited")
            raw = challenge(c, s, identity, "invite")
            mail = enqueue(
                c,
                s,
                "user.invited",
                "invite:" + str(uuid4()),
                target["Login"],
                {
                    "nombre": target["DisplayName"],
                    "detalle": "Te invitaron a RinovaPlus. Activa tu cuenta personal con este enlace de un solo uso, válido durante una hora.",
                    "enlace": s.public_origin + "/access/redeem#token=" + raw,
                },
                user_id=identity,
                expires=3600,
            )
            audit(c, s, actor["UserId"], "notifications.invite", identity)
            result = {"queued": True, "id": mail}
            record_operation(
                c,
                s,
                actor["UserId"],
                uid(body.operation_id),
                "notifications.invite",
                uid(identity),
                digest,
                result,
            )
        return result
