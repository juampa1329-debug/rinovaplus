"""Explicit institutional capabilities, independent of subscriptions."""

import re
from contextvars import ContextVar

TARGET = re.compile(r"CBN_P2_(REF|TRIAL|RECOVERY|FAULT)_20261026_([0-9a-f]{8})\Z")
VERSION = "cbn-institutional-p2-v1"
PORT = 4177
SCHEMA = "crm_access"
MODULES = (
    "overview",
    "clients",
    "inbox",
    "channels",
    "assistant",
    "agents",
    "knowledge",
    "memory",
    "broadcasts",
    "campaigns",
    "ads",
    "intelligence",
    "admissions",
    "settings",
)
ACTIONS = (
    "crm.read",
    "crm.write",
    "inbox.read",
    "inbox.write",
    "settings.crm.read",
    "settings.crm.write",
    "settings.institution.read",
    "settings.institution.write",
    "settings.ai.read",
    "settings.ai.write",
    "settings.providers.read",
    "settings.providers.write",
    "settings.channels.read",
    "settings.channels.write",
    "settings.webhooks.read",
    "settings.webhooks.write",
    "settings.modules.read",
    "settings.modules.write",
    "settings.budgets.read",
    "settings.budgets.write",
    "users.read",
    "users.manage",
    "roles.read",
    "roles.manage",
    "sessions.manage",
    "audit.read",
    "agents.manage",
    "sources.manage",
    "campaigns.manage",
    "ads.manage",
)
ROLE_ACTIONS = {
    "owner": ACTIONS,
    "admin": ACTIONS,
    "supervisor": tuple(
        a
        for a in ACTIONS
        if a
        not in {
            "users.manage",
            "roles.manage",
            "sessions.manage",
            "settings.providers.write",
            "settings.budgets.write",
        }
    ),
    "agent": (
        "crm.read",
        "crm.write",
        "inbox.read",
        "inbox.write",
        "settings.crm.read",
    ),
    "viewer": ("crm.read", "inbox.read", "settings.crm.read"),
}
ROLE_LABELS = {
    "owner": "Propietario",
    "admin": "Administrador",
    "supervisor": "Supervisor",
    "agent": "Asesor",
    "viewer": "Consulta",
}
READY = {"overview", "clients", "inbox", "channels", "settings"}
request_authority = ContextVar("institutional_request_authority", default=None)


def principal(database):
    match = TARGET.fullmatch(database)
    if not match:
        raise ValueError("P2_target_required")
    return "cbn_institutional_p2_" + match[2]
