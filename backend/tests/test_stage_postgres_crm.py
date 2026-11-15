import hashlib
import json
from io import BytesIO, StringIO
from zipfile import ZipFile

import pytest

from tools.stage_postgres_crm import ArchiveError, FORMAT, validate, write_staging_sql


def snapshot_archive(*, wrong_digest=False, wrong_width=False):
    value = json.dumps(['línea 1\nlínea "2" \\', {"hex": "00ff"}]).encode() + b"\n"
    manifest = {
        "format": FORMAT,
        "tables": {
            "dbo.CRMContacto": {
                "status": "exported", "path": "data/000.jsonl", "rows": 1,
                "sha256": "invalid" if wrong_digest else hashlib.sha256(value).hexdigest(),
            },
            "dbo.CRMOmitida": {"status": "restricted", "catalog_rows_estimate": 0},
        },
    }
    schema = {
        "tables": [{"schema": "dbo", "name": name} for name in ("CRMContacto", "CRMOmitida")],
        "columns": [
            {"schema": "dbo", "table": "CRMOmitida", "name": "ID"},
            {"schema": "dbo", "table": "CRMContacto", "name": "Text"},
        ],
    }
    if not wrong_width:
        schema["columns"].append({"schema": "dbo", "table": "CRMContacto", "name": "Binary"})
    result = BytesIO()
    with ZipFile(result, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("schema.json", json.dumps(schema))
        archive.writestr("data/000.jsonl", value)
    return ZipFile(result)


def test_staging_emits_guarded_transaction_and_preserves_restricted_status():
    with snapshot_archive() as archive:
        manifest, schema = validate(archive)
        sql = StringIO()
        write_staging_sql(archive, manifest, schema, "a" * 64, sql)
    script = sql.getvalue()
    assert script.startswith("BEGIN;\n")
    assert "current_database() NOT IN ('rinovaplus', 'rinovaplus_rehearsal')" in script
    assert '"dbo.CRMContacto","1",' in script
    assert '"dbo.CRMOmitida","1",' not in script
    assert '""status"": ""restricted""' in script
    assert script.endswith("\\.\nCOMMIT;\n")


@pytest.mark.parametrize(("override", "error"), [
    ({"wrong_digest": True}, "data_checksum_mismatch"),
    ({"wrong_width": True}, "wrong_row_width"),
])
def test_staging_rejects_incomplete_or_corrupt_records(override, error):
    with snapshot_archive(**override) as archive, pytest.raises(ArchiveError, match=error):
        validate(archive)
