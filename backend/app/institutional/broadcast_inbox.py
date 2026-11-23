"""Keep unanswered campaign outreach in campaigns until a real inbound exists."""

BROADCAST_PENDING = (
    "(EXISTS(SELECT 1 FROM crm.Message bm "
    "JOIN crm_channels2.SendJob bq ON bq.MessageId=bm.MessageId "
    "JOIN crm_broadcast7.Attempt ba ON ba.InstitutionId=bq.InstitutionId "
    "AND ba.QueueId=bq.QueueId "
    "WHERE bm.ConversationId=v.ConversationId AND bm.Direction='outgoing') "
    "AND NOT EXISTS(SELECT 1 FROM crm.Message bi "
    "WHERE bi.ConversationId=v.ConversationId AND bi.Direction='incoming'))"
)
