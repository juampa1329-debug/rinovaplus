"""Connection selection uses synthetic SQL and temporary encrypted storage."""

import json
from unittest.mock import Mock

import pyodbc
import pytest
from fastapi.testclient import TestClient

from app.database_connections import (
    COLUMNS_SQL,
    DATABASES_SQL,
    IDENTITY_SQL,
    RELATIONS_SQL,
    TABLES_SQL,
    VISIBILITY_SQL,
    ConnectionRequest,
    DatabaseConnections,
)
from app.main import create_app
from app.sql_profile import ProfileUnavailable, SqlProfileStore

SECRET = "synthetic-db-password-DO-NOT-REFLECT"
BODY = {
    "server": "sql.example.invalid",
    "port": 1433,
    "username": "reader",
    "password": SECRET,
    "certificate_hostname": "sql.example.invalid",
    "database": "fragment",
    "revision": 0,
}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("CRM_AI_STATE_DIR", str(tmp_path))
    application = create_app()
    with TestClient(
        application,
        base_url="http://127.0.0.1:8002",
        client=("127.0.0.1", 1234),
        headers={"X-CRM-Local": "1"},
    ) as http:
        yield http, application.state.database_connections


@pytest.fixture
def fake_sql(monkeypatch):
    statements = []
    cursor = Mock()
    connection = Mock()
    connection.cursor.return_value = cursor

    def execute(sql):
        assert sql in (
            DATABASES_SQL,
            IDENTITY_SQL,
            TABLES_SQL,
            COLUMNS_SQL,
            RELATIONS_SQL,
            VISIBILITY_SQL,
        ), "Only fixed SELECT metadata statements are accepted"
        assert sql.lstrip().startswith("SELECT")
        statements.append(sql)
        cursor.fetchone.return_value = (
            (1, 0)
            if sql == VISIBILITY_SQL
            else (
                "fragment",
                r"LOCAL\SQLEXPRESS",
                "LOCAL",
                "SQLEXPRESS",
                16,
                "Express",
                160,
            )
        )
        cursor.fetchmany.return_value = {
            DATABASES_SQL: [("fragment",)],
            TABLES_SQL: [("dbo", "ACProgramas")],
            COLUMNS_SQL: [
                ("dbo", "ACProgramas", "Id_Programa", "int", 4, 10, 0, False, 1)
            ],
            RELATIONS_SQL: [],
        }.get(sql, [])
        return cursor

    cursor.execute.side_effect = execute
    connect = Mock(return_value=connection)
    monkeypatch.setattr(pyodbc, "connect", connect)
    return connect, connection, cursor, statements


def test_status_has_no_sql_side_effect_or_password(client, fake_sql):
    http, _ = client
    connect, *_ = fake_sql
    result = http.get("/api/local/database")
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    assert "password" not in result.json()["connection"]
    connect.assert_not_called()


@pytest.mark.parametrize(
    "headers",
    [
        {"X-CRM-Local": "0"},
        {"Origin": "https://evil.invalid"},
        {"Host": "evil.invalid"},
    ],
)
def test_untrusted_requests_cannot_access_credentials_or_connect(
    client, fake_sql, headers
):
    http, _ = client
    result = http.post("/api/local/database/discover", json=BODY, headers=headers)
    assert result.status_code == 403
    fake_sql[0].assert_not_called()


@pytest.mark.parametrize(
    "changes",
    [
        {"server": "sql;Encrypt=No"},
        {"certificate_hostname": "*.invalid"},
        {"port": 65536},
        {"trust_server_certificate": True},
        {"password": "bad\nsecret"},
        {"database": "bad\0name"},
    ],
)
def test_invalid_or_injected_fields_rejected_without_reflection(
    client, fake_sql, changes
):
    http, _ = client
    result = http.post("/api/local/database/test", json=BODY | changes)
    assert result.status_code == 422
    assert SECRET not in result.text
    fake_sql[0].assert_not_called()


