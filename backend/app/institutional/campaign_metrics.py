"""Read authenticated replies once for the selected flow, across all attempts."""


def attempts_query(*, materialized=False):
    sql = """WITH base AS (
      SELECT e.InstitutionId,e.EnrollmentId,e.IdentityId,e.Variant,
        step.StepId,step.NativeCampaignId
      FROM crm_campaign8.Enrollment e
      JOIN crm_campaign8.Step step ON step.InstitutionId=e.InstitutionId
        AND step.EnrollmentId=e.EnrollmentId
      WHERE e.InstitutionId=? AND e.FlowId=?
    ), attempts AS (
      SELECT b.InstitutionId,b.EnrollmentId,b.IdentityId,b.Variant,b.StepId,
        q.QueueId,q.State,q.ExternalId,q.IntegrationId
      FROM base b
      JOIN crm_broadcast7.Recipient r ON r.InstitutionId=b.InstitutionId
        AND r.CampaignId=b.NativeCampaignId
      JOIN crm_broadcast7.Attempt a ON a.InstitutionId=r.InstitutionId
        AND a.RecipientId=r.RecipientId
      JOIN crm_channels2.SendJob q ON q.InstitutionId=a.InstitutionId AND q.QueueId=a.QueueId
      UNION ALL
      SELECT b.InstitutionId,b.EnrollmentId,b.IdentityId,b.Variant,b.StepId,
        q.QueueId,q.State,q.ExternalId,q.IntegrationId
      FROM base b
      JOIN crm_campaign8.Event link ON link.InstitutionId=b.InstitutionId
        AND link.StepId=b.StepId AND link.Kind='native_chat'
      JOIN crm_channels2.SendJob q ON q.InstitutionId=link.InstitutionId
        AND LOWER(CONVERT(varchar(36),q.QueueId))=JSON_VALUE(link.Document,'$.queue_id')
    ), event_accounts AS (
      SELECT DISTINCT InstitutionId,IntegrationId FROM attempts WHERE ExternalId IS NOT NULL
    ), scoped_replies AS (
      SELECT reply.InstitutionId,reply.IntegrationId,
        JSON_VALUE(reply.Payload,'$.provider.context.id') AS EventRef,
        JSON_VALUE(reply.Payload,'$.author') AS EventAuthor
      FROM crm_channels2.WebhookEvent reply
      JOIN event_accounts a ON a.InstitutionId=reply.InstitutionId
        AND a.IntegrationId=reply.IntegrationId
      WHERE reply.Kind='message' AND reply.Status='processed'
    ), replied AS (
      SELECT DISTINCT a.QueueId FROM attempts a
      JOIN crm_channels2.ExternalIdentity i ON i.InstitutionId=a.InstitutionId
        AND i.IdentityId=a.IdentityId
      JOIN scoped_replies reply ON reply.InstitutionId=a.InstitutionId
        AND reply.IntegrationId=a.IntegrationId
        AND reply.EventRef COLLATE Latin1_General_100_BIN2=a.ExternalId
        AND reply.EventAuthor COLLATE Latin1_General_100_BIN2=i.ExternalId
    )
    SELECT a.EnrollmentId,a.Variant,a.StepId,a.QueueId,a.State,a.ExternalId,
      CASE WHEN reply.QueueId IS NOT NULL THEN 1 ELSE 0 END AS Replied
    FROM attempts a LEFT JOIN replied reply ON reply.QueueId=a.QueueId
    ORDER BY a.EnrollmentId,a.StepId,a.QueueId OFFSET 0 ROWS FETCH NEXT 100001 ROWS ONLY
    """
    if materialized:
        for name in ("base", "attempts", "scoped_replies"):
            sql = sql.replace(name + " AS (", name + " AS MATERIALIZED (", 1)
    return sql
