import re
from pathlib import Path

import pytest

from app.institutional.postgres_dialect import postgres_sql
from app.institutional.postgres_rehearsal import ProfileError, load


MAP = {
    "crm_access.RateBucket": "dbo.CRMAccesoLimiteAcceso",
    "crm.Contact": "dbo.CRMContacto",
}


def test_rehearsal_rejects_other_database_or_combined_profiles():
    with pytest.raises(ProfileError, match="postgres_rehearsal_target_required"):
        load({"CRM_POSTGRES_URL": "postgresql://localhost/rinovaplus"})
    with pytest.raises(ProfileError, match="postgres_rehearsal_target_required"):
        load({
            "CRM_POSTGRES_URL": "postgresql://localhost/rinovaplus_rehearsal",
            "CRM_SQL_URL": "sqlserver://localhost:1433/dbsiie",
        })


@pytest.mark.parametrize("credentials", [
    {"CRM_POSTGRES_USER": "rinovaplus_app"},
    {"CRM_POSTGRES_PASSWORD": "example"},
    {"CRM_POSTGRES_USER": "rinovaplus_app", "CRM_POSTGRES_PASSWORD": ""},
])
def test_rehearsal_rejects_incomplete_separate_credentials(credentials):
    with pytest.raises(ProfileError, match="postgres_credentials_invalid"):
        load({"CRM_POSTGRES_URL": "postgresql://localhost/rinovaplus_rehearsal", **credentials})


def test_rehearsal_rejects_mixed_url_and_separate_credentials():
    with pytest.raises(ProfileError, match="postgres_credentials_invalid"):
        load({
            "CRM_POSTGRES_URL": "postgresql://legacy@localhost/rinovaplus_rehearsal",
            "CRM_POSTGRES_USER": "rinovaplus_app",
            "CRM_POSTGRES_PASSWORD": "example",
        })


def test_legacy_sql_keeps_parameters_separate_from_literals():
    query = "SELECT TOP(2) Name FROM crm.Contact WHERE Name<>N'crm.Contact?%' AND City=?"
    assert postgres_sql(query, MAP) == (
        "SELECT Name FROM rinovaplus_crm.crmcontacto"
        " WHERE Name<>'crm.Contact?%%' AND City=%s LIMIT 2"
    )


def test_rate_limit_cleanup_is_bounded_and_local():
    converted = postgres_sql(
        "DELETE TOP(100) FROM crm_access.RateBucket WHERE InstitutionId=? "
        "AND WindowAt<DATEADD(day,-1,SYSUTCDATETIME())",
        MAP,
    )
    assert converted.startswith("DELETE FROM rinovaplus_crm.crmaccesolimiteacceso")
    assert converted.endswith("(-1) * INTERVAL '1 day') LIMIT 100)")
    assert converted.count("%s") == 1


def test_postgres_worker_sql_keeps_outer_scope_and_query_binding():
    query = "UPDATE c SET c.Name=? FROM crm.Contact c JOIN crm_access.RateBucket r ON c.Id=r.SubjectId WHERE r.Name=?"
    assert postgres_sql(query, MAP) == (
        "UPDATE rinovaplus_crm.crmcontacto AS c SET Name=%s "
        "FROM rinovaplus_crm.crmaccesolimiteacceso AS r WHERE (c.Id=r.SubjectId) AND (r.Name=%s)"
    )


def test_postgres_worker_savepoints_are_bound_to_known_callsites():
    assert postgres_sql("ROLLBACK TRANSACTION p8_prepare_step", MAP) == "ROLLBACK TO SAVEPOINT p8_prepare_step"
    with pytest.raises(ValueError):
        postgres_sql("ROLLBACK TRANSACTION unknown", MAP)


@pytest.mark.parametrize("query", ["ALTER TABLE crm.Contact DROP COLUMN Name", "SELECT * FROM crm.Academic"])
def test_rehearsal_disallows_unported_sql(query):
    with pytest.raises(ValueError):
        postgres_sql(query, MAP)


def test_dba_script_is_a_single_own_batch_and_handles_repeat_execution():
    script = (Path(__file__).resolve().parents[2] / "docs/deployment/sql/readonly-crm-pending-36.sql")
    if not script.exists():
        pytest.skip("DBA documentation is outside the image")
    text = script.read_text(encoding="utf-8")
    assert len(re.findall(r"(?m)^GO$", text)) == 2
    assert "sp_executesql" not in text
    assert not re.search(r"(?im)^\s*USE\b", text)
    assert "@objects" not in text
    assert "qualified nvarchar(520) PRIMARY KEY" not in text
    assert "IF DB_NAME() <> N'DBSIIE_2025A'" in text
    assert "IF USER_ID(N'rinovaplus_pg_reader') IS NULL\n        CREATE USER" in text
