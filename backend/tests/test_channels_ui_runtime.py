"""Offline C9 UI profile, column-permission and local API boundary regressions."""

import hashlib
import json
from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pyodbc
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import channels_ui_app as ui
from app import channels_ui_contract as contract
from app.config import Settings
from app.sql_target import connection_string


@pytest.fixture
def profile(tmp_path):
    database = "CBN_C9_TRIAL_20261025_1234abcd"
    user = contract.principal(database)
    path = tmp_path / "ticket.json"
    value = {
        "scope": "SQL-C9-restored-channels-ui-only",
        "release_sha256": contract.RELEASE_SHA,
        "catalog_version": "cbn-channels-runtime-catalog-v1",
        "identity": {
            "database": database,
            "engine": 16,
            "compatibility": 160,
            "machine": "C9-TEST",
            "server": "C9-TEST\\SQLEXPRESS",
        },
        "credential_access": False,
        "login_sid": "C9-SID",
        "protected_logins": ["synthetic-admin"],
    }
    path.write_text(json.dumps(value), encoding="utf-8")
    return Settings(
        mode="local_channels_ui",
        sql_environment="channels_ui_rehearsal",
        sql_host="host.docker.internal",
        sql_database=database,
        sql_user=user,
        sql_password="synthetic};Encrypt=No",
        sql_certificate_hostname="localhost",
        sql_expected_machine="C9-TEST",
        sql_expected_server="C9-TEST\\SQLEXPRESS",
        sql_expected_login=user,
        sql_expected_database_user=user,
        channels_ticket_path=str(path),
        channels_ticket_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


@pytest.mark.parametrize(
    "change",
    [
        {"mode": "local_demo"},
        {"mode": "local_channels"},
        {"mode": "local_foundation"},
        {"sql_environment": "channels_rehearsal"},
        {"sql_environment": "institutional"},
        {"sql_database": "HORARIOSSIIE"},
        {"sql_database": "CBN_C8_TRIAL_20261025_1234abcd"},
        {"sql_database": "CBN_C3_TRIAL_20261024_ac8505b8"},
        {"sql_user": "sa"},
        {"sql_expected_database_user": "dbo"},
        {"sql_host": "remote.invalid"},
        {"sql_certificate_hostname": "remote.invalid"},
        {"sql_password": ""},
        {"channels_ticket_path": "relative.json"},
        {"channels_key_path": "/synthetic/provider.key"},
        {"channels_key_sha256": "a" * 64},
    ],
)
def test_rejects_foreign_profile_and_provider_key(profile, change):
    with pytest.raises(ValueError):
        connection_string(replace(profile, **change))


def test_tls_password_escaping_and_no_catalog_access(profile):
    value = connection_string(profile)
    assert "Encrypt=Yes;TrustServerCertificate=No;" in value
    assert "PWD={synthetic}};Encrypt=No};" in value
    assert profile.sql_password not in repr(profile)
    assert not profile.channels_key_path and not profile.channels_key_sha256
    with pytest.raises(ValueError):
        connection_string(profile, catalog=True)


def test_own_profile_required_without_environment_fallback(monkeypatch):
    monkeypatch.setenv("CRM_APP_MODE", "local_channels_ui")
    with pytest.raises(ValueError):
        Settings.from_environment()
    monkeypatch.setenv("CRM_CHANNELS_UI_PROFILE_DIR", "/synthetic/ui")
    monkeypatch.setenv("CRM_CHANNELS_PROFILE_DIR", "/synthetic/repositories")
    with pytest.raises(ValueError):
        Settings.from_environment()


def test_encrypted_profile_needs_no_provider_key(profile, tmp_path):
    from pathlib import Path

    from app.channels_ui_profile import load_settings
    from app.sql_profile import ProfileUnavailable, SqlProfileStore

    directory = tmp_path / "prepared-ui"
    directory.mkdir()
    (directory / "runtime-ticket.json").write_bytes(
        Path(profile.channels_ticket_path).read_bytes()
    )
    store = SqlProfileStore(directory / "runtime")
    store.save(
        {
            "revision": 1,
            "connection": {
                "server": profile.sql_host,
                "port": profile.sql_port,
                "username": profile.sql_user,
                "password": profile.sql_password,
                "certificate_hostname": "localhost",
                "database": profile.sql_database,
            },
            "review": {
                "machine": profile.sql_expected_machine,
                "server": profile.sql_expected_server,
                "ticket_sha256": profile.channels_ticket_sha256,
            },
        }
    )
    loaded = load_settings(directory)
    assert loaded.mode == "local_channels_ui"
    assert not loaded.channels_key_path and not loaded.channels_key_sha256
    assert not (directory / "channels-aes256.key").exists()
    store.key_path.unlink()
    with pytest.raises(ProfileUnavailable):
        load_settings(directory)
    assert not store.key_path.exists()


def test_ticket_rejects_credential_access_even_with_matching_hash(profile):
    from pathlib import Path

    path = Path(profile.channels_ticket_path)
    value = json.loads(path.read_text(encoding="utf-8"))
    value["credential_access"] = True
    path.write_text(json.dumps(value), encoding="utf-8")
    current = replace(
        profile, channels_ticket_sha256=hashlib.sha256(path.read_bytes()).hexdigest()
    )
    with pytest.raises(ValueError, match="channels_ticket_contract"):
        contract.ticket(current)


def test_acl_grants_only_two_credential_columns_and_no_crm_dml(profile):
    acl = contract.expected_acl(profile.sql_user)
    grants = [row for row in acl if row[3] == "GRANT"]
    assert len(grants) == 15
    assert sum(row[3] == "DENY" for row in acl) == 7
    credential = {row for row in grants if row[1] == "crm_channels.Credential"}
    assert credential == {
        ("OBJECT_OR_COLUMN", "crm_channels.Credential", "SELECT", "GRANT", 1, "dbo"),
        ("OBJECT_OR_COLUMN", "crm_channels.Credential", "SELECT", "GRANT", 2, "dbo"),
    }
    assert all(
        not table.startswith("crm.")
        and not (table == "crm_meta.MigrationJournal" and permission != "SELECT")
        and not (table == "crm_channels.outbound_queue" and permission != "SELECT")
        for _, table, permission, *_ in grants
    )


@pytest.fixture
def acl_context(profile, monkeypatch):
    user = profile.sql_user
    columns = [
        {"name": name, "column_id": index, "allowed": int(index < 3)}
        for index, name in enumerate(
            ("Channel", "Kind", "KeyId", "Nonce", "Ciphertext"), 1
        )
    ]
    powers = [
        {
            "table_name": table,
            "permission_name": permission,
            "value": int(permission in contract.RIGHTS.get(table, ())),
        }
        for table in (
            contract.PARTITION["academic"]
            + contract.PARTITION["foundation"]
            + contract.PARTITION["extension"]
        )
        for permission in (
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "ALTER",
            "REFERENCES",
            "CONTROL",
        )
    ]
    shape = {
        "principals": [
            {
                "name": user,
                "sid": "C9-SID",
                "type_desc": "SQL_USER",
                "authentication_type_desc": "INSTANCE",
                "default_schema_name": "crm_channels",
            }
        ],
        "all_permissions": [
            dict(
                zip(
                    (
                        "class_desc",
                        "target",
                        "permission_name",
                        "state_desc",
                        "minor_id",
                        "grantor",
                    ),
                    row,
                    strict=True,
                ),
                grantee=user,
            )
            for row in contract.expected_acl(user)
        ],
        "role_membership": [],
        "schemas": [],
    }
    cursor = Mock()
    cursor.execute.return_value.fetchone.return_value = (
        user,
        user,
        user,
        "C9-SID",
        0,
        0,
        0,
        1,
    )
    cursor.execute.return_value.fetchval.return_value = 0
    monkeypatch.setattr(contract, "verify_global_permissions", lambda *_: None)
    monkeypatch.setattr(
        contract,
        "records",
        lambda _cursor, sql: powers if "FROM sys.tables" in sql else columns,
    )
    return cursor, shape, powers, columns


def test_column_acl_accepts_valid_read_only_boundary(profile, acl_context):
    cursor, shape, powers, _ = acl_context
    for row in powers:
        if row["table_name"] == "crm_channels.Credential":
            if row["permission_name"] == "SELECT":
                row["value"] = None  # Per-column checks are authoritative.
    contract.verify_acl(
        cursor, profile, {"login_sid": "C9-SID", "protected_logins": []}, shape
    )


@pytest.mark.parametrize(
    "column,value",
    [
        ("KeyId", 1),
        ("Nonce", 1),
        ("Ciphertext", 1),
        ("Ciphertext", None),
        ("Channel", 0),
        ("Kind", None),
    ],
)
def test_column_acl_rejects_hidden_reads_and_inconclusive_access(
    profile, acl_context, column, value
):
    cursor, shape, _, columns = acl_context
    next(c for c in columns if c["name"] == column)["allowed"] = value
    with pytest.raises(ValueError, match="channels_ui_credential_column_access"):
        contract.verify_acl(
            cursor, profile, {"login_sid": "C9-SID", "protected_logins": []}, shape
        )


def test_effective_queue_write_rejected_even_without_direct_grant(profile, acl_context):
    cursor, shape, powers, _ = acl_context
    next(
        row
        for row in powers
        if row["table_name"] == "crm_channels.outbound_queue"
        and row["permission_name"] == "INSERT"
    )["value"] = 1
    with pytest.raises(ValueError, match="channels_effective_object_permission"):
        contract.verify_acl(
            cursor, profile, {"login_sid": "C9-SID", "protected_logins": []}, shape
        )


@pytest.mark.parametrize("write", [False, True])
def test_guard_precedes_body_under_correct_locks(profile, monkeypatch, write):
    connection = Mock()
    cursor = connection.cursor.return_value
    cursor.execute.return_value.fetchone.return_value = (0,)
    monkeypatch.setattr(pyodbc, "connect", lambda *a, **k: connection)
    checked = []

    def verify(actual, settings):
        assert actual is cursor and settings is profile
        calls = cursor.execute.call_args_list
        assert calls[1].args[1:] == ("crm.schema.migrate.v1", "Shared")
        assert calls[2].args[1:] == (
            "crm.local.commit",
            "Exclusive" if write else "Shared",
        )
        checked.append(True)

    monkeypatch.setattr(contract, "verify", verify)
    with contract.transaction(profile, write=write) as active:
        assert active is cursor and checked
    connection.commit.assert_called_once()
    connection.rollback.assert_not_called()
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


def test_guard_cleanup_keeps_sanitized_error(profile, monkeypatch):
    connection = Mock()
    cursor = connection.cursor.return_value
    cursor.execute.return_value.fetchone.return_value = (0,)
    monkeypatch.setattr(pyodbc, "connect", lambda *a, **k: connection)
    monkeypatch.setattr(
        contract, "verify", Mock(side_effect=ValueError("synthetic secret"))
    )
    connection.rollback.side_effect = pyodbc.Error("08S01", "synthetic secret")
    connection.close.side_effect = pyodbc.Error("08S01", "synthetic secret")
    cursor.close.side_effect = pyodbc.Error("08S01", "synthetic secret")
    with pytest.raises(HTTPException) as error:
        with contract.transaction(profile):
            pytest.fail("Unverified transaction yielded a business cursor")
    assert error.value.status_code == 503
    assert error.value.detail == "channels_storage_unavailable"


@pytest.fixture
def client(profile, monkeypatch):
    @contextmanager
    def local_transaction(settings, *, write=False):
        assert settings is profile
        yield Mock()

    monkeypatch.setattr(ui, "transaction", local_transaction)
    application = ui.create_channels_ui_app(profile)
    return TestClient(
        application,
        base_url="http://127.0.0.1:4175",
        client=("127.0.0.1", 50000),
        headers={"X-CRM-Local": "1"},
    )


def test_manifest_v2_only_advertises_safe_ui_capabilities(client):
    response = client.get("/api/local/runtime")
    assert response.status_code == 200
    value = response.json()
    assert value["version"] == "cbn-ui-capabilities-v2"
    assert value["profile"] == "channels" and value["modules"] == ["settings"]
    assert all(flag is False for flag in value["features"].values())
    for key in (
        "credentials",
        "providerActions",
        "externalDelivery",
        "publicWebhooks",
        "workers",
    ):
        assert value["channels"][key] is False
    assert not hasattr(client.app.state, "channel_worker")


def test_main_uses_ui_composition_without_crm_or_workers(profile, monkeypatch):
    from app import main
    from app.modules.channels import workers

    def forbidden(*args, **kwargs):
        pytest.fail("C9 UI must not construct the CRM workspace or workers")

    monkeypatch.setattr(main, "install_sql_workspace", forbidden)
    monkeypatch.setattr(workers, "ChannelWorkers", forbidden)
    application = main.create_app(settings=profile)
    assert application.version == "SQL-C9"
    assert not hasattr(application.state, "sql_workspace")
    assert not hasattr(application.state, "channel_worker")


@pytest.mark.parametrize(
    "headers",
    [
        {"X-CRM-Local": "0"},
        {"Host": "remote.invalid:4175"},
        {"Origin": "https://remote.invalid"},
        {"Origin": "http://127.0.0.1:4999"},
    ],
)
def test_manifest_requires_local_host_origin_and_header(client, headers):
    assert client.get("/api/local/runtime", headers=headers).status_code == 403


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/channels/whatsapp/activation",
        "/api/v1/channels/whatsapp/discovery",
        "/api/v1/channels/transport/retry-receipts",
        "/api/v1/webhooks/meta",
        "/api/v1/social-comments/123/reply",
        "/api/local/crm/inbox",
    ],
)
def test_external_and_crm_routes_remain_unavailable(client, path):
    response = client.post(path, json={})
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "body",
    [
        {"revision": 0, "configuration": {}, key: "must-not-echo"}
        for key in ("accessToken", "appSecret", "verifyToken", "refreshToken")
    ]
    + [
        {"revision": True, "configuration": {}},
        {"revision": 0, "configuration": {"callbackUrl": "http://unsafe.invalid"}},
    ],
)
def test_draft_rejects_secrets_and_invalid_dtos(client, body):
    response = client.put("/api/v1/channels/whatsapp/draft", json=body)
    assert response.status_code == 422
    assert "must-not-echo" not in response.text


