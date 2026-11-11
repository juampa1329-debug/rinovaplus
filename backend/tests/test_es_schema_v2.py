"""A manifest must have an external approval AND the exact allowed schema."""

import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import tools.es_schema_migrate_v2 as migrator


def manifest():
    return json.loads((migrator.PACKAGE / "release.json").read_text(encoding="utf-8"))


def test_reviewed_manifest_accepts():
    path = migrator.PACKAGE / "release.json"
    assert (
        migrator.release(hashlib.sha256(path.read_bytes()).hexdigest())["version"]
        == "cbn-spanish-baseline-v2"
    )


def test_external_approval_is_required_before_SQL():
    connection = Mock()
    with pytest.raises(ValueError, match="unapproved_manifest"):
        migrator.apply(
            connection, {}, Path("unused"), approved_manifest_sha256="0" * 64
        )
    connection.cursor.assert_not_called()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d["units"][0].__setitem__("file", "../source.sql"),
        lambda d: d["units"][0].__setitem__("file", "/etc/passwd"),
        lambda d: d["units"][0].__setitem__("file", "source_creation.sql"),
        lambda d: d["units"][0].__setitem__("sha256", "0" * 64),
        lambda d: d["units"][0].__setitem__("normalized_body_sha256", "0" * 64),
        lambda d: d["units"][0].__setitem__("source", "../other.sql"),
        lambda d: d["inputs"].pop("backend/tools/es_schema_catalog_v2.py"),
        lambda d: d["inputs"].__setitem__("../other.sql", "0" * 64),
        lambda d: d.__setitem__("version", "cbn-spanish-baseline-v1"),
        lambda d: d.__setitem__("engine_major", 17),
        lambda d: d.__setitem__("compatibility", 160),
        lambda d: d.__setitem__("runtime_redirect", True),
        lambda d: d.__setitem__("academic_DML", True),
        lambda d: d.__setitem__("automatic_startup_DDL", True),
        lambda d: d.__setitem__("package_tables", 99),
        lambda d: d.__setitem__("parent_C13_sha256", "0" * 64),
        lambda d: d["units"].append(copy.deepcopy(d["units"][0])),
        lambda d: d.__setitem__("extra", "unexpected"),
    ],
)
def test_even_approved_malformed_manifest_is_rejected(tmp_path, monkeypatch, mutation):
    original = migrator.PACKAGE
    data = manifest()
    source_root = migrator.ROOT
    for name in data["inputs"]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((source_root / name).read_bytes())
    mutation(data)
    raw = json.dumps(data).encode()
    (tmp_path / "release.json").write_bytes(raw)
    for name in ("ES_B000_journal.sql", "ES_B001_schema.sql"):
        (tmp_path / name).write_bytes((original / name).read_bytes())
    # Mirror the expected relative package path while using a private temporary root.
    relative = original.relative_to(migrator.ROOT)
    package = tmp_path / relative
    package.mkdir(parents=True, exist_ok=True)
    (package / "release.json").write_bytes(raw)
    for name in ("ES_B000_journal.sql", "ES_B001_schema.sql"):
        (package / name).write_bytes((original / name).read_bytes())
    monkeypatch.setattr(migrator, "ROOT", tmp_path)
    monkeypatch.setattr(migrator, "PACKAGE", package)
    with pytest.raises(ValueError):
        migrator.release(hashlib.sha256(raw).hexdigest())
