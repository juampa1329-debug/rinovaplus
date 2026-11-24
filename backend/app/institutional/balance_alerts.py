"""Read-only account monitor; durable cadence and one mail per low-balance episode."""

import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4

from app.institutional.crypto import unseal
from app.institutional.db import institution, key, one, uid
from app.institutional import email_notifications as mail
from app.institutional.provider_balances import safe_credits
from app.institutional.settings import setting
from app.institutional.store import transaction
from app.modules.ai.infrastructure.providers import AiError, ProviderGateway

CURSOR = "provider-balance:openrouter"


def state(c, s):
    return c.native("SELECT value FROM rinova_notify.cursor WHERE institution=%s AND key=%s", institution(s), CURSOR).fetchval() or {}


def save(c, s, value):
    c.native("INSERT INTO rinova_notify.cursor(institution,key,value) VALUES(%s,%s,%s::jsonb) ON CONFLICT(institution,key) DO UPDATE SET value=EXCLUDED.value", institution(s), CURSOR, json.dumps(value))


def secret_row(c, s):
    return one(c, "SELECT SecretId,VersionNo,Nonce,Ciphertext FROM crm_access.Secret WHERE InstitutionId=? AND Scope='provider' AND OwnerRef='openrouter' AND Kind='management_key' AND State='staged'", institution(s))


def identity(row):
    return [str(row["SecretId"]), row["VersionNo"]] if row else None


async def credits(token, transport=None):
    async with asyncio.timeout(12):
        raw = await ProviderGateway({"openrouter": token}, transport=transport).request("openrouter", "GET", "credits")
        return safe_credits(raw)["remaining"]


def transition(c, s, previous, remaining, threshold):
    """A failed/unknown check never manufactures a zero balance or blocks AI."""
    low = remaining <= threshold
    previous = dict(previous)
    if not low:
        previous.pop("episode", None)
        previous["low"] = False
        return previous, "available"
    if previous.get("low") and previous.get("threshold") == threshold:
        return previous, "low_notified"
    if not mail.transport(c, s)["enabled"]:
        return previous, "mail_disabled"
    admins = [p for p in mail.users(c, s) if mail.permitted(p, "users.manage")]
    if not admins:
        return previous, "no_admin_recipient"
    episode = str(uuid4())
    for person in admins:
        mail.enqueue(c, s, "provider.balance_low", "openrouter-low:" + episode, person["Login"], {
            "nombre": person["DisplayName"],
            "detalle": f"El saldo restante de OpenRouter es USD {remaining:.2f}, igual o inferior al umbral configurado de USD {threshold:.2f}. Revisa la cuenta y recarga directamente en OpenRouter. Esta alerta no detiene las respuestas de IA.",
            "enlace": s.public_origin + "/#/settings/budgets",
        }, user_id=person["UserId"])
    return {**previous, "low": True, "threshold": threshold, "episode": episode}, "low_notified"


class Monitor:
    def __init__(self, settings, fetch=credits):
        self.s, self.fetch = settings, fetch

    def once(self):
        s = self.s
        if not mail.enabled(s):
            return False
        now = datetime.now(timezone.utc).timestamp()
        with transaction(s, True, anonymous=True) as c:
            policy = setting(c, s, "budgets")["document"]
            if not policy.get("openrouter_balance_alert_enabled"):
                return False
            previous = state(c, s)
            if previous.get("next_at", 0) > now:
                return False
            row = secret_row(c, s)
            claim = str(uuid4())
            threshold = policy.get("openrouter_balance_alert_threshold_usd", 5)
            record = {**previous, "claim": claim, "next_at": now + policy.get("openrouter_balance_check_minutes", 15) * 60}
            if previous.get("credential") != identity(row):
                record.pop("low", None)
                record.pop("episode", None)
            record["credential"] = identity(row)
            record["status"] = "checking" if row else "management_key_required"
            save(c, s, record)
            if not row:
                return False
            token = unseal(key(s), {"institution": institution(s), "scope": "provider", "owner": "openrouter", "kind": "management_key", "version": row["VersionNo"], "secret_id": uid(str(row["SecretId"]))}, row["Nonce"], row["Ciphertext"])
        remaining = None
        try:
            remaining = asyncio.run(self.fetch(token))
            status = "available"
        except AiError as error:
            status = "management_key_rejected" if error.upstream_status in {401, 403} else "unavailable"
        except (TimeoutError, OSError):
            status = "unavailable"
        with transaction(s, True, anonymous=True) as c:
            current = state(c, s)
            policy = setting(c, s, "budgets")["document"]
            if current.get("claim") != claim or not policy.get("openrouter_balance_alert_enabled") or policy.get("openrouter_balance_alert_threshold_usd", 5) != threshold or identity(secret_row(c, s)) != identity(row):
                return False
            if remaining is not None:
                current, status = transition(c, s, current, remaining, threshold)
                current["remaining_usd"] = remaining
            current.update(status=status, checked_at=datetime.now(timezone.utc).isoformat())
            save(c, s, current)
        return False


def public_status(c, s):
    value = state(c, s) if mail.enabled(s) else {"status": "mail_unavailable"}
    return {name: value.get(name) for name in ("status", "checked_at", "remaining_usd")}
