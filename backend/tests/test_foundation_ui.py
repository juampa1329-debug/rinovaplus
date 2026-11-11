"""UI composition/profile boundaries, with synthetic secrets and no real SQL."""

import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_foundation_runtime import profile as _profile_fixture

from app.config import Settings
from app.foundation_app import create_foundation_app
from app.foundation_profile import load_settings
from app.main import create_app
from app.sql_profile import ProfileUnavailable, SqlProfileStore

profile = _profile_fixture


@pytest.fixture
def encrypted_profile(profile, tmp_path):
    directory = tmp_path / "prepared"
    directory.mkdir()
    shutil.copyfile(profile.foundation_ticket_path, directory / "runtime-ticket.json")
    store = SqlProfileStore(directory / "runtime")
    store.save(
        {
            "revision": 1,
            "connection": {
                "server": profile.sql_host,
                "port": profile.sql_port,
                "username": profile.sql_user,
                "password": profile.sql_password,
                "database": profile.sql_database,
                "certificate_hostname": profile.sql_certificate_hostname,
            },
            "review": {
                "machine": profile.sql_expected_machine,
                "server": profile.sql_expected_server,
                "ticket_sha256": profile.foundation_ticket_sha256,
            },
        }
    )
    return directory


def test_encrypted_profile_uses_only_the_prepared_target(
    profile, encrypted_profile, monkeypatch
):
    monkeypatch.setenv("CRM_APP_MODE", "local_foundation")
    monkeypatch.setenv("CRM_FOUNDATION_PROFILE_DIR", str(encrypted_profile))
    monkeypatch.setenv("CRM_SQL_USER", "sa")
    monkeypatch.setenv("CRM_SQL_PASSWORD", "must-not-be-used")
    monkeypatch.setenv("CRM_SQL_DATABASE", "HORARIOSSIIE")
    loaded = Settings.from_environment()
    assert loaded == replace(
        profile, foundation_ticket_path=str(encrypted_profile / "runtime-ticket.json")
    )
    assert profile.sql_password not in repr(loaded)


@pytest.mark.parametrize(
    "name", ["runtime/profile.key", "runtime/profile.enc", "runtime-ticket.json"]
)
def test_corrupt_profile_never_falls_back(encrypted_profile, name):
    (encrypted_profile / name).write_bytes(b"corrupt")
    with pytest.raises((ProfileUnavailable, ValueError)):
        load_settings(encrypted_profile)


@pytest.mark.parametrize(
    "mode", ["local_demo", "local_sql_copy", "local_readonly_catalog", "production"]
)
def test_profile_requires_explicit_foundation_mode(
    encrypted_profile, mode, monkeypatch
):
    monkeypatch.setenv("CRM_FOUNDATION_PROFILE_DIR", str(encrypted_profile))
    monkeypatch.setenv("CRM_APP_MODE", mode)
    with pytest.raises(ValueError):
        Settings.from_environment()


def test_relative_or_absent_profile_is_rejected(tmp_path):
    for path in (Path("relative"), tmp_path / "missing"):
        with pytest.raises(ValueError):
            load_settings(path)


def test_foundation_manifest_is_guarded_public_and_performs_no_sql(profile):
    application = create_foundation_app(profile)
    with TestClient(
        application, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 9000)
    ) as client:
        assert client.get("/api/local/runtime").status_code == 403
        response = client.get("/api/local/runtime", headers={"X-CRM-Local": "1"})
        assert (
            response.status_code == 200
            and response.headers["cache-control"] == "no-store"
        )
        value = response.json()
        assert value["profile"] == "foundation"
        assert value["modules"] == ["overview", "clients", "inbox", "settings"]
        assert all(flag is False for flag in value["features"].values())
        assert value["scope"] == "restored_rehearsal_only"
        assert not any(
            secret in response.text
            for secret in (profile.sql_password, profile.sql_host, profile.sql_database)
        )


def test_legacy_composition_retains_its_explicit_manifest():
    application = create_app(settings=Settings())
    with TestClient(application) as client:
        value = client.get("/api/local/runtime").json()
        assert value["mode"] == "local_demo" and value["profile"] == "legacy"
        assert value["modules"] is None
