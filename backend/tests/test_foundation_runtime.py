"""Offline C4 boundaries; real SQL acceptance is an explicit tools command."""

import copy
import hashlib
import json
from dataclasses import replace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import foundation
from app.config import Settings
from app.foundation_app import create_foundation_app
from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.sql_target import connection_string
from app.sql_workspace import (
    ContactMutation,
    ConversationMutation,
    MessageMutation,
    SqlWorkspace,
)


@pytest.fixture
def profile(tmp_path):
    value = {
        "scope": "SQL-C4-restored-repositories-only",
        "release_sha256": foundation.RELEASE_SHA,
        "identity": {
            "database": foundation.DATABASE,
            "database_id": 42,
            "machine": "C4-TEST",
            "server": "C4-TEST\\SQLEXPRESS",
            "instance": "SQLEXPRESS",
            "engine": 16,
            "compatibility": 160,
            "collation": "synthetic",
            "created_at": "synthetic",
        },
        "login_sid": "SYNTHETIC",
        "journal_sha256": "a" * 64,
    }
    path = tmp_path / "ticket.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return Settings(
        mode="local_foundation",
        sql_environment="foundation_rehearsal",
        sql_database=foundation.DATABASE,
        sql_host="host.docker.internal",
        sql_user=foundation.PRINCIPAL,
        sql_password="synthetic};Encrypt=No",
        sql_expected_login=foundation.PRINCIPAL,
        sql_expected_database_user=foundation.PRINCIPAL,
        sql_expected_machine="C4-TEST",
        sql_expected_server="C4-TEST\\SQLEXPRESS",
        sql_certificate_hostname="localhost",
        foundation_ticket_path=str(path),
        foundation_ticket_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


@pytest.mark.parametrize(
    "change",
    [
        {"mode": "local_sql_copy"},
        {"mode": "local_demo"},
        {"sql_environment": "local_copy"},
        {"sql_environment": "institutional"},
        {"sql_database": "HORARIOSSIIE"},
        {"sql_database": "DBSIIE"},
        {"sql_database": "CBN_C3_TRIAL_20261024_df12f51b"},
        {"sql_host": "sql.remote.invalid"},
        {"sql_host": ""},
        {"sql_port": 0},
        {"sql_certificate_hostname": ""},
        {"sql_certificate_hostname": "remote.invalid"},
        {"sql_user": "sa"},
        {"sql_password": ""},
        {"sql_expected_login": "sa"},
        {"sql_expected_database_user": "dbo"},
        {"sql_expected_machine": ""},
        {"sql_expected_server": ""},
        {"foundation_ticket_path": ""},
        {"foundation_ticket_sha256": "unverified"},
    ],
)
def test_profile_rejects_other_modes_targets_and_credentials(profile, change):
    with pytest.raises(ValueError):
        connection_string(replace(profile, **change))


def test_transport_keeps_tls_and_odbc_escaping(profile):
    value = connection_string(profile)
    assert "Encrypt=Yes;TrustServerCertificate=No;" in value
    assert "HostnameInCertificate=localhost;" in value
    assert "PWD={synthetic}};Encrypt=No};" in value
    assert profile.sql_password not in repr(profile)
    with pytest.raises(ValueError):
        connection_string(profile, catalog=True)


