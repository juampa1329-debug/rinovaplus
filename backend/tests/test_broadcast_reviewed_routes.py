import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.institutional import broadcast_alternate_phones as alternate
from app.institutional import broadcast_prospects as prospects
from app.institutional import broadcast_routes as routes
from app.institutional import broadcasts
from app.institutional.broadcast_models import Filters


@pytest.mark.parametrize(
    "change",
    [
        {"audience_mode": "segment"},
        {"contact_ids": []},
        {"identity_ids": ["same", "same"]},
    ],
)
def test_route_selection_requires_valid_unique_routes_and_selected_contacts(change):
    with pytest.raises(ValidationError):
        Filters(
            **{
                "audience_mode": "contacts",
                "contact_ids": [str(uuid4())],
                "identity_ids": [str(uuid4())],
                **change,
            }
        )


def test_route_selection_cannot_request_more_routes_than_people():
    with pytest.raises(ValidationError):
        Filters(
            audience_mode="contacts",
            contact_ids=[str(uuid4())],
            identity_ids=[str(uuid4()), str(uuid4())],
        )


@pytest.mark.parametrize("case", ["missing", "foreign_contact", "duplicate_person"])
def test_routes_cannot_escape_the_account_or_selected_people(monkeypatch, case):
    contact, identity = str(uuid4()), str(uuid4())
    selected = [{"ContactId": contact, "IdentityId": identity}]
    document = {
        "integration_id": "account",
        "filters": {
            "contact_ids": [contact],
            "identity_ids": [identity],
        },
    }
    if case == "missing":
        selected = []
    elif case == "foreign_contact":
        selected[0]["ContactId"] = str(uuid4())
    else:
        another = str(uuid4())
        document["filters"]["identity_ids"].append(another)
        selected.append({"ContactId": contact, "IdentityId": another})
    monkeypatch.setattr(routes.db, "institution", lambda _: "institution")

    def read(c, sql, *args):
        assert "InstitutionId=? AND IntegrationId=?" in sql
        assert args[:2] == ("institution", "account")
        return selected

    monkeypatch.setattr(routes.db, "rows", read)
    with pytest.raises(HTTPException) as error:
        routes.validate_selection(None, None, document)
    assert error.value.detail == "broadcast_identity_selection_review_required"


def test_reviewed_route_is_scoped_by_both_contact_and_identity(monkeypatch):
    contact, identity = str(uuid4()), str(uuid4())
    captured = []
    monkeypatch.setattr(broadcasts, "institution", lambda _: "institution")
    monkeypatch.setattr(
        broadcasts, "rows", lambda c, sql, *args: captured.append((sql, args)) or []
    )
    broadcasts.candidate_rows(
        None,
        None,
        {
            "integration_id": "account",
            "filters": {
                "contact_ids": [contact],
                "identity_ids": [identity],
            },
        },
    )
    sql, args = captured[0]
    assert "p.ContactId IN" in sql and "i.IdentityId IN" in sql
    assert json.loads(args[2]) == [contact]
    assert json.loads(args[3]) == [identity]


class Cursor:
    def __init__(self, *, merge=False, history=False):
        self.merge, self.history, self.calls = merge, history, []

    def execute(self, sql, *args):
        self.calls.append((sql, args))
        self.result = (
            ((1,) if self.merge else None)
            if "crm_workspace.Merge" in sql
            else ((1,) if self.history else None)
        )
        return self

    def fetchone(self):
        return self.result


def harness(
    monkeypatch,
    *,
    linked=None,
    mode="ai",
    state="open",
    epoch=1,
    primary=True,
    other_phone=False,
    **cursor_flags,
):
    contact, conversation = str(uuid4()), str(uuid4())
    main = {
        "IdentityId": str(uuid4()),
        "ContactId": contact,
        "ConversationId": conversation,
    }
    person = {
        "ContactId": contact,
        "Phone": "+573001234567",
        "Type": "Preinscrito",
        "CustomValues": json.dumps(
            {"pre_import_ref": "PRE-1234567890abcdef", "pre_programas": "PRE-ICFES"}
        ),
    }
    current = {
        "ContactId": contact,
        "ConversationId": conversation,
        "ControlMode": mode,
        "State": state,
        "ControlEpoch": epoch,
    }

    def one(c, sql, *args):
        if "FROM crm.Contact" in sql:
            return person
        if "FROM crm.Conversation v" in sql:
            return current
        assert "InstitutionId=?" in sql and "IntegrationId=?" in sql
        return (main if primary else None) if args[-1] == "573001234567" else linked

    monkeypatch.setattr(alternate.db, "one", one)
    monkeypatch.setattr(alternate.db, "institution", lambda _: "institution")
    monkeypatch.setattr(
        alternate.db,
        "rows",
        lambda *args: (
            [{"ContactId": str(uuid4()), "Phone": "+573119876543"}]
            if other_phone
            else [{"ContactId": contact, "Phone": person["Phone"]}]
        ),
    )
    return Cursor(**cursor_flags), contact, main


@pytest.mark.parametrize(
    "flags",
    [
        {"merge": True},
        {"history": True},
        {"mode": "human"},
        {"state": "closed"},
        {"epoch": 2},
        {"primary": False},
        {"other_phone": True},
        {"linked": {"ContactId": str(uuid4()), "ConversationId": str(uuid4())}},
    ],
)
def test_alternate_routes_keep_history_identity_and_human_review_guards(
    monkeypatch, flags
):
    c, contact, _ = harness(monkeypatch, **flags)
    with pytest.raises(HTTPException):
        alternate.plan(c, None, "account", contact, "+573119876543", "all")
    assert not any(sql.startswith(("INSERT", "UPDATE")) for sql, _ in c.calls)


