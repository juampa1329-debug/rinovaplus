"""Offline contract tests: every cursor and transport is synthetic."""

from dataclasses import replace
from unittest.mock import Mock

import pytest

from app.config import Settings
from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.modules.catalog.infrastructure.sql_reader import SqlCatalogReader
from app.sql_target import IDENTITY_SQL, connection_string, verify_identity


@pytest.fixture
def institutional():
    return Settings(
        sql_environment="institutional",
        sql_database="CBN SIIE",
        sql_host="sql.cbn.example.invalid",
        sql_port=1444,
        sql_certificate_hostname="sql.cbn.example.invalid",
        sql_user="synthetic}reader",
        sql_password="synthetic};Encrypt=No",
        sql_expected_machine="CBN-SQL",
        sql_expected_server="CBN-SQL",
        sql_expected_instance="DEFAULT",
        sql_expected_login="cbn_catalog",
        sql_expected_database_user="cbn_catalog_user",
    )


@pytest.fixture
def identity():
    return (
        "CBN SIIE",
        None,
        "CBN-SQL",
        "CBN-SQL",
        15,
        150,
        2,
        "Standard Edition (64-bit)",
        "cbn_catalog",
        "cbn_catalog",
        "cbn_catalog_user",
    )


def cursor_with(row):
    cursor = Mock()
    cursor.execute.return_value = cursor
    cursor.fetchone.return_value = row
    return cursor


def set_environment(monkeypatch, settings):
    for name in (
        "environment",
        "database",
        "host",
        "port",
        "certificate_hostname",
        "user",
        "password",
        "expected_machine",
        "expected_server",
        "expected_instance",
        "expected_login",
        "expected_database_user",
    ):
        monkeypatch.setenv(
            "CRM_SQL_" + name.upper(), str(getattr(settings, "sql_" + name))
        )


def test_institutional_environment_is_configuration_only(monkeypatch, institutional):
    set_environment(monkeypatch, institutional)
    actual = Settings.from_environment()
    assert actual == institutional
    assert actual.mode == "local_demo"
    assert "synthetic" not in repr(actual)
    text = connection_string(actual, catalog=True)
    assert "SERVER=tcp:sql.cbn.example.invalid,1444;DATABASE={CBN SIIE};" in text
    assert "Encrypt=Yes;TrustServerCertificate=No;" in text
    assert "HostnameInCertificate=sql.cbn.example.invalid;" in text
    assert "UID={synthetic}}reader};PWD={synthetic}};Encrypt=No};" in text


@pytest.mark.parametrize(
    "field",
    [
        "HOST",
        "PORT",
        "DATABASE",
        "CERTIFICATE_HOSTNAME",
        "USER",
        "PASSWORD",
        "EXPECTED_MACHINE",
        "EXPECTED_SERVER",
        "EXPECTED_INSTANCE",
        "EXPECTED_LOGIN",
        "EXPECTED_DATABASE_USER",
    ],
)
def test_environment_requires_every_institutional_expectation(
    monkeypatch, institutional, field
):
    set_environment(monkeypatch, institutional)
    monkeypatch.delenv("CRM_SQL_" + field)
    with pytest.raises(ValueError):
        Settings.from_environment()


@pytest.mark.parametrize(
    "field,value",
    [
        ("sql_environment", "production"),
        ("sql_host", "sql;TrustServerCertificate=Yes"),
        ("sql_certificate_hostname", "sql;Encrypt=No"),
        ("sql_certificate_hostname", "*.example.invalid"),
        ("sql_certificate_hostname", "-sql"),
        ("sql_port", 0),
        ("sql_port", 65536),
        ("sql_port", "1433"),
        ("sql_port", True),
        ("sql_database", "bad\nname"),
        ("sql_user", "bad\0user"),
        ("sql_password", "bad\rpassword"),
        ("sql_expected_instance", ""),
        ("sql_expected_machine", ""),
        ("sql_expected_server", ""),
        ("sql_expected_login", ""),
        ("sql_expected_database_user", ""),
        ("mode", "institutional"),
        ("mode", "local_sql_copy"),
    ],
)
def test_direct_settings_cannot_bypass_validation(institutional, field, value):
    with pytest.raises(ValueError):
        connection_string(replace(institutional, **{field: value}), catalog=True)


def test_database_odbc_metacharacters_are_braced(institutional):
    text = connection_string(
        replace(institutional, sql_database="CBN};Encrypt=No"), catalog=True
    )
    assert "DATABASE={CBN}};Encrypt=No};Encrypt=Yes;TrustServerCertificate=No;" in text


@pytest.mark.parametrize(
    "mode", ["local_demo", "local_readonly_catalog", "local_sql_copy"]
)
def test_institutional_workspace_cannot_open_transport(
    monkeypatch, institutional, mode
):
    from app.sql_workspace import SqlWorkspace

    connect = Mock(side_effect=AssertionError("Transport must not be reached"))
    monkeypatch.setattr("pyodbc.connect", connect)
    with pytest.raises(ValueError):
        with SqlWorkspace(replace(institutional, mode=mode)).transaction():
            pytest.fail("Institutional writes cannot be enabled in P1.2")
    connect.assert_not_called()


