import json
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pglast import parse_sql

from app.institutional import meta_history, channel_events, channel_workspace
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql


@pytest.mark.parametrize(
    "name",
    ["", "123456", "Contacto de Instagram", "Contacto de Messenger", "DM sender"],
)
def test_generated_social_names_are_candidates_for_background_resolution(name):
    assert channel_workspace.generic_social_name(name)
    assert not channel_workspace.generic_social_name("Karen Gutiérrez")


@pytest.mark.parametrize("channel", ["messenger", "instagram"])
def test_echo_normalization_keeps_actual_recipient_and_does_not_schedule_incoming(
    channel,
):
    data = {
        "object": "instagram" if channel == "instagram" else "page",
        "entry": [
            {
                "id": "123",
                "messaging": [
                    {
                        "sender": {"id": "123"},
                        "recipient": {"id": "456"},
                        "timestamp": 1795459200000,
                        "message": {
                            "mid": "mid.echo",
                            "text": "Información de PRE-ICFES",
                            "is_echo": True,
                            "app_id": "native",
                        },
                    }
                ],
            }
        ],
    }
    value = channel_events.normalize("meta", data)[0]
    assert value["kind"] == "message_echo" and value["author"] == "456"
    assert (
        value["provider"]["message"]["is_echo"]
        and value["provider"]["message"]["app_id"] == "native"
    )


@pytest.mark.parametrize("existing", [False, "imported", "owned_queue"])
def test_outgoing_projection_is_idempotent_and_never_opens_incoming_window(
    monkeypatch, existing
):
    inst, integration, conversation, contact, identity = [
        str(uuid4()) for _ in range(5)
    ]
    settings = SimpleNamespace(ticket={"context": [[1, inst]]})
    item = {"Channel": "messenger", "IntegrationId": integration}
    statements = []

    class Cursor:
        def execute(self, sql, *params):
            assert sql.count("?") == len(params)
            parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
            statements.append((sql, params))
            return self

        def fetchone(self):
            return (1,) if existing == "owned_queue" else None

    def one(_c, sql, *_):
        return (
            ({"MessageId": "already"} if existing == "imported" else None)
            if "ExternalMessage" in sql
            else {
                "IdentityId": identity,
                "ConversationId": conversation,
                "ContactId": contact,
            }
        )

    monkeypatch.setattr(meta_history.db, "one", one)
    assert meta_history.project(
        Cursor(),
        settings,
        item,
        "456",
        "mid.native",
        "PRE-ICFES",
        datetime.now(timezone.utc).isoformat(),
        program=27,
    ) == (not existing)
    inserts = [v for v in statements if v[0].startswith("INSERT")]
    if existing:
        assert not inserts
    else:
        assert len(inserts) == 3
        assert "'outgoing'" in inserts[0][0]
        metadata = json.loads(inserts[1][1][-1])
        assert (
            metadata["meta_outgoing"] and metadata["comment_source"]["program_id"] == 27
        )
        assert not any(
            "LastIncomingAt" in sql
            or "Unread=" in sql
            or "INSERT crm_channels2.SendJob" in sql
            for sql, _ in statements
        )


def test_own_app_echo_is_not_imported_again_while_acceptance_is_committing(monkeypatch):
    monkeypatch.setattr(
        meta_history,
        "project",
        lambda *_: pytest.fail("must not duplicate our own outbox"),
    )
    meta_history.echo(
        None,
        None,
        {"ExternalAccountId": "page", "ClientId": "our-app"},
        {
            "route": "page",
            "provider": {
                "sender": {"id": "page"},
                "message": {"is_echo": True, "app_id": "our-app"},
            },
        },
    )
    with pytest.raises(HTTPException):
        meta_history.echo(
            None,
            None,
            {"ExternalAccountId": "page"},
            {
                "route": "page",
                "provider": {
                    "sender": {"id": "someone-else"},
                    "message": {"is_echo": True},
                },
            },
        )


@pytest.mark.parametrize("protected", [False, True])
def test_verified_profile_name_persists_over_placeholder_but_not_manual_name(
    monkeypatch, protected
):
    from contextlib import nullcontext
    from app.institutional import sales_contact

    integration, contact = str(uuid4()), str(uuid4())
    statements = []

    class Cursor:
        def execute(self, sql, *params):
            statements.append(sql)
            return self

    service = SimpleNamespace(
        profile=SimpleNamespace(ticket={"context": [[1, str(uuid4())]]}),
        transaction=lambda *_: nullcontext(Cursor()),
    )
    monkeypatch.setattr(
        channel_workspace.db,
        "one",
        lambda _c, sql, *_: {
            "ExternalId": "123",
            "IntegrationId": integration,
            "ContactId": contact,
        }
        if "ExternalIdentity" in sql
        else {"Name": "Contacto de Instagram"},
    )
    monkeypatch.setattr(
        channel_workspace, "account", lambda *_: {"Channel": "instagram"}
    )
    monkeypatch.setattr(channel_workspace, "provider_account", lambda *_: ({}, None))
    monkeypatch.setattr(
        channel_workspace.providers,
        "request",
        lambda *_a, **_k: {"name": "Ana Ejemplo", "username": "ana.ejemplo"},
    )
    monkeypatch.setattr(
        sales_contact,
        "read",
        lambda *_: (
            {"fields": {"name": {"authority": "manual"}} if protected else {}},
            1,
        ),
    )
    value = channel_workspace.Workspace.social_profile(service, str(uuid4()))
    assert value["profile"]["name"] == "Ana Ejemplo"
    assert any(sql.startswith("UPDATE crm.Contact") for sql in statements) == (
        not protected
    )
