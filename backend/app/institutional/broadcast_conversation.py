"""A signed reply to accepted campaign outreach can start a commercial AI turn."""

import json
import re
import unicodedata

from app.institutional import db

LABEL = "Hablar con Juan Pablo"
POLICY = (
    "\nINICIO COMERCIAL DESDE CAMPAÑA: sólo cuando inicio_comercial_campana con entry_turn=true acredita el botón "
    "'Hablar con Juan Pablo', ese botón por sí solo solicita iniciar la atención comercial de IA, "
    "no derivar a una persona ni usar revisar. En su turno de entrada preséntate brevemente con el "
    "nombre de atención indicado; entry_turn=false significa seguimiento sin esta excepción ni nueva presentación. "
    "En ese inicio usa Juan Pablo, de CBN, y conecta con el programa de la campaña y la meta del contacto. "
    "Ese nombre es la presentación del agente, no prueba de identidad de un empleado ni de que seas humano. "
    "Continúa con las skills de apertura, descubrimiento, valor, objeciones y cierre según la consulta. "
    "No vuelques todos los precios ni preguntes de nuevo qué programa interesa si está identificado. "
    "Usa el nombre conocido del contacto y una sola pregunta útil. Si este mismo inicio ya recibió "
    "presentación, continúa sin repetirla. La campaña aporta contexto, nunca sustituye la ficha vigente "
    "para precios, fechas y beneficios. Un cambio explícito de programa prevalece sobre la campaña. "
    "Si otro mensaje pide expresamente una persona real, atención humana o una queja, respeta la "
    "derivación; esta excepción no permite levantar el modo Humano ni inventar una transferencia."
)


def advisor_entry(text):
    if not isinstance(text, str):
        return False
    value = "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))
    return " ".join(re.findall(r"\w+", value)) == "hablar con juan pablo"


def origin(c, settings, conversation, history):
    incoming = next((m for m in reversed(history) if m["Direction"] == "incoming" and advisor_entry(m["Body"])), None)
    if not incoming:
        return None
    row = db.one(c,
        "SELECT TOP(1) m.MessageId,m.Sequence,e.Payload,r.Snapshot,b.CampaignId,b.Name "
        "FROM crm.Message m JOIN crm_channels2.ExternalMessage x ON x.MessageId=m.MessageId "
        "JOIN crm_channels2.MessageRoute ir ON ir.InstitutionId=x.InstitutionId "
        "AND ir.IntegrationId=x.IntegrationId AND ir.MessageId=m.MessageId "
        "JOIN crm_channels2.WebhookEvent e ON e.InstitutionId=x.InstitutionId AND e.IntegrationId=x.IntegrationId "
        "AND e.Kind='message' AND e.Status='processed' "
        "AND JSON_VALUE(e.Payload,'$.external') COLLATE Latin1_General_100_BIN2=x.ExternalId "
        "JOIN crm_channels2.SendJob q ON q.InstitutionId=x.InstitutionId AND q.IntegrationId=x.IntegrationId "
        "AND q.ExternalId=JSON_VALUE(e.Payload,'$.provider.context.id') COLLATE Latin1_General_100_BIN2 "
        "JOIN crm.Message om ON om.MessageId=q.MessageId AND om.ConversationId=m.ConversationId AND om.Sequence<m.Sequence "
        "JOIN crm_broadcast7.Attempt a ON a.InstitutionId=q.InstitutionId AND a.QueueId=q.QueueId "
        "JOIN crm_broadcast7.Recipient r ON r.InstitutionId=a.InstitutionId AND r.RecipientId=a.RecipientId "
        "AND r.IdentityId=ir.IdentityId AND r.CurrentQueueId=q.QueueId "
        "JOIN crm_broadcast7.Campaign b ON b.InstitutionId=r.InstitutionId AND b.CampaignId=r.CampaignId "
        "AND b.IntegrationId=q.IntegrationId "
        "WHERE x.InstitutionId=? AND m.ConversationId=? AND m.MessageId=? AND m.Direction='incoming' "
        "AND q.ExternalId IS NOT NULL AND q.State IN('accepted','sent','delivered','read') "
        "ORDER BY e.CreatedAt DESC",
        db.institution(settings), conversation, incoming["MessageId"])
    if not row:
        return None
    from app.institutional.channel_events import whatsapp_reply_text
    if not advisor_entry(whatsapp_reply_text(json.loads(row["Payload"]).get("provider", {}))):
        return None
    snapshot = json.loads(row["Snapshot"])
    profile = snapshot.get("audience_profile", {})
    return {
        "authority": "accepted_broadcast_button_v1", "button": LABEL,
        "campaign_id": str(row["CampaignId"]), "campaign_name": row["Name"][:160],
        "source_message_id": str(row["MessageId"]), "sequence": row["Sequence"],
        "program_hint": profile.get("program", "")[:200], "schedule_hint": profile.get("schedule", "")[:100],
        "routing_text": snapshot.get("body", "")[:1600],
        "academic_confirmation": False,
    }
