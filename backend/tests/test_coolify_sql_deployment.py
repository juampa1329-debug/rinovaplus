from types import SimpleNamespace
from unittest.mock import Mock

import pyodbc
import pytest

from app.institutional import deployment, operations_policy
from app.institutional.db import bound_hash
from tools.coolify_sql_grants import render, render_inventory


def environment(**overrides):
    return {
        "CRM_SQL_URL": "sqlserver://192.0.2.42:1433/dbsiie",
        "CRM_SQL_USER": "fake_runtime",
        "CRM_SQL_PASSWORD": "example;with}braces",
        **overrides,
    }


def test_deployment_transport_uses_tls_and_quotes_credentials():
    transport = deployment.transport_from_env(environment())
    assert transport.database == "dbsiie"
    assert "DRIVER={ODBC Driver 18 for SQL Server}" in transport.odbc_string()
    assert "Encrypt=Yes;TrustServerCertificate=Yes;" in transport.odbc_string()
    assert "PWD={example;with}}braces};" in transport.odbc_string()
    assert "fake_runtime" not in repr(transport)
    assert "example;with" not in repr(transport)


def test_previous_certificate_hostname_does_not_block_deployment():
    transport = deployment.transport_from_env(environment(CRM_SQL_CERTIFICATE_HOSTNAME=""))
    assert "TrustServerCertificate=Yes;" in transport.odbc_string()
    assert "HostnameInCertificate" not in transport.odbc_string()


def test_unset_keeps_signed_profile_and_partial_configuration_fails():
    assert deployment.transport_from_env({}) is None
    with pytest.raises(deployment.DeploymentError, match="sql_environment_incomplete"):
        deployment.transport_from_env(environment(CRM_SQL_PASSWORD=""))


@pytest.mark.parametrize("url", [
    "sqlserver://name:password@example.org:1433/dbsiie",
    "sqlserver://example.org:1433/dbsiie?TrustServerCertificate=Yes",
    "sqlserver://example.org:1433/master",
    "sqlserver://example.org:65536/dbsiie",
])
def test_url_rejects_extra_credentials_options_and_unknown_databases(url):
    with pytest.raises(deployment.DeploymentError) as error:
        deployment.transport_from_env(environment(CRM_SQL_URL=url))
    assert url not in str(error.value)


@pytest.mark.parametrize(
    "url",
    [
        "sqlserver://192.0.2.42:1433",
        "sqlserver://192.0.2.42:1433/",
        "sqlserver://192.0.2.42:1433/dbsiie",
    ],
)
@pytest.mark.parametrize("name", ["DBSIIE_Copia", "DBSIIE - Réplica"])
def test_explicit_database_selects_the_copy(url, name):
    transport = deployment.transport_from_env(
        environment(CRM_SQL_URL=url, CRM_SQL_DATABASE=name)
    )
    assert transport.database == name
    assert f"DATABASE={{{name}}};" in transport.odbc_string()


@pytest.mark.parametrize(
    "name", ["", " copia", "copia;UID=sa", "MaStEr", "model", "msdb", "tempdb"]
)
def test_explicit_database_rejects_invalid_names_and_system_databases(name):
    with pytest.raises(deployment.DeploymentError, match="sql_database_invalid"):
        deployment.transport_from_env(environment(CRM_SQL_DATABASE=name))


def test_url_without_database_requires_the_database_variable():
    with pytest.raises(deployment.DeploymentError, match="sql_database_missing"):
        deployment.transport_from_env(
            environment(CRM_SQL_URL="sqlserver://192.0.2.42:1433")
        )


def test_database_variable_alone_is_an_incomplete_configuration():
    with pytest.raises(deployment.DeploymentError, match="sql_environment_incomplete"):
        deployment.transport_from_env({"CRM_SQL_DATABASE": "DBSIIE_Copia"})


def test_driver_errors_are_redacted(monkeypatch):
    def reject(*_args, **_kwargs):
        raise pyodbc.Error("08001", "SSL Provider: certificate failure fake_runtime example;with}braces")

    monkeypatch.setattr(pyodbc, "connect", reject)
    with pytest.raises(deployment.DeploymentError, match="sql_tls_negotiation_failed") as error:
        deployment.open_connection(deployment.transport_from_env(environment()))
    assert "fake_runtime" not in str(error.value)
    assert "example;with" not in str(error.value)


def test_deployment_normalizes_only_equivalent_fill_factors():
    from tools.p9_catalog_snapshot import compare

    base = dict.fromkeys(
        ("tables", "columns", "checks", "foreign_keys", "table_options", "ansi_padding"), []
    )
    expected = {**base, "indexes": [{"name": "crm_index", "fill_factor": 0}]}
    equivalent = {**base, "indexes": [{"name": "crm_index", "fill_factor": 100}]}
    different = {**base, "indexes": [{"name": "crm_index", "fill_factor": 80}]}
    normalize = operations_policy._deployment_index_model

    assert compare(normalize(equivalent), normalize(expected))["passed"]
    rejected = compare(normalize(different), normalize(expected))
    assert rejected["differing_sections"] == ["indexes"]
    assert equivalent["indexes"][0]["fill_factor"] == 100


def test_missing_tables_are_listed_by_fixed_catalog_name():
    cursor = Mock()
    cursor.execute.return_value.fetchval.return_value = 1
    cursor.execute.return_value.fetchall.return_value = []
    with pytest.raises(deployment.DeploymentError, match="sql_tables_missing") as error:
        operations_policy.deployment_catalog(cursor, inventory_only=True)
    assert "dbo.CRMContacto" in str(error.value)
    assert "dbo.ACAspirante" in str(error.value)


def test_deployment_session_hash_binds_to_validated_database():
    settings = SimpleNamespace(
        deployment_transport=deployment.transport_from_env(environment()),
        ticket={
            "context": [[1, "a6ec3dd5-8e9f-4fee-8000-4d99236bf409", "CBN-channels-parity-v1"]],
            "identity": {"database": "DBSIIE"},
        },
        review={"session_token": "synthetic-session-secret"},
    )
    before = bound_hash(settings, "sample", "session")
    settings.ticket["identity"]["database"] = "RinovaPlus_Trial_1234abcd"
    assert before != bound_hash(settings, "sample", "session")


def test_grant_script_checks_database_and_defaults_to_rollback():
    script = render("dbsiie", "crm_rinova")
    assert "IF DB_NAME() <> N'dbsiie'" in script
    assert "ON OBJECT::dbo.CRMContacto" in script
    assert "ON OBJECT::dbo.ACAspirante" not in script
    assert script.endswith("ROLLBACK TRANSACTION;")


def test_inventory_script_labels_missing_crm_and_siie_tables_without_writes():
    script = render_inventory("dbsiie")
    assert "IF DB_NAME() <> N'dbsiie'" in script
    assert "(N'CRM', N'dbo', N'CRMContacto')" in script
    assert "(N'SIIE', N'dbo', N'ACAspirante')" in script
    assert "THEN 'MISSING' ELSE 'PRESENT'" in script
    assert all(word not in script for word in ("CREATE ", "ALTER ", "GRANT ", "INSERT ", "DELETE "))
