import hashlib
import io
import json
import re
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.institutional import operations_policy
from tools.cutover_postgres_crm import METADATA, METADATA_FIELDS, SQL_SOURCE, capture, emit_candidate
from tools.stage_postgres_crm import ArchiveError, validate


def crm_model():
    keys = set(operations_policy.layout()["tables"].values())
    source = json.loads(
        (operations_policy.parent.PACKAGE / "expected-model.json").read_text(encoding="utf-8")
    )
    return {
        section: [
            row for row in values
            if row["schema"] + "." + row["name" if section == "tables" else "table"] in keys
        ]
        for section, values in source.items()
    }


class SourceFixture:
    def __init__(self, model):
        self.columns = {}
        for column in model["columns"]:
            self.columns.setdefault((column["schema"], column["table"]), []).append(column)
        self.rows = []
        self.read = []
        self.finished = False

    def cursor(self):
        return self

    def execute(self, statement, *params):
        if statement.startswith("SELECT DB_NAME()"):
            self.rows = [(SQL_SOURCE, 15, 150)]
        elif statement == METADATA:
            self.rows = [
                tuple(c[field] for field in METADATA_FIELDS)
                for c in sorted(self.columns[params], key=lambda col: col["ordinal"])
            ]
        elif statement.startswith("SELECT "):
            table = re.search(r" FROM \[(\w+)\]\.\[(\w+)\] ORDER BY ", statement).groups()
            assert table in self.columns
            self.read.append(table)
            self.rows = []
            if table == ("dbo", "CRMContacto"):
                assert "CONVERT(varchar(33),[CreatedAt],126)" in statement
                self.rows = [(
                    "b219190b-4352-4f47-8fb6-2f063041c1b1", "Contacto actualizado", "", "", None,
                    "", "", "Nuevo", "", "", "", "", "{}", "2026-11-15T03:00:00.1234567",
                    "2026-11-15T03:01:00.1111111",
                )]
        elif "ROLLBACK TRANSACTION" in statement:
            self.finished = True
        else:
            assert "SERIALIZABLE" in statement and "BEGIN TRANSACTION" in statement
        return self

    def fetchone(self):
        return self.rows[0]

    def __iter__(self):
        return iter(self.rows)


def fixture_archive():
    model = crm_model()
    conn = SourceFixture(model)
    result = io.BytesIO()
    with ZipFile(result, "w", ZIP_DEFLATED) as archive:
        capture(conn, model, archive)
    assert len(set(conn.read)) == 155 and conn.finished
    return result.getvalue()


def test_capture_and_emit_full_crm_candidate():
    contents = fixture_archive()
    digest = hashlib.sha256(contents).hexdigest()
    with ZipFile(io.BytesIO(contents)) as archive:
        manifest, schema = validate(archive)
        contact = manifest["tables"]["dbo.CRMContacto"]
        assert contact["rows"] == 1
        # Data stays in the private staging stream and the snapshot retains precision.
        assert b"03:00:00.1234567" in archive.read(contact["path"])
        out = io.StringIO()
        emit_candidate(archive, manifest, schema, digest, "rinovaplus_rehearsal", out)
        sql = out.getvalue()
        assert sql.count("\nCOMMIT;\n") == 1
        assert sql.index("Use the named empty CRM candidate database") < sql.index("CREATE SCHEMA")
        assert "CREATE FUNCTION rinovaplus_crm.next_outbound" in sql
        manifest["tables"]["dbo.CRMContacto"]["status"] = "restricted"
        untouched = io.StringIO()
        with pytest.raises(ArchiveError, match="complete_fresh_snapshot_required"):
            emit_candidate(archive, manifest, schema, digest, "rinovaplus_rehearsal", untouched)
        assert untouched.getvalue() == ""


def test_capture_aborts_on_schema_drift():
    model = crm_model()
    conn = SourceFixture(model)
    key = min(conn.columns)
    conn.columns[key] = []
    with ZipFile(io.BytesIO(), "w") as archive, pytest.raises(ArchiveError, match="source_columns_drift"):
        capture(conn, model, archive)
    assert conn.finished and not conn.read