def test_default_and_named_instances_are_explicit(institutional, identity):
    cursor = cursor_with(identity)
    verify_identity(cursor, institutional)
    cursor.execute.assert_called_once_with(IDENTITY_SQL)
    named = replace(institutional, sql_expected_instance="CAMPUS")
    row = list(identity)
    row[1] = "CAMPUS"
    verify_identity(cursor_with(tuple(row)), named)
    with pytest.raises(ValueError):
        verify_identity(cursor_with(identity), named)
    with pytest.raises(ValueError):
        verify_identity(cursor_with(tuple(row)), institutional)


@pytest.mark.parametrize("index", [0, 2, 3, 4, 5, 6, 7, 8, 9, 10])
def test_null_identity_fails_closed(institutional, identity, index):
    row = list(identity)
    row[index] = None
    with pytest.raises(ValueError):
        verify_identity(cursor_with(tuple(row)), institutional)


@pytest.mark.parametrize(
    "index,value",
    [
        (0, "OTHER"),
        (1, "SQLEXPRESS"),
        (2, "OTHER"),
        (3, "OTHER"),
        (4, 14),
        (4, 16),
        (4, "15"),
        (5, 120),
        (5, 135),
        (5, 160),
        (5, "150"),
        (6, 5),
        (6, 8),
        (8, "sa"),
        (9, "impersonated"),
        (10, "dbo"),
    ],
)
def test_wrong_identity_or_engine_fails_closed(institutional, identity, index, value):
    row = list(identity)
    row[index] = value
    with pytest.raises(ValueError):
        verify_identity(cursor_with(tuple(row)), institutional)


@pytest.mark.parametrize("row", [None, (), ("DBSIIE",)])
def test_absent_or_truncated_metadata_fails_closed(institutional, row):
    with pytest.raises(ValueError):
        verify_identity(cursor_with(row), institutional)


def test_demo_settings_cannot_open_workspace(monkeypatch):
    from app.sql_workspace import SqlWorkspace

    connect = Mock(side_effect=AssertionError("Transport must not be reached"))
    monkeypatch.setattr("pyodbc.connect", connect)
    with pytest.raises(ValueError, match="explicit local-copy mode"):
        with SqlWorkspace(Settings()).transaction():
            pytest.fail("Demo must not fall back to a trusted workspace connection")
    connect.assert_not_called()


@pytest.mark.parametrize("level", [130, 140, 150])
def test_sql2019_compatible_levels(institutional, identity, level):
    row = list(identity)
    row[5] = level
    verify_identity(cursor_with(tuple(row)), institutional)


def test_catalog_identity_precedes_business_and_closes_on_rejection(
    monkeypatch, institutional, identity
):
    from app.modules.catalog.infrastructure import sql_reader

    cursor = cursor_with(identity)
    cursor.fetchmany.return_value = []
    connection = Mock()
    connection.cursor.return_value = cursor
    connect = Mock(return_value=connection)
    principal = Mock()
    monkeypatch.setattr(sql_reader.pyodbc, "connect", connect)
    monkeypatch.setattr(sql_reader, "verify_principal", principal)
    reader = SqlCatalogReader(institutional)
    assert reader.read_schools(25, 0) == []
    principal.assert_called_once_with(cursor)
    assert cursor.execute.call_args_list[0].args == (IDENTITY_SQL,)
    assert connect.call_args.kwargs == {
        "timeout": 5,
        "autocommit": True,
        "readonly": True,
    }
    cursor.reset_mock()
    connection.reset_mock()
    cursor.fetchone.return_value = None
    for _ in range(2):  # Capacity is released even after a rejected identity.
        with pytest.raises(CatalogUnavailable):
            reader.read_schools(25, 0)
    cursor.fetchmany.assert_not_called()
    assert all(call.args == (IDENTITY_SQL,) for call in cursor.execute.call_args_list)
    assert connection.close.call_count == cursor.close.call_count == 2


def test_local_workspace_retains_marker_and_shape_guards():
    from app.sql_workspace import verify_target

    settings = Settings(sql_expected_machine="LOCAL")
    identity = (
        "DBSIIE",
        "SQLEXPRESS",
        "LOCAL",
        r"LOCAL\SQLEXPRESS",
        15,
        150,
        4,
        "Express Edition",
        "local",
        "local",
        "local",
    )
    for marker, shape in [(("wrong",), (1,)), (("ADR-006-v1",), (0,)), (None, (1,))]:
        cursor = cursor_with(None)
        cursor.fetchone.side_effect = [identity, marker, shape]
        with pytest.raises(CatalogUnavailable):
            verify_target(cursor, settings)


def test_institutional_configuration_does_not_enable_app_io(
    monkeypatch, tmp_path, institutional
):
    from fastapi.testclient import TestClient

    from app.main import create_app

    set_environment(monkeypatch, institutional)
    monkeypatch.setenv("CRM_AI_STATE_DIR", str(tmp_path))
    with TestClient(create_app()) as client:
        assert client.get("/api/v1/catalog/schools").status_code == 503
        assert client.get("/health/ready").status_code == 503
