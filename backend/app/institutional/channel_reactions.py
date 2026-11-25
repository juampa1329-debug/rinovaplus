"""Read-only reaction context, including verified legacy receipts. Never replay."""

import json
from cryptography.exceptions import InvalidTag

from app.institutional.channel_events import normalize, valid_external
from app.institutional.channel_ingress import body_owner, strict_json
from app.institutional.crypto import unseal
from app.institutional.db import institution, key, rows


def reference(provider):
    if provider.get("type") != "reaction" or not isinstance(provider.get("reaction"), dict):
        return None
    value = provider["reaction"]
    external, emoji = value.get("message_id"), value.get("emoji")
    if not valid_external(external) or not isinstance(emoji, str) or len(emoji) > 32:
        return None
    return {"external": external, "emoji": emoji, "removed": emoji == ""}


def recovered_provider(saved, receipt, settings):
    """Old normalizers omitted reaction fields; inspect only authenticated raw bytes."""
    provider = saved.get("provider") or {}
    if reference(provider):
        return provider
    if provider.get("type") != "reaction" or not receipt.get("BodyCiphertext"):
        return provider
    raw = unseal(key(settings), body_owner(settings, receipt["ReceiptId"], receipt["EndpointId"]),
                 receipt["BodyNonce"], receipt["BodyCiphertext"])
    candidates = normalize("meta", strict_json(raw))
    matching = [v["provider"] for v in candidates if all(v.get(k) == saved.get(k)
                for k in ("channel", "route", "kind", "external", "author"))]
    return matching[0] if len(matching) == 1 else provider


def presentation(value, targets):
    label = "Retiró su reacción" if value["removed"] else "Reaccionó " + value["emoji"]
    result = {"body": label, "reaction": {"emoji": value["emoji"], "removed": value["removed"],
                                           "targetAvailable": len(targets) == 1}}
    if len(targets) == 1:
        target = targets[0]
        result["replyTo"] = {"id": str(target["MessageId"]).lower(), "body": target["Body"][:600],
                             "direction": target["Direction"]}
    else:
        result["body"] += " · mensaje original no disponible"
    return result


def project(c, settings, conversation, messages):
    ids = [v["id"] for v in messages if v["direction"] == "incoming" and v["body"] == "[reaction]"]
    if not ids:
        return {}
    sources = rows(c,
        "SELECT x.MessageId,x.IntegrationId,r.IdentityId,e.Payload,w.ReceiptId,w.EndpointId,w.BodyNonce,w.BodyCiphertext "
        "FROM crm_channels2.ExternalMessage x JOIN crm.Message m ON m.MessageId=x.MessageId "
        "JOIN crm_channels2.MessageRoute r ON r.InstitutionId=x.InstitutionId AND r.IntegrationId=x.IntegrationId AND r.MessageId=x.MessageId "
        "JOIN crm_channels2.WebhookEvent e ON e.InstitutionId=x.InstitutionId AND e.IntegrationId=x.IntegrationId "
        "AND e.ProviderEventId COLLATE Latin1_General_100_BIN2=x.ExternalId AND e.Kind='message' "
        "JOIN crm_channels2.WebhookReceipt w ON w.InstitutionId=e.InstitutionId AND w.ReceiptId=e.ReceiptId AND w.Authentication='verified' "
        "WHERE x.InstitutionId=? AND m.ConversationId=? AND x.MessageId IN(" + ",".join("?" for _ in ids) + ")",
        institution(settings), conversation, *ids)
    result = {}
    for source in sources:
        try:
            value = reference(recovered_provider(json.loads(source["Payload"]), source, settings))
        except (InvalidTag, ValueError, KeyError, TypeError, RecursionError):
            value = None
        message_id = str(source["MessageId"]).lower()
        if not value:
            result[message_id] = {"body": "Reacción · detalle original no disponible"}
            continue
        targets = rows(c,
            "SELECT TOP(2) m.MessageId,m.Body,m.Direction FROM crm.Message m "
            "JOIN crm_channels2.MessageRoute r ON r.MessageId=m.MessageId AND r.InstitutionId=? AND r.IntegrationId=? AND r.IdentityId=? "
            "WHERE m.ConversationId=? AND (EXISTS(SELECT 1 FROM crm_channels2.ExternalMessage x "
            "WHERE x.InstitutionId=r.InstitutionId AND x.IntegrationId=r.IntegrationId AND x.MessageId=m.MessageId "
            "AND x.ExternalId COLLATE Latin1_General_100_BIN2=?) OR EXISTS(SELECT 1 FROM crm_channels2.SendJob q "
            "WHERE q.InstitutionId=r.InstitutionId AND q.IntegrationId=r.IntegrationId AND q.MessageId=m.MessageId "
            "AND q.IdentityId=r.IdentityId AND q.ExternalId COLLATE Latin1_General_100_BIN2=? "
            "AND q.State IN('accepted','sent','delivered','read'))) ORDER BY m.Sequence",
            institution(settings), source["IntegrationId"], source["IdentityId"], conversation, value["external"], value["external"])
        result[message_id] = presentation(value, targets)
    return result