def test_environment_requires_an_explicit_foundation_profile(profile, monkeypatch):
    values = {
        "CRM_APP_MODE": profile.mode,
        "CRM_SQL_ENVIRONMENT": profile.sql_environment,
        "CRM_SQL_DATABASE": profile.sql_database,
        "CRM_SQL_HOST": profile.sql_host,
        "CRM_SQL_PORT": str(profile.sql_port),
        "CRM_SQL_USER": profile.sql_user,
        "CRM_SQL_PASSWORD": profile.sql_password,
        "CRM_SQL_EXPECTED_MACHINE": profile.sql_expected_machine,
        "CRM_SQL_EXPECTED_SERVER": profile.sql_expected_server,
        "CRM_SQL_EXPECTED_LOGIN": profile.sql_expected_login,
        "CRM_SQL_EXPECTED_DATABASE_USER": profile.sql_expected_database_user,
        "CRM_SQL_CERTIFICATE_HOSTNAME": profile.sql_certificate_hostname,
        "CRM_FOUNDATION_TICKET_PATH": profile.foundation_ticket_path,
        "CRM_FOUNDATION_TICKET_SHA256": profile.foundation_ticket_sha256,
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    assert Settings.from_environment() == profile
    monkeypatch.delenv("CRM_SQL_DATABASE")
    with pytest.raises(ValueError):
        Settings.from_environment()


def test_frozen_assets_and_ticket_are_separate_from_legacy_markers(profile):
    release, shape = foundation.assets()
    assert release["release_id"] == "CBN-foundation-local-v2"
    assert len(shape["columns"]) == 69
    assert foundation.ticket(profile)["identity"]["database"] == foundation.DATABASE
    with pytest.raises(ValueError):
        foundation.ticket(replace(profile, foundation_ticket_sha256="0" * 64))


@pytest.mark.parametrize(
    "section",
    [
        "objects",
        "columns",
        "indexes",
        "checks",
        "foreign_keys",
        "properties",
        "permissions",
        "schemas",
    ],
)
def test_full_managed_shape_rejects_drift(profile, monkeypatch, section):
    value = foundation.ticket(profile)
    _, expected = foundation.assets()
    actual = copy.deepcopy(expected)
    actual[section][0][next(iter(actual[section][0]))] = "drift"
    monkeypatch.setattr(foundation, "identity", lambda cursor: value["identity"])
    monkeypatch.setattr(foundation, "verify_acl", lambda cursor, ticket: None)
    monkeypatch.setattr(foundation, "metadata", lambda cursor, managed: actual)
    with pytest.raises(ValueError, match="contract mismatch"):
        foundation.verify(Mock(), profile)


def test_journal_drift_blocks_before_configuration_read(profile, monkeypatch):
    value = foundation.ticket(profile)
    monkeypatch.setattr(foundation, "identity", lambda cursor: value["identity"])
    monkeypatch.setattr(foundation, "verify_acl", lambda cursor, ticket: None)
    monkeypatch.setattr(
        foundation, "metadata", lambda cursor, managed: foundation.assets()[1]
    )
    monkeypatch.setattr(foundation, "journal_signature", lambda *args: "changed")
    cursor = Mock()
    with pytest.raises(ValueError):
        foundation.verify(cursor, profile)
    cursor.execute.assert_not_called()


def test_projection_preserves_every_other_actor_and_acl():
    shape = {
        "permissions": [
            {"grantee": foundation.PRINCIPAL},
            {"grantee": "public"},
            {"grantee": "cbn_foundation_migrator"},
        ],
        "principals": [{"name": foundation.PRINCIPAL}, {"name": "dbo"}],
        "database_permissions": [
            {"grantee": foundation.PRINCIPAL},
            {"grantee": "public"},
        ],
        "role_membership": [{"member_name": foundation.PRINCIPAL}],
        "columns": ["keep"],
    }
    projected = foundation.project_academic(shape)
    assert [p["grantee"] for p in projected["permissions"]] == [
        "public",
        "cbn_foundation_migrator",
    ]
    assert projected["principals"] == [{"name": "dbo"}]
    assert projected["database_permissions"] == [{"grantee": "public"}]
    assert projected["role_membership"] == shape["role_membership"]
    assert projected["columns"] == ["keep"]


@pytest.mark.parametrize(
    "extra",
    [
        {"mode": "ai"},
        {"assignee": "unmapped"},
        {"assessmentChanged": True},
        {"leadScore": 0},
        {"temperature": "cold"},
        {"readThroughSequence": "0"},
    ],
)
def test_unsupported_conversation_writes_reject_before_any_query(profile, extra):
    body = ConversationMutation.model_validate(
        {
            "operationId": str(uuid4()),
            "expectedRevision": "0",
            "state": "open",
            "priority": "normal",
            "mode": "human",
            "unread": False,
            **extra,
        }
    )
    cursor = Mock()
    with pytest.raises(HTTPException) as error:
        SqlWorkspace(profile).mutate_in(
            cursor, "update_conversation", str(uuid4()), body
        )
    assert error.value.status_code == 503
    cursor.execute.assert_not_called()


@pytest.mark.parametrize(
    "extra",
    [{"mediaId": str(uuid4())}, {"delivery": "external", "identityId": str(uuid4())}],
)
def test_unsupported_messages_reject_before_any_query(profile, extra):
    body = MessageMutation.model_validate(
        {
            "operationId": str(uuid4()),
            "expectedRevision": "0",
            "messageId": str(uuid4()),
            "body": "synthetic",
            **extra,
        }
    )
    cursor = Mock()
    with pytest.raises(HTTPException) as error:
        SqlWorkspace(profile).mutate_in(cursor, "add_message", str(uuid4()), body)
    assert error.value.status_code == 503
    cursor.execute.assert_not_called()


@pytest.mark.parametrize(
    "extra", [{"programId": 1, "program": "Academic"}, {"institutionalProfile": {}}]
)
def test_unsupported_academic_links_reject_before_any_query(profile, extra):
    contact_id = str(uuid4())
    body = ContactMutation.model_validate(
        {
            "operationId": str(uuid4()),
            "expectedRevision": "0",
            "conversationId": str(uuid4()),
            "client": {
                "id": contact_id,
                "name": "Synthetic",
                "phone": "",
                "city": "",
                "program": "",
                "schedule": "",
                "stage": "Trial",
                "tags": "",
                "notes": "",
                "type": "",
                "interests": "",
                "customValues": {},
                **extra,
            },
        }
    )
    cursor = Mock()
    with pytest.raises(HTTPException) as error:
        SqlWorkspace(profile).mutate_in(cursor, "create_contact", contact_id, body)
    assert error.value.status_code == 503
    cursor.execute.assert_not_called()


def test_contract_failure_rolls_back_and_closes_without_repository_queries(
    profile, monkeypatch
):
    import app.sql_workspace as module

    connection = Mock()
    connection.cursor.return_value.execute.return_value.fetchone.return_value = (0,)
    monkeypatch.setattr(module.pyodbc, "connect", lambda *a, **k: connection)
    monkeypatch.setattr(foundation, "verify", Mock(side_effect=ValueError("drift")))
    with pytest.raises(CatalogUnavailable):
        with SqlWorkspace(profile).transaction(write=True):
            pytest.fail("Repository must never receive this cursor")
    connection.commit.assert_not_called()
    connection.rollback.assert_called_once()
    connection.close.assert_called_once()


def test_composition_has_no_demo_catalog_workers_or_provider_state(profile):
    app = create_foundation_app(profile)
    assert not any(
        hasattr(app.state, name)
        for name in (
            "ai",
            "catalog_reader",
            "event_worker",
            "analysis_worker",
            "channel_worker",
            "campaign_worker",
        )
    )
    assert "/api/local/clients" not in [getattr(r, "path", None) for r in app.routes]
    with TestClient(
        app,
        base_url="http://127.0.0.1:8000",
        client=("127.0.0.1", 5000),
        headers={"X-CRM-Local": "1"},
    ) as client:
        assert client.get("/health/live").json()["mode"] == "local_foundation"
        assert client.get("/health/ready").status_code == 503
        for path in (
            "/api/local/admissions",
            "/api/v1/catalog/programs",
            "/api/local/clients",
            "/api/ai/settings",
        ):
            response = client.get(path)
            assert response.status_code == 503
            assert response.headers["cache-control"] == "no-store"
        assert (
            client.get(
                "/api/local/foundation", headers={"X-CRM-Local": "0"}
            ).status_code
            == 403
        )
        assert (
            client.get(
                "/api/local/foundation", headers={"Origin": "https://foreign.invalid"}
            ).status_code
            == 403
        )
        assert (
            client.put(
                "/api/v1/agents/profiles/" + str(uuid4()),
                content="x" * 64001,
                headers={"Content-Type": "application/json"},
            ).status_code
            == 413
        )


def test_effective_permission_null_is_rejected(profile, monkeypatch):
    keys = (
        "class_desc",
        "permission_name",
        "state_desc",
        "target",
        "minor_id",
        "grantor",
    )
    monkeypatch.setattr(
        foundation,
        "runtime_permissions",
        lambda cursor: [
            dict(zip(keys, row, strict=True))
            for row in foundation.expected_permissions()
        ],
    )
    cursor = Mock()
    cursor.execute.return_value.fetchone.side_effect = [
        (foundation.PRINCIPAL,) * 3 + ("SYNTHETIC",) + (0,) * 7 + (1,),
        None,
        None,
        (50, 1),
    ]
    with pytest.raises(ValueError):
        foundation.verify_acl(cursor, foundation.ticket(profile))


def test_overgrant_is_rejected_even_if_shapes_match(profile, monkeypatch):
    monkeypatch.setattr(foundation, "runtime_permissions", lambda cursor: [])
    with pytest.raises(ValueError):
        foundation.verify_acl(Mock(), foundation.ticket(profile))


@pytest.mark.parametrize(
    "scope,permission",
    [
        ("SERVER", "ALTER ANY LOGIN"),
        ("DATABASE", "IMPERSONATE ANY USER"),
        ("SERVER", None),
        ("DATABASE", "ALTER ANY ROLE"),
    ],
)
def test_effective_global_elevation_or_unknown_permission_is_rejected(
    scope, permission
):
    cursor = Mock()
    cursor.execute.return_value.fetchall.side_effect = [
        [(p,) for p in allowed | ({permission} if name == scope else set())]
        for name, allowed in foundation.GLOBAL_PERMISSIONS.items()
    ]
    with pytest.raises(ValueError):
        foundation.verify_global_permissions(cursor)