@pytest.mark.parametrize("destination", ["+573001234567", "123", "+12345678901"])
def test_alternate_must_be_a_distinct_valid_colombian_phone(monkeypatch, destination):
    c, contact, _ = harness(monkeypatch)
    with pytest.raises(HTTPException):
        alternate.plan(c, None, "account", contact, destination, "all")


def test_new_alternate_reuses_contact_and_conversation_without_message_or_inbound(
    monkeypatch,
):
    c, contact, main = harness(monkeypatch)
    planned = alternate.plan(c, None, "account", contact, "+573119876543", "all")
    identity = alternate.link(c, None, "account", planned)
    inserts = [(sql, args) for sql, args in c.calls if sql.startswith("INSERT")]
    assert len(inserts) == 1
    sql, args = inserts[0]
    assert "crm_channels2.ExternalIdentity" in sql
    assert args[0:3] == ("institution", identity, "account")
    assert args[3:] == ("573119876543", contact, main["ConversationId"])
    assert "LastIncomingAt" not in sql
    assert not any(sql.startswith("INSERT crm.Message") for sql, _ in c.calls)


def test_existing_alternate_is_not_relinked_or_reassigned(monkeypatch):
    c, contact, main = harness(monkeypatch)
    existing = dict(main, IdentityId=str(uuid4()))
    original_one = alternate.db.one
    monkeypatch.setattr(
        alternate.db,
        "one",
        lambda c, sql, *args: (
            existing if args[-1] == "573119876543" else original_one(c, sql, *args)
        ),
    )
    planned = alternate.plan(c, None, "account", contact, "+573119876543", "all")
    assert alternate.link(c, None, "account", planned) == existing["IdentityId"]
    assert not any(sql.startswith(("INSERT", "UPDATE")) for sql, _ in c.calls)


def test_additional_phone_requires_explicit_contact_in_the_reviewed_batch():
    contact = str(uuid4())
    body = dict(
        operation_id=str(uuid4()),
        revision=0,
        reason="Review",
        confirmed=True,
        evidence="Owner reviewed two declared phones",
        origin="Owner request",
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        program="all",
        contact_ids=[contact],
    )
    for extra in [{str(uuid4()): "+573119876543"}, {contact: "invalid"}]:
        with pytest.raises(ValidationError):
            prospects.ProspectSetup(**body, additional_phones=extra)
    assert prospects.ProspectSetup(
        **body, additional_phones={contact: "+573119876543"}
    ).additional_phones == {contact: "+573119876543"}


@pytest.mark.parametrize("revoked", [False, True])
def test_setup_preserves_primary_and_fences_revoked_alternate_before_writes(
    monkeypatch, revoked
):
    contact, primary, secondary = str(uuid4()), str(uuid4()), str(uuid4())
    cursor = Cursor()
    grants, writes = [], []

    @contextmanager
    def tx(auth, write=False, recent=False):
        assert write and recent
        yield cursor, {"UserId": "actor"}

    service = SimpleNamespace(
        settings=SimpleNamespace(ticket={}),
        tx=tx,
        save_consent=lambda *args: grants.append(args[-1]),
    )
    monkeypatch.setattr(prospects, "authorize", lambda *args: None)
    monkeypatch.setattr(
        prospects,
        "account",
        lambda *args: {
            "Channel": "whatsapp",
            "RequestedStatus": "connected",
            "VerifiedStatus": "verified",
        },
    )
    monkeypatch.setattr(prospects.db, "replay", lambda *args: (b"digest", None))
    monkeypatch.setattr(prospects.db, "record_operation", lambda *args: None)
    monkeypatch.setattr(prospects.db, "audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(prospects, "prior_opt_out", lambda *args: False)
    monkeypatch.setattr(
        prospects, "link", lambda *args: writes.append("primary") or primary
    )
    monkeypatch.setattr(
        alternate, "plan", lambda *args: {"IdentityId": secondary if revoked else None}
    )
    monkeypatch.setattr(
        alternate, "link", lambda *args: writes.append("secondary") or secondary
    )
    monkeypatch.setattr(
        broadcasts,
        "consent",
        lambda c, settings, identity: {
            "State": "revoked" if identity == secondary else "granted",
            "VersionNo": 4,
            "ExpiresAt": datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(hours=1),
        },
    )
    body = prospects.ProspectSetup(
        operation_id=uuid4(),
        revision=0,
        reason="Owner reviewed",
        confirmed=True,
        evidence="Owner confirms two phones",
        origin="Direct request",
        program="all",
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        contact_ids=[contact],
        additional_phones={contact: "+573119876543"},
    )
    result = prospects.setup(service, {}, "account", body)
    if revoked:
        assert result["held"][0]["reason"] == "prospect_revoked_consent_review_required"
        assert writes == grants == []
    else:
        assert result["items"][0]["preserve_consent"]
        assert result["additional_items"][0]["identity_id"] == secondary
        assert len(grants) == 1 and str(grants[0].operation_id)
        assert writes == ["primary", "secondary"]
    assert result["messages_sent"] == 0