def test_discovery_test_save_reload_and_schema_are_readonly(client, fake_sql):
    http, service = client
    assert http.post("/api/local/database/discover", json=BODY).json() == {
        "databases": ["fragment"]
    }
    assert not service.store.path.exists()
    tested = http.post("/api/local/database/test", json=BODY)
    assert tested.status_code == 200
    review = tested.json()["review"]
    assert review["engine_major"] == 16
    assert review["crm_activation"] == "not_activated"
    assert review["missing_crm_tables"]
    assert not service.store.path.exists()
    saved = http.put("/api/local/database", json=BODY)
    assert saved.status_code == 200 and saved.json()["revision"] == 1
    assert SECRET.encode() not in service.store.path.read_bytes()
    assert service.store.load()["connection"]["password"] == SECRET
    status = http.get("/api/local/database").json()
    assert status["connection"]["database"] == "fragment" and status["has_password"]
    assert SECRET not in json.dumps(status)
    schema = http.post("/api/local/database/schema", json=BODY | {"password": ""})
    assert schema.status_code == 200 and len(schema.json()["columns"]) == 1
    assert SECRET not in schema.text
    assert all(sql.lstrip().startswith("SELECT") for sql in fake_sql[3])
    text = fake_sql[0].call_args.args[0]
    assert "Encrypt=Yes;TrustServerCertificate=No;" in text
    assert fake_sql[0].call_args.kwargs == {
        "timeout": 5,
        "autocommit": True,
        "readonly": True,
    }
    assert fake_sql[1].close.call_count == 4
    assert fake_sql[2].close.call_count == 4


def test_stale_revision_and_cross_server_password_reuse_rejected(client, fake_sql):
    http, service = client
    assert http.put("/api/local/database", json=BODY).status_code == 200
    original = service.store.path.read_bytes()
    assert http.put("/api/local/database", json=BODY).status_code == 409
    assert service.store.path.read_bytes() == original
    result = http.post(
        "/api/local/database/test",
        json=BODY | {"server": "other.invalid", "password": ""},
    )
    assert result.status_code == 422
    assert result.json()["detail"] == "sql_credentials_required"


def test_login_error_redacted_and_capacity_released(client, fake_sql):
    http, _ = client
    fake_sql[0].side_effect = pyodbc.Error("28000", "private-server " + SECRET)
    for _ in range(2):
        result = http.post("/api/local/database/test", json=BODY)
        assert result.status_code == 503
        assert result.json()["detail"] == "sql_login_or_database_denied"
        assert SECRET not in result.text and "private-server" not in result.text


def test_lost_key_fails_closed_without_destroying_saved_profile(client, fake_sql):
    http, service = client
    assert http.put("/api/local/database", json=BODY).status_code == 200
    original = service.store.path.read_bytes()
    service.store.key_path.unlink()
    assert http.get("/api/local/database").status_code == 503
    assert (
        http.put("/api/local/database", json=BODY | {"revision": 1}).status_code == 503
    )
    assert service.store.path.read_bytes() == original
    assert not service.store.key_path.exists()


def test_ciphertext_tampering_and_missing_key_not_silently_reset(tmp_path):
    store = SqlProfileStore(tmp_path / "database")
    store.save({"revision": 1, "connection": {"password": SECRET}})
    encrypted = bytearray(store.path.read_bytes())
    encrypted[-1] ^= 1
    store.path.write_bytes(encrypted)
    with pytest.raises(ProfileUnavailable):
        store.load()


def test_authenticated_but_malformed_profile_fails_closed(tmp_path):
    store = SqlProfileStore(tmp_path / "database")
    store.save({"revision": 1, "connection": {"password": SECRET}, "review": {}})
    original = store.path.read_bytes()
    with pytest.raises(ProfileUnavailable):
        store.load()
    assert store.path.read_bytes() == original


def test_odbc_database_and_credentials_are_delimited(tmp_path, monkeypatch):
    service = DatabaseConnections(SqlProfileStore(tmp_path))
    connect = Mock(side_effect=pyodbc.Error("08001", "synthetic"))
    monkeypatch.setattr(pyodbc, "connect", connect)
    value = ConnectionRequest.model_validate(
        BODY
        | {
            "database": "fragment};Encrypt=No",
            "password": "p};Encrypt=No",
        }
    )
    with pytest.raises(Exception):
        service.inspect(value)
    text = connect.call_args.args[0]
    assert (
        "DATABASE={fragment}};Encrypt=No};Encrypt=Yes;TrustServerCertificate=No;"
        in text
    )
    assert "PWD={p}};Encrypt=No};" in text
