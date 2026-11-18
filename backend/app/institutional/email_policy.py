"""P15 mail inputs, safe HTML and scheduling. No network or storage effects."""

import re
from datetime import datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from fastapi import HTTPException

EVENTS = {
    "mail.test": ("Prueba de correo", "users.manage"),
    "user.invited": ("Invitación de usuario", "self"),
    "password.reset": ("Recuperación de contraseña", "self"),
    "users.create": ("Nuevo usuario", "users.manage"),
    "users.edit": ("Cambio de acceso", "users.manage"),
    "auth.access_redeemed": ("Acceso actualizado", "users.manage"),
    "channels.create": ("Nuevo canal", "settings.channels.read"),
    "agents.create": ("Nuevo agente", "agents.manage"),
    "settings.save": ("Cambio de configuración", "users.manage"),
    "operations.failure": ("Fallo operativo", "users.manage"),
    "operations.recovered": ("Servicio recuperado", "users.manage"),
    "report.daily": ("Informe diario", "users.manage"),
    "report.weekly": ("Informe semanal", "users.manage"),
}
VARIABLES = {"nombre", "evento", "detalle", "fecha", "enlace", "institucion", "periodo"}
DEFAULT_HTML = '<div style="font-family:Arial,Helvetica,sans-serif;background-color:#F5F7F2;color:#12343B;padding:32px;border-radius:16px"><p style="color:#52666B">RinovaPlus · CBN</p><h1 style="font-size:24px">{{evento}}</h1><p>Hola {{nombre}},</p><p>{{detalle}}</p><p>{{fecha}}</p><p><a style="background-color:#C4F04D;color:#12343B;padding:12px;border-radius:8px;text-decoration:none" href="{{enlace}}">Abrir RinovaPlus</a></p><p>{{institucion}}</p></div>'
EMAIL = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}\Z"
)
TOKEN = re.compile(r"{{\s*([a-z_]+)\s*}}")
TAGS = {
    "html",
    "head",
    "body",
    "title",
    "meta",
    "table",
    "thead",
    "tbody",
    "tr",
    "td",
    "th",
    "div",
    "span",
    "p",
    "br",
    "hr",
    "h1",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "strong",
    "b",
    "em",
    "i",
    "a",
    "img",
    "blockquote",
}
ATTRS = {
    "style",
    "class",
    "width",
    "height",
    "align",
    "valign",
    "colspan",
    "rowspan",
    "alt",
    "role",
    "cellpadding",
    "cellspacing",
    "border",
    "lang",
    "dir",
    "charset",
    "name",
    "content",
}
CSS = {
    "color",
    "background-color",
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "line-height",
    "text-align",
    "text-decoration",
    "padding",
    "padding-top",
    "padding-bottom",
    "padding-left",
    "padding-right",
    "margin",
    "margin-top",
    "margin-bottom",
    "border",
    "border-color",
    "border-radius",
    "border-collapse",
    "width",
    "max-width",
    "height",
    "vertical-align",
}


def fail(code):
    raise HTTPException(422, code)


def address(value):
    if not isinstance(value, str) or len(value) > 254 or not EMAIL.fullmatch(value):
        fail("email_invalid_address")
    return value.lower()


def header(value):
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 200
        or any(ord(c) < 32 for c in value)
    ):
        fail("email_invalid_header")
    return value


def safe_link(value):
    if value == "{{enlace}}":
        return value
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        fail("email_unsafe_url")
    return value


class MailHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag not in TAGS:
            fail("email_unsafe_html")
        clean = []
        for key, value in attrs:
            value = value or ""
            if key in {"href", "src"}:
                if (key == "href" and tag != "a") or (key == "src" and tag != "img"):
                    fail("email_unsafe_html")
                if key == "src":
                    # Only authenticated, inspected library assets become MIME CID images.
                    if not re.fullmatch(r"cid:[a-f0-9-]{36}", value):
                        fail("email_image_requires_library")
                else:
                    safe_link(value)
            elif key not in ATTRS:
                fail("email_unsafe_html")
            if key == "style":
                for rule in value.split(";"):
                    if not rule.strip():
                        continue
                    prop, sep, val = rule.partition(":")
                    if (
                        not sep
                        or prop.strip().lower() not in CSS
                        or not re.fullmatch(r"[\w\s#%,.()'\"/+-]+", val)
                        or re.search(r"url|expression|javascript|@|\\", val, re.I)
                    ):
                        fail("email_unsafe_css")
            clean.append(f' {key}="{escape(value, quote=True)}"')
        self.parts.append("<" + tag + "".join(clean) + ">")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag not in TAGS:
            fail("email_unsafe_html")
        self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        self.parts.append(escape(data))

    def handle_decl(self, decl):
        if decl.lower() != "doctype html":
            fail("email_unsafe_html")

    def unknown_decl(self, data):
        fail("email_unsafe_html")


def template(value):
    if not isinstance(value, str) or not 1 <= len(value.encode()) <= 100_000:
        fail("email_template_too_large")
    if set(TOKEN.findall(value)) - VARIABLES or re.search(r"{{(?:(?!}}).)*$", value):
        fail("email_unknown_variable")
    parser = MailHTML()
    try:
        parser.feed(value)
        parser.close()
    except HTTPException:
        raise
    except Exception:
        fail("email_invalid_html")
    return "".join(parser.parts)


def render(source, values):
    clean = template(source)
    missing = sorted(set(TOKEN.findall(clean)) - values.keys())
    if missing:
        fail("email_missing_variables")
    if "enlace" in values:
        safe_link(str(values["enlace"]))
    return TOKEN.sub(lambda m: escape(str(values[m[1]]), quote=True), clean)


def next_run(now, zone, local_time, frequency, weekday=0):
    """One occurrence per local date; gaps advance, folds choose the first instant."""
    try:
        tz = ZoneInfo(zone)
        hour, minute = map(int, local_time.split(":"))
        if frequency not in {"daily", "weekly"} or not 0 <= weekday <= 6:
            raise ValueError
        for days in range(9):
            day = now.astimezone(tz).date() + timedelta(days=days)
            if frequency == "weekly" and day.weekday() != weekday:
                continue
            candidate = datetime(
                day.year, day.month, day.day, hour, minute, tzinfo=tz, fold=0
            )
            # round-trip moves a nonexistent wall clock through the DST gap.
            candidate = candidate.astimezone(timezone.utc).astimezone(tz)
            if candidate.astimezone(timezone.utc) > now:
                return candidate.astimezone(timezone.utc)
    except (ValueError, KeyError):
        fail("email_invalid_schedule")
    fail("email_invalid_schedule")
