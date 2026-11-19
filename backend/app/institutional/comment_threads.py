"""Read-only PostgreSQL comment groups, scoped by institution, account, post and author."""

import hashlib
import json
import re

from fastapi import HTTPException

from app.institutional.auth import authorize
from app.institutional.db import institution, uid, utc
from app.institutional.store import transaction


def is_account_comment(value, account=None):
    account = account or value
    payload = json.loads(value.get("Payload") or "{}")
    provider = payload.get("provider") or {}
    author = str(value.get("AuthorExternalId") or "")
    ids = {
        str(account.get("ExternalAccountId") or ""),
        str(provider.get("self_ig_scoped_id") or ""),
    }
    return bool(
        payload.get("_crm", {}).get("is_self")
        or value.get("SelfComment")
        or author
        and author in ids - {""}
    )


def incoming_only_sql():
    # Also classifies old rows which predate the explicit is_self projection.
    return (
        " AND ISNULL(JSON_VALUE(s.Payload,'$._crm.is_self'),'false')<>'true'"
        " AND ISNULL(s.AuthorExternalId,'')<>ISNULL(i.ExternalAccountId,'')"
        " AND ISNULL(s.AuthorExternalId,'')<>ISNULL(JSON_VALUE(s.Payload,'$.provider.self_ig_scoped_id'),'')"
        " AND NOT EXISTS(SELECT 1 FROM crm_channels2.SendJob own WHERE "
        "own.InstitutionId=s.InstitutionId AND own.IntegrationId=s.IntegrationId "
        "AND own.ExternalId=s.ExternalId AND own.CommentId IS NOT NULL)"
    )


def table(settings, logical):
    name = settings.ticket["table_map"][logical].split(".")[-1].lower()
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", name):
        raise ValueError("invalid_comment_table_mapping")
    return 'rinovaplus_crm."' + name + '"'


def thread_cte(settings):
    comments = table(settings, "crm_channels2.SocialComment")
    accounts = table(settings, "crm_channels2.Integration")
    jobs = table(settings, "crm_channels2.SendJob")
    return f"""WITH RECURSIVE base AS (
      SELECT s.*,i.channel,i.displayname,i.requestedstatus,i.verifiedstatus,i.externalaccountid,
        COALESCE(NULLIF(s.payload::jsonb #>> '{{provider,post_id}}',''),
          NULLIF(s.payload::jsonb #>> '{{provider,media,id}}',''),
          NULLIF(s.payload::jsonb #>> '{{provider,media_id}}',''),
          NULLIF(s.payload::jsonb #>> '{{provider,video_id}}','')) AS post_ref,
        COALESCE(NULLIF(s.payload::jsonb #>> '{{provider,parent_id}}',''),
          NULLIF(s.payload::jsonb #>> '{{provider,parent_comment_id}}',''),
          NULLIF(s.payload::jsonb #>> '{{provider,reply_to_comment_id}}','')) AS parent_ref,
        (COALESCE(s.payload::jsonb #>> '{{_crm,is_self}}','false')='true'
         OR s.authorexternalid=i.externalaccountid
         OR s.authorexternalid=s.payload::jsonb #>> '{{provider,self_ig_scoped_id}}'
         OR echo.commentid IS NOT NULL) IS TRUE AS self_comment,
        echo.commentid AS echo_target
      FROM {comments} s JOIN {accounts} i
        ON i.institutionid=s.institutionid AND i.integrationid=s.integrationid
      LEFT JOIN LATERAL (SELECT q.commentid FROM {jobs} q
        WHERE q.institutionid=s.institutionid AND q.integrationid=s.integrationid
          AND q.externalid=s.externalid AND q.commentid IS NOT NULL
        ORDER BY q.createdat,q.queueid LIMIT 1) echo ON TRUE
      WHERE s.institutionid=%s
    ), edges AS (
      SELECT b.*,COALESCE(p.commentid,b.echo_target) AS parent_comment
      FROM base b LEFT JOIN base p ON p.integrationid=b.integrationid
        AND p.externalid=b.parent_ref AND p.commentid<>b.commentid
        AND (b.post_ref IS NULL OR p.post_ref IS NULL OR b.post_ref=p.post_ref)
    ), walk AS (
      SELECT b.commentid AS leaf,b.commentid AS node,b.integrationid,b.post_ref,
        CASE WHEN NOT b.self_comment THEN b.authorexternalid END AS person,
        CASE WHEN NOT b.self_comment THEN b.commentid END AS target,
        ARRAY[b.commentid] AS path,0 AS depth
      FROM edges b
      UNION ALL
      SELECT w.leaf,p.commentid,w.integrationid,COALESCE(w.post_ref,p.post_ref),
        COALESCE(w.person,CASE WHEN NOT p.self_comment THEN p.authorexternalid END),
        COALESCE(w.target,CASE WHEN NOT p.self_comment THEN p.commentid END),
        w.path||p.commentid,w.depth+1
      FROM walk w JOIN edges n ON n.commentid=w.node
      JOIN edges p ON p.commentid=n.parent_comment AND p.integrationid=w.integrationid
      WHERE w.depth<16 AND NOT p.commentid=ANY(w.path)
        AND (w.post_ref IS NULL OR p.post_ref IS NULL OR w.post_ref=p.post_ref)
    ), resolved AS (
      SELECT DISTINCT ON(w.leaf) w.leaf,w.integrationid,
        COALESCE(w.post_ref,'missing:'||w.node::text) AS thread_post,
        COALESCE(w.person,'unlinked:'||w.leaf::text) AS thread_person,w.target
      FROM walk w ORDER BY w.leaf,w.depth DESC
    ), members AS (
      SELECT b.*,r.thread_post,r.thread_person,r.target,
        COALESCE(b.payload::jsonb #>> '{{_crm,state}}','new') AS crm_state
      FROM base b JOIN resolved r ON r.leaf=b.commentid
    ) """


