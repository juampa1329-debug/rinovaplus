"""C8 isolated profile, TLS, fail-closed transaction and API boundary regressions."""

import hashlib
import json
from dataclasses import replace
from unittest.mock import Mock

import pyodbc
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import channels_contract as contract
from app.channels_app import create_channels_app
from app.channels_catalog import metadata
from app.config import Settings
from app.modules.channels.storage import ChannelStore
from app.sql_target import connection_string


@pytest.fixture
def profile(tmp_path):
    database = "CBN_C8_TRIAL_20261025_1234abcd"
    user = contract.principal(database)
    key = bytes(range(32))
    path = tmp_path / "ticket.json"
    key_path = tmp_path / "channels.key"
    key_path.write_bytes(key)
    key_hash = hashlib.sha256(key).hexdigest()
    value = {
        "scope": "SQL-C8-restored-channels-only",
        "release_sha256": contract.RELEASE_SHA,
        "catalog_version": "cbn-channels-runtime-catalog-v1",
        "identity": {
            "database": database,
            "engine": 16,
            "compatibility": 160,
            "machine": "C8-TEST",
            "server": "C8-TEST\\SQLEXPRESS",
        },
        "credential_key_sha256": key_hash,
    }
    path.write_text(json.dumps(value), encoding="utf-8")
    return Settings(
        mode="local_channels",
        sql_environment="channels_rehearsal",
        sql_host="host.docker.internal",
        sql_database=database,
        sql_user=user,
        sql_password="synthetic};Encrypt=No",
        sql_certificate_hostname="localhost",
        sql_expected_machine="C8-TEST",
        sql_expected_server="C8-TEST\\SQLEXPRESS",
        sql_expected_login=user,
        sql_expected_database_user=user,
        channels_ticket_path=str(path),
        channels_ticket_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        channels_key_path=str(key_path),
        channels_key_sha256=key_hash,
    )


@pytest.mark.parametrize(
    "change",
    [
        {"mode": "local_demo"},
        {"mode": "local_sql_copy"},
        {"mode": "local_foundation"},
        {"sql_environment": "institutional"},
        {"sql_environment": "foundation_rehearsal"},
        {"sql_database": "HORARIOSSIIE"},
        {"sql_database": "CBN_C7_TRIAL_20261025_1234abcd"},
        {"sql_database": "CBN_C3_TRIAL_20261024_ac8505b8"},
        {"sql_user": "sa"},
        {"sql_password": ""},
        {"sql_expected_database_user": "dbo"},
        {"sql_host": "remote.invalid"},
        {"sql_host": ""},
        {"sql_port": 0},
        {"sql_certificate_hostname": "remote.invalid"},
        {"sql_expected_machine": ""},
        {"sql_expected_server": ""},
        {"channels_ticket_path": "relative.json"},
        {"channels_ticket_sha256": "unverified"},
        {"channels_key_path": "relative.key"},
        {"channels_key_sha256": ""},
    ],
)
def test_profile_rejects_unsafe_or_mixed_targets(profile, change):
    with pytest.raises(ValueError):
        connection_string(replace(profile, **change))


def test_tls_cannot_be_disabled_and_secrets_are_not_repr(profile):
    value = connection_string(profile)
    assert "Encrypt=Yes;TrustServerCertificate=No;" in value
    assert "PWD={synthetic}};Encrypt=No};" in value
    assert profile.sql_password not in repr(profile)
    with pytest.raises(ValueError):
        connection_string(profile, catalog=True)


def test_profile_requires_own_environment_directory(monkeypatch, profile):
    monkeypatch.setenv("CRM_APP_MODE", "local_channels")
    with pytest.raises(ValueError):
        Settings.from_environment()
    monkeypatch.setenv("CRM_CHANNELS_PROFILE_DIR", "/synthetic/channels")
    monkeypatch.setenv("CRM_FOUNDATION_PROFILE_DIR", "/synthetic/foundation")
    with pytest.raises(ValueError):
        Settings.from_environment()


@pytest.fixture
def encrypted_profile(profile, tmp_path):
    from pathlib import Path

    from app.sql_profile import SqlProfileStore

    directory = tmp_path / "prepared"
    directory.mkdir()
    (directory / "runtime-ticket.json").write_bytes(
        Path(profile.channels_ticket_path).read_bytes()
    )
    (directory / "channels-aes256.key").write_bytes(
        Path(profile.channels_key_path).read_bytes()
    )
    SqlProfileStore(directory / "runtime").save(
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
                "credential_key_sha256": profile.channels_key_sha256,
            },
        }
    )
    return directory


def test_encrypted_profile_loads_and_rejects_foreign_identity(encrypted_profile):
    from app.channels_profile import load_settings
    from app.sql_profile import SqlProfileStore

    settings = load_settings(encrypted_profile)
    assert settings.mode == "local_channels" and settings.sql_password
    store = SqlProfileStore(encrypted_profile / "runtime")
    value = store.load()
    value["connection"]["username"] = "cbn_foundation_runtime_c4"
    store.save(value)
    with pytest.raises(ValueError):
        load_settings(encrypted_profile)


def test_encrypted_profile_missing_key_fails_without_recreation(encrypted_profile):
    from app.channels_profile import load_settings
    from app.sql_profile import ProfileUnavailable, SqlProfileStore

    store = SqlProfileStore(encrypted_profile / "runtime")
    store.key_path.unlink()
    with pytest.raises(ProfileUnavailable):
        load_settings(encrypted_profile)
    assert not store.key_path.exists()


