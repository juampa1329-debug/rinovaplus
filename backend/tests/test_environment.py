"""Exercise the real bootstrap with synthetic environment files and no external IO."""

import json
import os
from pathlib import Path

import pytest

from app import environment
from app.main import create_app


@pytest.fixture
def private_environment(monkeypatch, tmp_path):
    path = tmp_path / "checkout" / ".env"
    path.parent.mkdir()
    monkeypatch.setattr(environment, "ENV_FILE", path)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    for key in (
        "GEMINI_API_KEY",
        "CRM_SQL_PASSWORD",
        "CRM_SQL_USER",
        "CRM_SQL_HOST",
        "CRM_SQL_PORT",
        "CRM_APP_MODE",
        "CRM_CATALOG_TOKEN",
        "CRM_AI_OUTBOUND_ENABLED",
        "CRM_AI_STATE_DIR",
    ):
        monkeypatch.delenv(key, raising=False)
    return path


@pytest.mark.parametrize("working_directory", ["", "backend"])
def test_bootstrap_loads_one_root_file_from_either_cwd(
    private_environment, monkeypatch, working_directory, tmp_path, capsys, caplog
):
    private_environment.write_text(
        "CRM_APP_MODE=local_demo\nCRM_AI_OUTBOUND_ENABLED=false\n"
        "GEMINI_API_KEY='synthetic-$key # with spaces'\n"
        f"CRM_AI_STATE_DIR='{tmp_path.as_posix()}'\n",
        encoding="utf-8-sig",
    )
    directory = private_environment.parent / working_directory
    directory.mkdir(exist_ok=True)
    monkeypatch.chdir(directory)
    application = create_app()
    assert application.state.settings.mode == "local_demo"
    service = application.state.ai_service
    assert service.gateway.keys["gemini"] == "synthetic-$key # with spaces"
    assert service.outbound is False
    snapshot = service.connection_snapshot()
    assert snapshot["providers"][0]["configured"] is True
    assert snapshot["providers"][0]["credential_source"] == "environment"
    assert "synthetic-$key" not in json.dumps(snapshot)
    assert "synthetic-$key" not in repr(application.state.settings)
    captured = capsys.readouterr()
    assert "synthetic-$key" not in captured.out + captured.err + caplog.text


def test_missing_root_file_does_not_search_the_working_directory(
    private_environment, monkeypatch, tmp_path
):
    other = tmp_path / "unrelated"
    other.mkdir()
    (other / ".env").write_text("GEMINI_API_KEY=must-not-load\n", encoding="utf-8")
    monkeypatch.chdir(other)
    environment.load_environment()
    assert "GEMINI_API_KEY" not in os.environ


def test_existing_process_values_including_empty_take_precedence(
    private_environment, monkeypatch
):
    private_environment.write_text(
        "GEMINI_API_KEY=file-key\nCRM_SQL_PASSWORD=file-password\n", encoding="utf-8"
    )
    monkeypatch.setenv("GEMINI_API_KEY", "process-key")
    monkeypatch.setenv("CRM_SQL_PASSWORD", "")
    environment.load_environment()
    assert os.environ["GEMINI_API_KEY"] == "process-key"
    assert os.environ["CRM_SQL_PASSWORD"] == ""


@pytest.mark.parametrize(
    ("quoted", "expected"),
    [
        ("'literal$dollar'", "literal$dollar"),
        ("'${HOME}'", "${HOME}"),
        ("' spaced # value '", " spaced # value "),
        ("'double\"quote'", 'double"quote'),
        (r"'single\'quote'", "single'quote"),
    ],
)
def test_secret_characters_are_literal(private_environment, quoted, expected):
    private_environment.write_text(f"CRM_SQL_PASSWORD={quoted}\n", encoding="utf-8")
    environment.load_environment()
    assert os.environ["CRM_SQL_PASSWORD"] == expected


def test_invalid_encoding_has_a_sanitized_error(private_environment, capsys):
    private_environment.write_bytes(b"GEMINI_API_KEY=private-marker\xff")
    with pytest.raises(
        ValueError, match="^Local environment configuration could not be loaded$"
    ):
        environment.load_environment()
    assert "private-marker" not in capsys.readouterr().err


def test_template_is_safe_and_credentials_stay_server_owned(
    private_environment, tmp_path, monkeypatch
):
    root = Path(__file__).resolve().parents[2]
    template = (root / ".env.example").read_text(encoding="utf-8")
    private_environment.write_text(template, encoding="utf-8")
    monkeypatch.setenv("CRM_AI_STATE_DIR", str(tmp_path))
    application = create_app()
    assert application.state.settings.mode == "local_demo"
    assert not application.state.settings.sql_host
    assert application.state.ai_service.outbound is False
    assert not any(application.state.ai_service.gateway.keys.values())
    assert not any(line.startswith("VITE_") for line in template.splitlines())
    compose = (root / "compose.yaml").read_text(encoding="utf-8")
    assert "env_file:" not in compose
    assert "META_APP_SECRET:" not in compose
    assert "WHATSAPP_ACCESS_TOKEN:" not in compose