def native_rows(c, sql, *params):
    c.native(sql, *params)
    fields = [col[0] for col in c.description]
    return [dict(zip(fields, row, strict=True)) for row in c.fetchall()]


def group_key(row):
    return hashlib.sha256(
        json.dumps(
            [str(row["IntegrationId"]), row["thread_post"], row["thread_person"]],
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


class Threads:
    def __init__(self, settings):
        self.settings = settings

    def read(
        self,
        authority,
        *,
        channel="",
        integration="",
        state="all",
        q="",
        offset=0,
        comment_id="",
    ):
        from app.institutional.channel_comments import public_comment

        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, "inbox.read")
            cte = thread_cte(self.settings)
            where, params = ["TRUE"], [institution(self.settings)]
            for column, value in [("channel", channel), ("integrationid", integration)]:
                if value:
                    where.append(f"m.{column}=%s")
                    params.append(uid(value) if column == "integrationid" else value)
            if comment_id:
                where.append(
                    "EXISTS(SELECT 1 FROM members anchor WHERE anchor.commentid=%s AND anchor.integrationid=m.integrationid AND anchor.thread_post=m.thread_post AND anchor.thread_person=m.thread_person)"
                )
                params.append(uid(comment_id))
            # Match a whole group, keeping every member visible in its detail.
            having = []
            if state != "all":
                having.append("bool_or(m.crm_state=%s)")
                params.append(state)
            if q:
                having.append(
                    "bool_or(strpos(lower(m.body COLLATE \"default\"),lower(%s))>0 OR strpos(lower(m.payload::jsonb #>> '{provider,from,name}'),lower(%s))>0 OR strpos(lower(m.payload::jsonb #>> '{provider,from,username}'),lower(%s))>0 OR strpos(m.authorexternalid,%s)>0)"
                )
                params.extend([q] * 4)
            grouped = (
                """, groups AS (
              SELECT m.integrationid,m.thread_post,m.thread_person,
                (array_agg(m.commentid ORDER BY m.self_comment,m.receivedat DESC,m.commentid))[1] AS sample,
                max(m.receivedat) AS last_activity,
                count(*) FILTER(WHERE NOT m.self_comment) AS incoming_count,
                count(*) FILTER(WHERE m.self_comment) AS reply_count,
                count(*) FILTER(WHERE NOT m.self_comment AND m.crm_state='new') AS unread_count
              FROM members m WHERE """
                + " AND ".join(where)
                + " GROUP BY m.integrationid,m.thread_post,m.thread_person"
                + (" HAVING " + " AND ".join(having) if having else "")
                + ") "
            )
            total = c.native(
                cte + grouped + "SELECT count(*) FROM groups", *params
            ).fetchval()
            values = native_rows(
                c,
                cte
                + grouped
                + """SELECT m.*,g.incoming_count,g.reply_count,g.unread_count,g.last_activity,
              (SELECT q.state FROM """
                + table(self.settings, "crm_channels2.SendJob")
                + """ q
                WHERE q.institutionid=m.institutionid AND q.commentid=m.commentid
                ORDER BY q.createdat DESC,q.queueid LIMIT 1) AS ReplyState
              FROM groups g JOIN members m ON m.commentid=g.sample
              ORDER BY g.last_activity DESC,m.commentid LIMIT 25 OFFSET %s""",
                *params,
                offset,
            )
            items = []
            for row in values:
                row["SelfComment"] = row["self_comment"]
                item = public_comment(row)
                item["thread"] = {
                    "id": group_key(row),
                    "post_id": None
                    if row["thread_post"].startswith("missing:")
                    else row["thread_post"],
                    "comments": row["incoming_count"],
                    "replies": row["reply_count"],
                    "unread": row["unread_count"],
                    "last_activity": utc(row["last_activity"]),
                    "unlinked_reply": row["self_comment"],
                    "focus_id": comment_id or item["id"],
                }
                items.append(item)
            return {
                "items": items,
                "total": total,
                "has_more": offset + len(items) < total,
                "view": "threads",
            }

    def detail(self, authority, identity, offset=0):
        from app.institutional.channel_comments import public_comment

        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, "inbox.read")
            cte = thread_cte(self.settings)
            anchor = native_rows(
                c,
                cte + "SELECT * FROM members WHERE commentid=%s",
                institution(self.settings),
                uid(identity),
            )
            if not anchor:
                raise HTTPException(404, "comment_not_found")
            a = anchor[0]
            params = (
                institution(self.settings),
                a["IntegrationId"],
                a["thread_post"],
                a["thread_person"],
            )
            condition = " FROM members WHERE integrationid=%s AND thread_post=%s AND thread_person=%s AND NOT self_comment"
            total = c.native(cte + "SELECT count(*)" + condition, *params).fetchval()
            values = native_rows(
                c,
                cte
                + "SELECT *"
                + condition
                + " ORDER BY receivedat DESC,commentid DESC LIMIT 25 OFFSET %s",
                *params,
                offset,
            )
            # Keep a deep-linked original visible even outside the current page.
            focus = next(
                (
                    v
                    for v in native_rows(
                        c,
                        cte + "SELECT * FROM members WHERE commentid=%s",
                        institution(self.settings),
                        a["target"] or a["CommentId"],
                    )
                    if not v["self_comment"]
                ),
                None,
            )
            if focus and all(v["CommentId"] != focus["CommentId"] for v in values):
                values.append(focus)
            ids = [v["CommentId"] for v in values]
            jobs, replies = [], []
            if ids:
                replies = native_rows(
                    c,
                    cte
                    + "SELECT * FROM members WHERE integrationid=%s AND thread_post=%s AND thread_person=%s AND self_comment AND target=ANY(%s::uuid[]) ORDER BY receivedat,commentid",
                    *params,
                    ids,
                )
                jobs = native_rows(
                    c,
                    "SELECT * FROM "
                    + table(self.settings, "crm_channels2.SendJob")
                    + " WHERE institutionid=%s AND integrationid=%s AND kind='comment_reply' AND commentid=ANY(%s::uuid[]) ORDER BY createdat,queueid",
                    institution(self.settings),
                    a["IntegrationId"],
                    ids,
                )
            items = []
            for value in sorted(
                values, key=lambda v: (v["ReceivedAt"], str(v["CommentId"]))
            ):
                sent = [j for j in jobs if j["CommentId"] == value["CommentId"]]
                value["ReplyState"] = sent[-1]["State"] if sent else None
                item = public_comment(value)
                matching = [r for r in replies if r["target"] == value["CommentId"]]
                item["replies"] = reply_history(matching, sent, value["DisplayName"], value["Channel"])
                items.append(item)
            return {
                "items": items,
                "total": total,
                "has_more": offset + 25 < total,
                "focus_id": str(a["target"] or a["CommentId"]).lower(),
                "unlinked_reply": bool(a["self_comment"] and not a["target"]),
            }


