"""Comment-origin Inbox views, without changing delivery or conversation control."""

# Old, explicitly identified PRE-ICFES outreach predates private SendJobs.
# Its original provider-confirmed message declares the origin. Merely naming
# a program, an ad referral or an ordinary outbound DM does not qualify.
COMMENT_ORIGIN = (
    "EXISTS(SELECT 1 FROM crm.Message om "
    "JOIN crm_channels2.ExternalMessage ox ON ox.MessageId=om.MessageId "
    "JOIN crm_channels2.Integration oi ON oi.InstitutionId=ox.InstitutionId "
    "AND oi.IntegrationId=ox.IntegrationId "
    "WHERE om.ConversationId=v.ConversationId AND oi.Channel IN('messenger','instagram') "
    "AND (JSON_VALUE(ox.Payload,'$.private_queue_id') IS NOT NULL "
    "OR (JSON_VALUE(ox.Payload,'$.comment_source.authority')='cbn-comment-private-v1' "
    "AND NOT (JSON_VALUE(ox.Payload,'$.comment_source.comment_id') LIKE 'private:%')) "
    "OR (om.Direction='outgoing' AND JSON_VALUE(ox.Payload,'$.meta_outgoing')='true' "
    "AND om.Body LIKE '%Gracias por comentar nuestro video de PRE-ICFES CBN.%')))"
)
COMMENT_PENDING = (
    "(" + COMMENT_ORIGIN + " AND NOT EXISTS(SELECT 1 FROM crm.Message incoming "
    "WHERE incoming.ConversationId=v.ConversationId AND incoming.Direction='incoming'))"
)


def view_predicate(queue):
    if queue == "comment_pending":
        return COMMENT_PENDING
    if queue == "comment_origin":
        return COMMENT_ORIGIN
    return "NOT " + COMMENT_PENDING
