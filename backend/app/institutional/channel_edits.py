"""Attributable incoming edits. Keep originals and never replay old provider IO."""

import json

from cryptography.exceptions import InvalidTag

from app.institutional.channel_events import normalize, valid_external
from app.institutional.channel_ingress import body_owner, strict_json
from app.institutional.crypto import unseal
from app.institutional.db import institution, key, rows


def reference(provider):
    if not isinstance(provider, dict) or provider.get("type") != "edit":
        return None
    edit = provider.get("edit")
    if not isinstance(edit, dict) or not valid_external(edit.get("original_message_id")):
        return None
    message = edit.get("message")
    if not isinstance(message, dict):
        return None
    text = message.get("text")
    body = text.get("body") if isinstance(text, dict) else None
    if not isinstance(body, str) or not body.strip() or len(body) > 4000:
        return None
    return {"external": edit["original_message_id"], "text": body}


def recovered_provider(saved, receipt, settings):
    provider = saved.get("provider") or {}
    if reference(provider) or provider.get("type") != "edit" or not receipt.get("BodyCiphertext"):
        return provider
    raw = unseal(key(settings), body_owner(settings, receipt["ReceiptId"], receipt["EndpointId"]),
                 receipt["BodyNonce"], receipt["BodyCiphertext"])
    matches = [v["provider"] for v in normalize("meta", strict_json(raw))
               if all(v.get(k) == saved.get(k) for k in ("channel", "route", "kind", "external", "author"))]
    return matches[0] if len(matches) == 1 else provider


def targets(c, settings, conversation, integration, identity, external):
    return rows(c,
        "SELECT TOP(2) m.MessageId,m.Body,m.Direction FROM crm.Message m "
        "JOIN crm_channels2.MessageRoute r ON r.MessageId=m.MessageId AND r.InstitutionId=? "
        "AND r.IntegrationId=? AND r.IdentityId=? AND r.ActorKind='external' "
        "JOIN crm_channels2.ExternalMessage x ON x.InstitutionId=r.InstitutionId "
        "AND x.IntegrationId=r.IntegrationId AND x.MessageId=m.MessageId "
        "WHERE m.ConversationId=? AND m.Direction='incoming' "
        "AND x.ExternalId COLLATE Latin1_General_100_BIN2=? ORDER BY m.Sequence",
        institution(settings), integration, identity, conversation, external)


def project(c, settings, conversation, messages):
    ids = [v["id"] for v in messages if v.get("direction") == "incoming"]
    if not ids:
        return {}
    sources = rows(c,
        "SELECT x.MessageId,x.IntegrationId,r.IdentityId,e.Payload,w.ReceiptId,w.EndpointId,w.BodyNonce,w.BodyCiphertext "
        "FROM crm_channels2.ExternalMessage x JOIN crm.Message m ON m.MessageId=x.MessageId "
        "JOIN crm_channels2.MessageRoute r ON r.InstitutionId=x.InstitutionId AND r.IntegrationId=x.IntegrationId AND r.MessageId=x.MessageId "
        "JOIN crm_channels2.WebhookEvent e ON e.InstitutionId=x.InstitutionId AND e.IntegrationId=x.IntegrationId "
        "AND e.ProviderEventId COLLATE Latin1_General_100_BIN2=x.ExternalId AND e.Kind='message' "
        "JOIN crm_channels2.WebhookReceipt w ON w.InstitutionId=e.InstitutionId AND w.ReceiptId=e.ReceiptId AND w.Authentication='verified' "
        "WHERE x.InstitutionId=? AND m.ConversationId=? AND JSON_VALUE(e.Payload,'$.provider.type')='edit' "
        "AND x.MessageId IN(" + ",".join("?" for _ in ids) + ")",
        institution(settings), conversation, *ids)
    result = {}
    for source in sources:
        try:
            value = reference(recovered_provider(json.loads(source["Payload"]), source, settings))
        except (InvalidTag, ValueError, KeyError, TypeError, RecursionError):
            value = None
        identity = str(source["MessageId"]).lower()
        found = targets(c, settings, conversation, source["IntegrationId"], source["IdentityId"], value["external"]) if value else []
        if len(found) != 1:
            result[identity] = {"body": "Edición recibida · no se pudo verificar el mensaje original", "messageEdit": {"verified": False}}
            continue
        target = found[0]
        result[identity] = {"body": value["text"], "messageEdit": {"verified": True},
                            "replyTo": {"id": str(target["MessageId"]).lower(), "body": target["Body"][:600],
                                        "direction": "incoming"}, "editTargetExternal": value["external"]}
    return result


def history(c, settings, conversation, messages):
    presentation = project(c, settings, conversation,
        [{"id": str(v["MessageId"]).lower(), "body": v["Body"], "direction": v["Direction"]}
         for v in messages if v.get("MessageId")])
    result = []
    for message in messages:
        value = presentation.get(str(message.get("MessageId", "")).lower())
        if not value:
            result.append(message)
        elif value["messageEdit"]["verified"]:
            result.append({**message, "Body": "[Mensaje editado; reemplaza su versión anterior] " + value["body"]
                           + "\nMensaje anterior: " + value["replyTo"]["body"],
                           "ExternalId": value["editTargetExternal"], "edit_target_id": value["replyTo"]["id"],
                           "body_origin": "authenticated_message_edit"})
        else:
            result.append({**message, "Body": value["body"]})
    return result