def reply_history(comments, jobs, account, channel=""):
    """A provider echo and its accepted job are one reply, never two bubbles."""
    from app.institutional.comment_edits import edit_info, presentation

    ids = {v["ExternalId"] for v in comments}
    values = [
        {
            "id": str(v["CommentId"]).lower(),
            "body": v["Body"],
            "author": account,
            "received_at": utc(v["ReceivedAt"]),
            "state": (
                json.loads(v.get("Payload") or "{}").get("_crm", {}).get("state")
                if json.loads(v.get("Payload") or "{}").get("_crm", {}).get("state") in {"deleted", "unavailable"}
                else "published"
            ),
            "origin": "meta",
            "external_id": v["ExternalId"],
            "edit": edit_info(v, "meta", channel, json.loads(v.get("Payload") or "{}").get("_crm", {}).get("state", "published")),
        }
        for v in comments
    ]
    for j in jobs:
        if j.get("ExternalId") and j["ExternalId"] in ids:
            continue
        values.append(
            {
                "id": str(j["QueueId"]).lower(),
                "body": presentation(j, "crm")[0],
                "author": account,
                "received_at": utc(j["CreatedAt"]),
                "state": j["State"],
                "origin": "crm",
                "external_id": j.get("ExternalId"),
                "edit": edit_info(j, "crm", channel, j["State"]),
            }
        )
    return sorted(values, key=lambda v: (v["received_at"], v["id"]))
