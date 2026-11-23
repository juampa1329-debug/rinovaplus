"""Project confirmed Meta outgoing messages without sending or opening a reply window."""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import Field

from app.institutional import db
from app.institutional.auth import authorize
from app.institutional.channel_operations import account
from app.institutional.channel_provider import provider_account
from app.institutional.models import Strict
from app.institutional.store import transaction
from app.modules.channels import providers


def project(
    c,
    settings,
    item,
    recipient,
    external,
    body,
    stamp,
    *,
    name="",
    queue=None,
    program=None,
):
    from app.institutional.channel_events import create_contact, valid_external
    from app.institutional.comment_private import created_at, POLICY

    if (
        item["Channel"] not in {"messenger", "instagram"}
        or not valid_external(recipient)
        or not valid_external(external)
    ):
        raise HTTPException(409, "meta_history_identity_invalid")
    inst, integration = db.institution(settings), item["IntegrationId"]
    old = db.one(
        c,
        "SELECT MessageId,Payload FROM crm_channels2.ExternalMessage WITH(UPDLOCK,HOLDLOCK) WHERE InstitutionId=? AND IntegrationId=? AND ExternalId=?",
        inst,
        integration,
        external,
    )
    if old:
        if queue:
            metadata = json.loads(old.get("Payload") or "{}")
            metadata.update(meta_outgoing=True, private_queue_id=str(queue))
            c.execute(
                "UPDATE crm_channels2.ExternalMessage SET Payload=? WHERE InstitutionId=? AND IntegrationId=? AND ExternalId=?",
                json.dumps(metadata),
                inst,
                integration,
                external,
            )
        return False
    if c.execute(
        "SELECT 1 FROM crm_channels2.SendJob WHERE InstitutionId=? AND IntegrationId=? AND ExternalId=? AND MessageId IS NOT NULL",
        inst,
        integration,
        external,
    ).fetchone():
        return False
    linked = db.one(
        c,
        "SELECT * FROM crm_channels2.ExternalIdentity WITH(UPDLOCK,HOLDLOCK) WHERE InstitutionId=? AND IntegrationId=? AND ExternalId=?",
        inst,
        integration,
        recipient,
    )
    if not linked:
        contact, conversation = create_contact(
            c, settings, item, name or recipient, control_mode="ai"
        )
        linked = {
            "IdentityId": str(uuid4()),
            "ContactId": contact,
            "ConversationId": conversation,
        }
        c.execute(
            "INSERT crm_channels2.ExternalIdentity(InstitutionId,IdentityId,IntegrationId,ExternalId,ContactId,ConversationId,CreatedAt) VALUES(?,?,?,?,?,?,SYSUTCDATETIME())",
            inst,
            linked["IdentityId"],
            integration,
            recipient,
            contact,
            conversation,
        )
    elif name:
        from app.institutional.channel_workspace import generic_social_name
        from app.institutional.sales_contact import read

        person = db.one(
            c, "SELECT Name FROM crm.Contact WHERE ContactId=?", linked["ContactId"]
        )
        fields, _ = read(c, settings, linked["ContactId"])
        if (
            person
            and generic_social_name(person["Name"])
            and not fields.get("fields", {}).get("name")
        ):
            c.execute(
                "UPDATE crm.Contact SET Name=?,UpdatedAt=SYSUTCDATETIME() WHERE ContactId=? AND Name=?",
                name[:100],
                linked["ContactId"],
                person["Name"],
            )
    message = str(uuid4())
    created = created_at(stamp).replace(tzinfo=None)
    if created > datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5):
        raise HTTPException(409, "meta_history_timestamp_invalid")
    metadata = {
        "meta_outgoing": True,
        "source": "meta_confirmed_outgoing",
        **({"private_queue_id": str(queue)} if queue else {}),
    }
    if program:
        metadata["comment_source"] = {
            "authority": POLICY,
            "program_id": int(program),
            "comment_id": "private:" + str(queue or external),
        }
    c.execute(
        "INSERT crm.Message(MessageId,ConversationId,Body,Direction,CreatedAt) VALUES(?,?,?,'outgoing',?)",
        message,
        linked["ConversationId"],
        body[:4000] or "[multimedia]",
        created,
    )
    c.execute(
        "INSERT crm_channels2.ExternalMessage(InstitutionId,ExternalMessageId,IntegrationId,ExternalId,MessageId,Payload,CreatedAt) VALUES(?,?,?,?,?,?,SYSUTCDATETIME())",
        inst,
        str(uuid4()),
        integration,
        external,
        message,
        json.dumps(metadata),
    )
    c.execute(
        "INSERT crm_channels2.MessageRoute(InstitutionId,MessageId,IntegrationId,IdentityId,ActorKind,CompletedAt) VALUES(?,?,?,?,'external',SYSUTCDATETIME())",
        inst,
        message,
        integration,
        linked["IdentityId"],
    )
    c.execute(
        "UPDATE crm.Conversation SET UpdatedAt=CASE WHEN UpdatedAt<? THEN ? ELSE UpdatedAt END WHERE ConversationId=?",
        created,
        created,
        linked["ConversationId"],
    )
    c.execute("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
    # LastIncomingAt, unread, control mode and epochs are deliberately untouched.
    return True


def private_accepted(settings, job, payload, external):
    recipient = getattr(external, "recipient_id", "")
    if not recipient:
        return
    with transaction(settings, True, anonymous=True) as c:
        source = account(c, settings, str(job["IntegrationId"]))
        if source["Channel"] == "facebook":
            matches = db.rows(
                c,
                "SELECT TOP(2) IntegrationId FROM crm_channels2.Integration WHERE InstitutionId=? AND ApplicationId=? AND ExternalAccountId=? AND Channel='messenger' AND RequestedStatus='connected' AND VerifiedStatus='verified'",
                db.institution(settings),
                source["ApplicationId"],
                source["ExternalAccountId"],
            )
            if len(matches) != 1:
                raise HTTPException(409, "meta_history_messenger_account_required")
            target = account(c, settings, str(matches[0]["IntegrationId"]))
        else:
            target = source
        operation = db.one(
            c,
            "SELECT ResultMetadata FROM crm_channels2.ProviderOperation WHERE InstitutionId=? AND OperationId=?",
            db.institution(settings),
            job["CommentId"],
        )
        program = (
            json.loads(operation["ResultMetadata"])
            .get("social_decision", {})
            .get("program_id")
            if operation
            else None
        )
        project(
            c,
            settings,
            target,
            recipient,
            str(external),
            payload["body"],
            datetime.now(timezone.utc).isoformat(),
            queue=job["QueueId"],
            program=program,
        )


def echo(c, settings, item, effect):
    message = effect["provider"].get("message", {})
    sender = str((effect["provider"].get("sender") or {}).get("id", ""))
    ig_scoped_echo = (
        item.get("Channel") == "instagram"
        and str(effect["route"]) == str(item["ExternalAccountId"])
        and sender
        and sender != effect["author"]
    )
    if not message.get("is_echo") or (
        not ig_scoped_echo
        and sender
        not in {
            str(item["ExternalAccountId"]),
            str(item.get("ParentExternalId")),
            str(effect["route"]),
        }
    ):
        raise HTTPException(409, "meta_echo_sender_mismatch")
    if str(message.get("app_id") or "") == str(item.get("ClientId") or "missing"):
        return
    # Our own outbox may not yet have committed acceptance. It owns projection
    # and deduplication; native Meta sends have no matching queue.
    if c.execute(
        "SELECT 1 FROM crm_channels2.SendJob WHERE InstitutionId=? AND ExternalId=?",
        db.institution(settings),
        effect["external"],
    ).fetchone():
        return
    from app.institutional.social_messages import text

    stamp = datetime.fromtimestamp(
        float(effect["provider"]["timestamp"]) / 1000, timezone.utc
    ).isoformat()
    project(
        c, settings, item, effect["author"], effect["external"], text(message), stamp
    )


class Sync(Strict):
    operation_id: str
    after: str = Field(default="", max_length=2000)


def install(app, settings):
    @app.get("/api/institution/workspace/inbox/meta-history-accounts")
    def accounts(request: Request):
        with transaction(settings, anonymous=True) as c:
            authorize(c, settings, request.state.authority, "inbox.read")
            values = db.rows(
                c,
                "SELECT IntegrationId,Channel,DisplayName FROM crm_channels2.Integration WHERE InstitutionId=? AND Channel IN('messenger','instagram') AND RequestedStatus='connected' AND VerifiedStatus='verified' ORDER BY DisplayName",
                db.institution(settings),
            )
            return {
                "items": [
                    {
                        "id": str(v["IntegrationId"]).lower(),
                        "name": v["DisplayName"],
                        "channel": v["Channel"],
                    }
                    for v in values
                ]
            }

    @app.post("/api/institution/workspace/inbox/meta-history/{integration}")
    def sync(request: Request, integration: str, body: Sync):
        integration = db.uid(integration)
        with transaction(settings, anonymous=True) as c:
            actor = authorize(c, settings, request.state.authority, "inbox.write")
            digest, previous = db.replay(
                c,
                settings,
                actor["UserId"],
                body.operation_id,
                "meta-history",
                integration,
                body.model_dump(),
            )
            if previous:
                return previous
            item = account(c, settings, integration)
            if (
                item["Channel"] not in {"messenger", "instagram"}
                or item["RequestedStatus"] != "connected"
                or item["VerifiedStatus"] != "verified"
            ):
                raise HTTPException(409, "meta_history_connected_account_required")
            adapter, secret = provider_account(c, settings, item)
        name_field = "username" if item["Channel"] == "instagram" else "name"
        target = (
            adapter["configuration"]["pageId"]
            if item["Channel"] == "instagram"
            and not adapter["configuration"].get("instagramLogin") == "instagram"
            else item["ExternalAccountId"]
        )
        params = {
            "limit": 25,
            "fields": "id,participants{id,"
            + name_field
            + "},messages.limit(20){id,message,created_time,from,to}",
        }
        if item["Channel"] == "instagram":
            params["platform"] = "instagram"
        if body.after:
            params["after"] = body.after
        try:
            own_username = ""
            if item["Channel"] == "instagram":
                own_profile = providers.request(
                    adapter,
                    "GET",
                    item["ExternalAccountId"],
                    params={"fields": "id,username"},
                )
                if str(own_profile.get("id")) != str(item["ExternalAccountId"]):
                    raise HTTPException(409, "meta_history_account_changed")
                own_username = own_profile.get("username") or ""
            result = providers.request(
                adapter, "GET", target + "/conversations", params=params
            )
        except providers.ProviderFailure as error:
            raise HTTPException(409, "meta_history_" + error.code) from None
        imported = skipped = 0
        own = {str(item["ExternalAccountId"]), str(item.get("ParentExternalId"))} - {
            "",
            "None",
        }
        from app.institutional.agent_catalog import Catalog, relevant_programs

        with transaction(settings, True, anonymous=True) as c:
            actor = authorize(c, settings, request.state.authority, "inbox.write")
            recent = account(c, settings, integration)
            if bytes(recent["RowVersion"]) != bytes(item["RowVersion"]):
                raise HTTPException(409, "meta_history_account_changed")
            _, current_secret = provider_account(c, settings, recent)
            if str(current_secret["SecretId"]) != str(secret["SecretId"]):
                raise HTTPException(409, "meta_history_account_changed")
            # Recheck operation after the read-only provider request.
            _, previous = db.replay(
                c,
                settings,
                actor["UserId"],
                body.operation_id,
                "meta-history",
                integration,
                body.model_dump(),
            )
            if previous:
                return previous
            programs = Catalog(settings).programs(c, 0, 300)["items"]
            for thread in (result.get("data") or [])[:25]:
                participants = (thread.get("participants") or {}).get("data", [])
                if own_username:
                    own.update(
                        str(p["id"])
                        for p in participants
                        if p.get("username") == own_username and p.get("id")
                    )
                people = [p for p in participants if str(p.get("id")) not in own]
                if len(people) != 1:
                    skipped += 1
                    continue
                person = people[0]
                for message in reversed(
                    (thread.get("messages") or {}).get("data", [])[:20]
                ):
                    if str((message.get("from") or {}).get("id")) not in own:
                        continue
                    from app.institutional.comment_private import created_at

                    try:
                        stamp = created_at(message.get("created_time"))
                    except HTTPException:
                        skipped += 1
                        continue
                    if stamp < datetime.now(timezone.utc) - timedelta(days=7):
                        continue
                    external = str(message.get("id", ""))
                    from app.institutional.channel_events import valid_external

                    if not valid_external(external):
                        skipped += 1
                        continue
                    text = message.get("message") or ""
                    matches = relevant_programs(programs, {}, text)
                    imported += int(
                        project(
                            c,
                            settings,
                            recent,
                            str(person.get("id", "")),
                            external,
                            text,
                            stamp.isoformat(),
                            name=str(person.get(name_field) or "")[:100],
                            program=matches[0]["program_id"]
                            if len(matches) == 1
                            else None,
                        )
                    )
            paging = result.get("paging") or {}
            after = (
                str((paging.get("cursors") or {}).get("after") or "")[:2000]
                if paging.get("next")
                else ""
            )
            answer = {
                "imported": imported,
                "skipped": skipped,
                "has_more": bool(after),
                "after": after,
                "sent": 0,
            }
            db.record_operation(
                c,
                settings,
                actor["UserId"],
                body.operation_id,
                "meta-history",
                integration,
                digest,
                answer,
            )
            db.audit(c, settings, actor["UserId"], "meta-history", integration)
            return answer
