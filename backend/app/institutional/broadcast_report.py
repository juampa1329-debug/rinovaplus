"""Campaign receipt projection without a correlated event scan per recipient."""


def projection(*, materialized=False):
    # Multi-use scoped CTEs let PostgreSQL extract authenticated event references
    # once per campaign account. Counts, pages and exports share these semantics.
    # No receipt is inferred from queue acceptance or an unrelated conversation.
    statement = """WITH base AS (
        SELECT r.InstitutionId,r.RecipientId,r.IdentityId,r.Attempts,r.CurrentQueueId,
            pc.Stage AS CurrentStage,pc.Program AS CurrentProgram,
            p.CustomValues AS CurrentCustomValues,p.Name,i.ExternalId AS Phone,
            COALESCE(q.State COLLATE Latin1_General_100_BIN2,r.State) AS Status,
            COALESCE(q.LastErrorCode COLLATE Latin1_General_100_BIN2,r.LastError) AS Error,
            q.IntegrationId,q.ExternalId AS ProviderMessageId,r.Snapshot,
            JSON_VALUE(r.Snapshot,'$.body') AS Body,r.CreatedAt AS PreparedAt,
            q.CreatedAt AS QueuedAt,
            CASE WHEN q.ExternalId IS NOT NULL THEN q.CompletedAt END AS AcceptedAt
        FROM crm_broadcast7.Recipient r
        JOIN crm.Contact p ON p.ContactId=r.ContactId
        LEFT JOIN crm_workspace.Merge mg ON mg.SourceContactId=r.ContactId AND mg.Active=1
        JOIN crm.Contact pc ON pc.ContactId=COALESCE(mg.TargetContactId,r.ContactId)
        JOIN crm_channels2.ExternalIdentity i ON i.InstitutionId=r.InstitutionId AND i.IdentityId=r.IdentityId
        LEFT JOIN crm_channels2.SendJob q ON q.InstitutionId=r.InstitutionId AND q.QueueId=r.CurrentQueueId
        WHERE r.InstitutionId=? AND r.CampaignId=?
    ), event_accounts AS (
        SELECT DISTINCT InstitutionId,IntegrationId FROM base
        WHERE ProviderMessageId IS NOT NULL AND IntegrationId IS NOT NULL
    ), scoped_events AS (
        SELECT e.InstitutionId,e.IntegrationId,e.Kind,e.CreatedAt,
            CASE WHEN e.Kind='status' THEN JSON_VALUE(e.Payload,'$.external')
                ELSE JSON_VALUE(e.Payload,'$.provider.context.id') END AS EventRef,
            CASE WHEN e.Kind='message' THEN JSON_VALUE(e.Payload,'$.author') END AS EventAuthor,
            CASE WHEN e.Kind='status' THEN JSON_VALUE(e.Payload,'$.text') END AS StatusText
        FROM crm_channels2.WebhookEvent e
        JOIN event_accounts a ON a.InstitutionId=e.InstitutionId AND a.IntegrationId=e.IntegrationId
        WHERE e.Status='processed' AND e.Kind IN('status','message')
    ), status_dates AS (
        SELECT r.RecipientId,
            MIN(CASE WHEN e.StatusText='sent' THEN e.CreatedAt END) AS SentAt,
            MIN(CASE WHEN e.StatusText='delivered' THEN e.CreatedAt END) AS DeliveredAt,
            MIN(CASE WHEN e.StatusText='read' THEN e.CreatedAt END) AS ReadAt,
            MIN(CASE WHEN e.StatusText='failed' THEN e.CreatedAt END) AS FailedAt
        FROM base r JOIN scoped_events e
          ON e.InstitutionId=r.InstitutionId AND e.IntegrationId=r.IntegrationId
          AND e.Kind='status' AND e.EventRef COLLATE Latin1_General_100_BIN2=r.ProviderMessageId
        GROUP BY r.RecipientId
    ), reply_dates AS (
        SELECT r.RecipientId,MIN(e.CreatedAt) AS RepliedAt
        FROM base r JOIN scoped_events e
          ON e.InstitutionId=r.InstitutionId AND e.IntegrationId=r.IntegrationId
          AND e.Kind='message' AND e.EventRef COLLATE Latin1_General_100_BIN2=r.ProviderMessageId
          AND e.EventAuthor COLLATE Latin1_General_100_BIN2=r.Phone
        GROUP BY r.RecipientId
    ), enriched AS (
        SELECT r.*,d.SentAt,d.DeliveredAt,d.ReadAt,d.FailedAt,p.RepliedAt
        FROM base r
        LEFT JOIN status_dates d ON d.RecipientId=r.RecipientId
        LEFT JOIN reply_dates p ON p.RecipientId=r.RecipientId
    ), filtered AS (
        SELECT * FROM enriched WHERE (?='' OR Status=? OR ?='replied' AND RepliedAt IS NOT NULL)
          AND (?='' OR CHARINDEX(?,Name)>0 OR CHARINDEX(?,Phone)>0 OR CHARINDEX(?,ISNULL(Body,''))>0)
    ) """
    if materialized:
        # PostgreSQL 16 may otherwise inline projections and re-evaluate the
        # JSON expressions during each join. SQL Server keeps its native CTE.
        statement = statement.replace("base AS (", "base AS MATERIALIZED (", 1)
        statement = statement.replace(
            "scoped_events AS (", "scoped_events AS MATERIALIZED (", 1
        )
    return statement
