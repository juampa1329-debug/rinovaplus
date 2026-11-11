"""Container compatibility preserves opt-in IO, local guards and durable budgets."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.modules.ai.api.router import install_ai
from app.modules.ai.infrastructure.media import MediaGateway
from app.modules.catalog.infrastructure.sql_reader import SqlCatalogReader


def test_linux_environment_credentials_and_state_survive_restart(monkeypatch, tmp_path):
    from app.modules.ai.api import router as ai_routes

    monkeypatch.setattr(
        ai_routes,
        "os",
        SimpleNamespace(
            name="posix",
            environ={
                "CRM_AI_STATE_DIR": str(tmp_path),
                "GEMINI_API_KEY": "synthetic-environment-key",
                "CRM_AI_OUTBOUND_ENABLED": "false",
            },
        ),
    )
    app = FastAPI()
    app.state.settings = Settings()
    install_ai(app)
    with TestClient(
        app,
        base_url="http://127.0.0.1:8002",
        client=("127.0.0.1", 1234),
        headers={"X-CRM-Local": "1"},
    ) as client:
        snapshot = client.get("/api/ai/settings").json()
        assert snapshot["credential_storage_available"] is False
        assert snapshot["outbound_enabled"] is False
        assert snapshot["providers"][0]["credential_source"] == "environment"
        assert "synthetic-environment-key" not in str(snapshot)
        assert (
            client.put(
                "/api/ai/credentials/gemini",
                json={"revision": 0, "api_key": "never-written"},
            ).status_code
            == 503
        )
        assert (
            client.put(
                "/api/ai/outbound", json={"revision": 0, "enabled": True}
            ).status_code
            == 503
        )
        saved = client.put(
            "/api/ai/settings",
            json={"revision": 0, "settings": snapshot["settings"]},
        )
        assert saved.status_code == 200
        identifier = client.post("/api/ai/conversation", json={}).json()[
            "conversation_id"
        ]
    service = app.state.ai_service
    assert service.credentials is None
    assert service.ledger.reserve_voice(identifier, service.media_binding(), 1)
    restarted = FastAPI()
    restarted.state.settings = Settings()
    install_ai(restarted)
    second = restarted.state.ai_service
    assert second.repository.read().revision == 1
    assert not second.ledger.reserve_voice(identifier, second.media_binding(), 1)
    assert not list(tmp_path.glob("*.dpapi"))
    assert "synthetic-environment-key" not in "".join(
        item.read_text() for item in tmp_path.glob("*.json")
    )


def test_relative_state_directory_rejected(monkeypatch):
    monkeypatch.setenv("CRM_AI_STATE_DIR", "relative-state")
    with pytest.raises(ValueError, match="absolute"):
        install_ai(FastAPI())


@pytest.mark.parametrize(
    "system,relative", [("nt", "Scripts/python.exe"), ("posix", "bin/python")]
)
def test_piper_uses_platform_runtime_without_downloading(
    monkeypatch, tmp_path, system, relative
):
    from app.modules.ai.infrastructure import media as ai_media

    monkeypatch.setattr(ai_media, "os", SimpleNamespace(name=system))
    gateway = MediaGateway({}, tmp_path)
    assert gateway.piper_runtime() == tmp_path / "piper" / ".venv" / relative
    assert gateway.piper_voices() == {
        "voices": [],
        "models": [],
        "ready": False,
        "local": True,
    }


@pytest.mark.parametrize(
    "host",
    [
        "sql;Encrypt=No",
        "sql\\instance",
        "sql,1433",
        "sql{host}",
        " sql",
        "sql\n",
        "-sql",
        "sql.",
        "https://sql",
        "[::1]",
    ],
)
def test_tcp_host_rejects_connection_string_injection(monkeypatch, host):
    monkeypatch.setenv("CRM_SQL_HOST", host)
    monkeypatch.setenv("CRM_SQL_USER", "reader")
    monkeypatch.setenv("CRM_SQL_PASSWORD", "synthetic")
    with pytest.raises(ValueError):
        Settings.from_environment()


@pytest.mark.parametrize(
    "port", ["0", "65536", "-1", "1433;Encrypt=No", "1.5", "１２３"]
)
def test_tcp_port_rejects_invalid_values(monkeypatch, port):
    monkeypatch.setenv("CRM_SQL_HOST", "sql.example.invalid")
    monkeypatch.setenv("CRM_SQL_PORT", port)
    monkeypatch.setenv("CRM_SQL_USER", "reader")
    monkeypatch.setenv("CRM_SQL_PASSWORD", "synthetic")
    with pytest.raises(ValueError):
        Settings.from_environment()


@pytest.mark.parametrize("user,password", [("", ""), ("reader", ""), ("", "synthetic")])
def test_tcp_requires_both_sql_credentials(monkeypatch, user, password):
    monkeypatch.setenv("CRM_SQL_HOST", "sql.example.invalid")
    monkeypatch.setenv("CRM_SQL_USER", user)
    monkeypatch.setenv("CRM_SQL_PASSWORD", password)
    with pytest.raises(ValueError):
        Settings.from_environment()


def test_tcp_port_alone_does_not_choose_a_server(monkeypatch):
    monkeypatch.setenv("CRM_SQL_PORT", "1433")
    with pytest.raises(ValueError, match="explicit host"):
        Settings.from_environment()


def test_tcp_transport_keeps_tls_fixed_database_and_escaped_credentials(monkeypatch):
    from app.modules.catalog.infrastructure import sql_reader as sql_periods

    monkeypatch.setenv("CRM_SQL_HOST", "sql.example.invalid")
    monkeypatch.setenv("CRM_SQL_PORT", "1444")
    monkeypatch.setenv("CRM_SQL_USER", "synthetic}reader")
    monkeypatch.setenv("CRM_SQL_PASSWORD", "synthetic};Encrypt=No")
    settings = Settings.from_environment()
    assert settings.mode == "local_demo"
    connection = Mock()
    connection.cursor.return_value.execute.return_value.fetchmany.return_value = []
    connection.cursor.return_value.execute.return_value.fetchone.return_value = (
        "DBSIIE",
        "SQLEXPRESS",
        "TESTMACHINE",
        r"TESTMACHINE\SQLEXPRESS",
        15,
        150,
        4,
        "Express Edition",
        "reader",
        "reader",
        "reader",
    )
    connect = Mock(return_value=connection)
    monkeypatch.setattr(sql_periods.pyodbc, "connect", connect)
    monkeypatch.setattr(sql_periods, "verify_principal", lambda cursor: None)
    assert SqlCatalogReader(settings).read_schools(25, 0) == []
    text = connect.call_args.args[0]
    assert "SERVER=tcp:sql.example.invalid,1444;DATABASE={DBSIIE};" in text
    assert "Encrypt=Yes;TrustServerCertificate=No;" in text
    assert "UID={synthetic}}reader};PWD={synthetic}};Encrypt=No};" in text
    assert connect.call_args.kwargs == {
        "timeout": 5,
        "autocommit": True,
        "readonly": True,
    }
    connection.close.assert_called_once()


def test_tcp_parameters_do_not_enable_catalog_or_connect(monkeypatch):
    from app.main import create_app

    monkeypatch.setenv("CRM_SQL_HOST", "sql.example.invalid")
    monkeypatch.setenv("CRM_SQL_USER", "reader")
    monkeypatch.setenv("CRM_SQL_PASSWORD", "synthetic")
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/api/v1/catalog/schools").status_code == 503
        assert client.get("/health/ready").status_code == 503
