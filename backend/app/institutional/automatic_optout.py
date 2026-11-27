"""Immediate canonical suppression from attributable customer input, without LLM IO."""

import json
import time

from app.institutional import db
from app.institutional.contact_intent import opted_out

VERSIONS = {"cbn-institutional-campaign-p8-v1", "cbn-institutional-ads-p9-v1",
            "cbn-institutional-learning-p10-v1", "cbn-institutional-operations-p11-v1"}


def supported(settings):
    return settings.ticket.get("version") in VERSIONS


def receive(c, settings, identity, message, text, *, transcribed=False):
    if not supported(settings) or not opted_out(text):
        return False
    from app.institutional.campaigns import event, key
    from app.institutional.contact_preference import apply_no_contact
    from app.institutional.workspace import primary

    identity, message = db.uid(str(identity)), db.uid(str(message))
    source = key("global-no-contact", identity, message)
    if db.one(c, "SELECT EventId FROM crm_campaign8.Event WHERE InstitutionId=? AND SourceKey=?",
              db.institution(settings), source):
        return True
    incoming = db.one(c,
        "SELECT m.Body,m.ConversationId,i.ContactId FROM crm.Message m "
        "JOIN crm_channels2.MessageRoute r ON r.MessageId=m.MessageId "
        "JOIN crm_channels2.ExternalIdentity i ON i.InstitutionId=r.InstitutionId "
        "AND i.IdentityId=r.IdentityId AND i.IntegrationId=r.IntegrationId "
        "AND i.ConversationId=m.ConversationId "
        "JOIN crm.Conversation v ON v.ConversationId=m.ConversationId AND v.ContactId=i.ContactId "
        "WHERE r.InstitutionId=? AND r.IdentityId=? AND m.MessageId=? "
        "AND m.Direction='incoming' AND r.ActorKind='external'",
        db.institution(settings), identity, message)
    if not incoming:
        return False
    if transcribed:
        from app.institutional.conversation_scope import transcript_section
        saved = db.one(c, "SELECT Document FROM crm_access.Setting WHERE InstitutionId=? AND Section=?",
                       db.institution(settings), transcript_section(message))
        proof = json.loads(saved["Document"]) if saved else {}
        if (proof.get("message_id") != message or proof.get("conversation_id") != str(incoming["ConversationId"]).lower()
                or proof.get("text") != text or proof.get("authority") != "automatic_audio_transcription_not_human_verified"):
            return False
    elif incoming["Body"] != text:
        return False
    contact = primary(c, str(incoming["ContactId"]))
    proof = {"origin_identity_id": identity, "message_id": message,
             "input_kind": "audio_transcription" if transcribed else "customer_text"}
    event(c, settings, "opt_out", {"identity_id": identity, "source": "authenticated_incoming", **proof},
          source=key("optout", identity, message))
    apply_no_contact(c, settings, contact, message,
                     "Solicitud explícita de no recibir más mensajes en un canal vinculado.",
                     source="canonical_incoming_request", proof=proof)
    event(c, settings, "no_contact_applied", proof, source=source)
    return True


class Reconciler:
    """Drain old authenticated opt-outs one at a time; one idle scan per minute."""
    def __init__(self, settings):
        self.settings, self.next_check = settings, 0

    def once(self):
        if not supported(self.settings) or time.monotonic() < self.next_check:
            return False
        # An unavailable history query must not cause a retry storm. Successful
        # recovery can drain the next request on the following worker iteration.
        self.next_check = time.monotonic() + 60
        from app.institutional.store import transaction
        from app.institutional.campaigns import event, key
        with transaction(self.settings, anonymous=True) as c:
            request = db.one(c,
                "SELECT TOP(1) e.EventId,e.Document,i.IdentityId,m.MessageId,m.Body "
                "FROM crm_campaign8.Event e JOIN crm_channels2.ExternalIdentity i "
                "ON i.InstitutionId=e.InstitutionId AND LOWER(CONVERT(varchar(36),i.IdentityId))=JSON_VALUE(e.Document,'$.identity_id') "
                "JOIN crm_channels2.MessageRoute r ON r.InstitutionId=i.InstitutionId AND r.IdentityId=i.IdentityId "
                "AND LOWER(CONVERT(varchar(36),r.MessageId))=JSON_VALUE(e.Document,'$.message_id') "
                "JOIN crm.Message m ON m.MessageId=r.MessageId AND m.Direction='incoming' "
                "WHERE e.InstitutionId=? AND e.Kind='opt_out' AND r.ActorKind='external' "
                "AND JSON_VALUE(e.Document,'$.source')='authenticated_incoming' "
                "AND NOT EXISTS(SELECT 1 FROM crm_campaign8.Event done WHERE done.InstitutionId=e.InstitutionId "
                "AND done.Kind='no_contact_applied' AND JSON_VALUE(done.Document,'$.origin_identity_id')=JSON_VALUE(e.Document,'$.identity_id') "
                "AND JSON_VALUE(done.Document,'$.message_id')=JSON_VALUE(e.Document,'$.message_id')) "
                "ORDER BY e.CreatedAt,e.EventId", db.institution(self.settings))
            if not request:
                from app.institutional.contact_preference import suppression_query
                query, params = suppression_query(self.settings)
                recorded = db.one(c, "SELECT TOP(1) b.ContactId FROM (" + query + ") b "
                    "JOIN crm.Conversation v ON 1=1 LEFT JOIN crm_workspace.Merge g "
                    "ON g.SourceContactId=v.ContactId AND g.Active=1 "
                    "WHERE COALESCE(g.TargetContactId,v.ContactId)=b.ContactId AND v.State<>'closed' "
                    "ORDER BY v.UpdatedAt,v.ConversationId", *params)
        if not request:
            if not recorded:
                return False
            # Existing suppression is already authoritative across channels.
            # Finish its missing closure without inventing a customer message.
            from app.institutional.contact_preference import apply_no_contact, blocked
            from app.institutional.workspace import primary
            with transaction(self.settings, True, anonymous=True) as c:
                contact = primary(c, db.uid(str(recorded["ContactId"])))
                if not blocked(c, self.settings, contact):
                    return False
                apply_no_contact(c, self.settings, contact, contact,
                    "Completar cierre de una solicitud de No contactar ya registrada.",
                    source="recorded_no_contact_recovery", proof={"authority": "existing_persisted_no_contact"})
            self.next_check = 0
            return True
        with transaction(self.settings, True, anonymous=True) as c:
            # A later reviewed consent is respected; historical input is never
            # a new instruction to revoke that later authorization.
            granted = db.one(c, "SELECT 1 AS Allowed FROM crm_broadcast7.Consent grantor "
                "JOIN crm_campaign8.Event e ON e.InstitutionId=grantor.InstitutionId "
                "WHERE grantor.InstitutionId=? AND grantor.IdentityId=? AND e.EventId=? "
                "AND grantor.State='granted' AND grantor.CreatedAt>e.CreatedAt",
                db.institution(self.settings), request["IdentityId"], request["EventId"])
            applied = not granted and receive(c, self.settings, request["IdentityId"], request["MessageId"], request["Body"])
            if not applied:
                proof = {"origin_identity_id": str(request["IdentityId"]).lower(),
                         "message_id": str(request["MessageId"]).lower(),
                         "outcome": "later_consent_preserved" if granted else "source_review_required"}
                event(c, self.settings, "no_contact_applied", proof,
                      source=key("global-no-contact", proof["origin_identity_id"], proof["message_id"]))
        self.next_check = 0
        return True
