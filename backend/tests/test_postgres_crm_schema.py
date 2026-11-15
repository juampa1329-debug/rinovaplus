import json
import re
from pathlib import Path

import pytest

from tools.postgres_crm_schema import TABLE, build, compile_expression, row_value


BACKEND = Path(__file__).resolve().parents[1]


def crm_model():
    source = json.loads(
        (BACKEND / "migrations/cbn_learning_operations_v1/expected-model.json")
        .read_text(encoding="utf-8")
    )
    return {
        section: [
            row for row in rows
            if TABLE.fullmatch(row["schema"] + "." + row["name" if section == "tables" else "table"])
        ]
        for section, rows in source.items()
    }


def test_all_crm_bindings_translate_without_academic_ddl():
    source = crm_model()
    sql = build(source, "a" * 64)
    assert len(source["tables"]) == 155
    assert len(source["columns"]) == 1564
    assert sql.count("CREATE TABLE rinovaplus_crm.") == 155
    assert sql.count(" PRIMARY KEY ") == 155
    assert sql.count(" FOREIGN KEY ") == 298
    assert sql.count("CREATE TRIGGER bump_row_version") == 29
    assert "NULLS NOT DISTINCT" in sql
    assert "CREATE TABLE rinovaplus_crm.\"acaspirante\"" not in sql
    assert sql.endswith("COMMIT;\n")


@pytest.mark.parametrize("predicate", [
    "([Name]>0); DROP TABLE x",
    "dbo.secret([Name])=1",
    "([AcademicColumn]>0)",
])
def test_unknown_source_expressions_stop_conversion(predicate):
    with pytest.raises(ValueError):
        compile_expression(predicate, {"Name"})


def test_binary_and_bit_import_preserve_null_and_bits():
    assert row_value({"ordinal": 5, "type_name": "timestamp"}) == (
        "decode(source_values -> 4 ->> 'hex', 'hex')"
    )
    assert "WHEN 'true' THEN '1' WHEN 'false' THEN '0'" in row_value(
        {"ordinal": 6, "type_name": "bit"}
    )


def test_dba_script_lists_exactly_36_reviewed_crm_objects():
    script = (BACKEND.parent / "docs/deployment/sql/readonly-crm-pending-36.sql").read_text()
    grants = re.findall(r"GRANT SELECT ON OBJECT::\[dbo\]\.\[(CRM\w+)\]", script)
    scope = re.findall(r"\(N'(CRM\w+)'\)", script)
    assert len(grants) == len(set(grants)) == 36
    assert set(grants) == set(scope)
    assert set("dbo." + name for name in grants).issubset(
        {row["schema"] + "." + row["name"] for row in crm_model()["tables"]}
    )
    assert "GRANT SELECT ON SCHEMA" not in script
    assert "EXECUTE AS USER" in script