def test_main_composition_does_not_construct_workers(profile, monkeypatch):
    from app.main import create_app
    from app.modules.channels import workers

    def forbidden(*args, **kwargs):
        raise AssertionError("C8 must not construct channel workers")

    monkeypatch.setattr(workers, "ChannelWorkers", forbidden)
    application = create_app(settings=profile)
    assert not hasattr(application.state, "channel_worker")
    assert application.version == "SQL-C8"


def test_ticket_hash_target_and_key_are_pinned(profile):
    contract.ticket(profile)
    with pytest.raises(ValueError):
        contract.ticket(replace(profile, channels_key_sha256="a" * 64))
    with pytest.raises(ValueError):
        contract.ticket(replace(profile, channels_ticket_sha256="a" * 64))


def test_independent_key_missing_or_changed_fails_without_generation(profile):
    from pathlib import Path

    store = ChannelStore(profile)
    assert store.key(None) == bytes(range(32))
    Path(profile.channels_key_path).unlink()
    with pytest.raises(HTTPException) as error:
        store.key(None)
    assert error.value.detail == "channel_encryption_key_unavailable"
    assert not Path(profile.channels_key_path).exists()


@pytest.mark.parametrize("failure", ["guard", "body", "commit", "guard_cleanup"])
def test_transaction_guards_under_locks_and_rolls_back(profile, monkeypatch, failure):
    connection = Mock()
    cursor = connection.cursor.return_value
    cursor.execute.return_value.fetchone.return_value = (0,)
    monkeypatch.setattr(pyodbc, "connect", lambda *a, **k: connection)
    checked = []

    def verify(c, s):
        assert c is cursor and s is profile
        assert cursor.execute.call_count == 3
        checked.append(True)
        if failure in ("guard", "guard_cleanup"):
            raise ValueError("synthetic drift")

    monkeypatch.setattr(contract, "verify", verify)
    if failure == "commit":
        connection.commit.side_effect = pyodbc.Error("08007", "synthetic secret")
    if failure == "guard_cleanup":
        connection.rollback.side_effect = pyodbc.Error("08S01", "synthetic secret")
        connection.close.side_effect = pyodbc.Error("08S01", "synthetic secret")
        cursor.close.side_effect = pyodbc.Error("08S01", "synthetic secret")
    with pytest.raises(HTTPException) as error:
        with ChannelStore(profile).transaction():
            assert checked
            if failure == "body":
                raise HTTPException(409, "synthetic_conflict")
    assert error.value.status_code == (409 if failure == "body" else 503)
    assert "secret" not in str(error.value.detail)
    connection.rollback.assert_called_once()
    connection.close.assert_called_once()
    cursor.close.assert_called_once()


def test_metadata_normalizes_identity_before_sorting(monkeypatch):
    from app import channels_catalog

    cursor = Mock()
    cursor.execute.return_value.fetchval.return_value = 1
    last = [None]
    monkeypatch.setattr(channels_catalog, "records", lambda *_: [])

    def legacy(_cursor, managed):
        return {
            "version": "old",
            "ddl_triggers": [],
            "columns": []
            if managed
            else [
                {"schema_name": "dbo", "name": "Id", "identity_last_value": 42},
                {
                    "schema_name": "crm_channels",
                    "name": "Id",
                    "identity_last_value": last[0],
                },
            ],
        }

    monkeypatch.setattr(channels_catalog, "legacy_metadata", legacy)
    before = metadata(cursor)
    last[0] = 1
    assert metadata(cursor) == before
    cursor.execute.return_value.fetchval.return_value = 0
    with pytest.raises(ValueError):
        metadata(cursor)


@pytest.fixture
def client(profile):
    return TestClient(
        create_channels_app(profile),
        base_url="http://127.0.0.1:4173",
        client=("127.0.0.1", 50000),
        headers={"X-CRM-Local": "1"},
    )


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/v1/channels/whatsapp/activate"),
        ("post", "/api/v1/channels/whatsapp/test"),
        ("get", "/api/v1/channels/whatsapp/numbers"),
        ("post", "/api/v1/channels/transport/retry"),
        ("post", "/api/v1/webhooks/meta"),
        ("post", "/api/v1/social-comments/123/reply"),
        ("get", "/api/local/crm/inbox"),
    ],
)
def test_provider_workers_and_unavailable_modules_are_not_mounted(client, method, path):
    response = client.request(method, path, json={} if method == "post" else None)
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "body",
    [
        {"revision": 0, "configuration": {}, "accessToken": "must-not-echo"},
        {"revision": True, "configuration": {}},
        {"revision": 0, "configuration": {"callbackUrl": "http://unsafe.invalid"}},
    ],
)
def test_draft_rejects_provider_credentials_and_invalid_values(client, body):
    response = client.put("/api/v1/channels/whatsapp/draft", json=body)
    assert response.status_code == 422
    assert "must-not-echo" not in response.text


def test_local_api_guard_and_pagination(client):
    response = client.get("/api/v1/channels", headers={"X-CRM-Local": "0"})
    assert response.status_code == 403
    assert client.get("/api/v1/social-comments?limit=101").status_code == 422
    runtime = client.get("/api/local/runtime").json()
    assert not runtime["features"]["externalDelivery"]
    assert not runtime["features"]["workers"]
    assert not hasattr(client.app.state, "channel_worker")
    assert client.get("/health/ready").status_code == 503
    for path in ("/api/local/runtime", "/api/unknown"):
        assert client.get(path, headers={"X-CRM-Local": "0"}).status_code == 403
    assert client.get("/api/unknown").status_code == 503
    assert client.get("/health/live", headers={"X-CRM-Local": "0"}).status_code == 200