def test_public_account_redacts_provider_status_and_credential_presence(
    client, monkeypatch
):
    store = client.app.state.channel_store
    monkeypatch.setattr(
        store,
        "get",
        lambda *_: {
            "channel": "whatsapp",
            "configuration": {},
            "revision": 2,
            "state": "connected",
            "credentials": ["accessToken"],
            "capabilities": {"messages": True},
            "verifiedAt": "synthetic",
            "lastError": "must-not-echo",
        },
    )
    value = client.get("/api/v1/channels/whatsapp").json()
    assert value["state"] == "configured"
    assert value["credentials"] == [] and value["capabilities"] == {}
    assert value["verifiedAt"] is None and value["lastError"] is None
    assert "must-not-echo" not in json.dumps(value)


def test_stage_options_read_foundation_and_reject_inactive_choice(client, monkeypatch):
    config = SimpleNamespace(
        stages=[
            SimpleNamespace(label="Active", active=True),
            SimpleNamespace(label="Inactive", active=False),
        ]
    )
    reader = Mock(return_value=(config, "1"))
    monkeypatch.setattr(ui, "read_configuration", reader)
    assert client.get("/api/local/channels/stages").json() == {"stages": ["Active"]}
    assert reader.call_args.kwargs == {"foundation": True}
    response = client.put(
        "/api/v1/channels/whatsapp/draft",
        json={"revision": 0, "configuration": {"initialStage": "Inactive"}},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("method", ["key", "secrets", "write_secret"])
def test_provider_secrets_are_blocked_without_files_or_sql(profile, method):
    store = ui.ChannelUiStore(profile)
    assert not hasattr(store, "key_path")
    args = {
        "key": (None,),
        "secrets": (None, "whatsapp"),
        "write_secret": (None, "whatsapp", "accessToken", "synthetic"),
    }
    with pytest.raises(HTTPException) as error:
        getattr(store, method)(*args[method])
    assert error.value.detail == "channels_ui_credentials_unavailable"
