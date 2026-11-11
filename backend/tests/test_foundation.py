"""Offline negative checks for the explicit foundation package; no SQL or app IO."""

import copy
import json
from unittest.mock import Mock

import pytest

from tools import cbn_foundation as f
from tools.foundation_snapshot import sha


@pytest.fixture
def package(tmp_path):
    shapes = {name: {"prefix": i} for i, name in enumerate(["prepared", *f.UNITS])}
    (tmp_path / "expected-shapes.json").write_text(json.dumps(shapes), encoding="utf-8")
    manifest = {
        "release_id": "synthetic",
        "scope": "restored_rehearsal_only",
        "shape_version": f.SHAPE_VERSION,
        "engine_major": 16,
        "institutional_sql2019_accepted": False,
        "tool_files": [
            {"path": p, "sha256": f.file_sha(f.ROOT / p)} for p in f.TOOL_FILES
        ],
        "legacy_sources": [
            {"path": p, "sha256": f.file_sha(f.ROOT / p)} for p in f.LEGACY_FILES
        ],
        "expected_shapes_sha256": f.file_sha(tmp_path / "expected-shapes.json"),
        "units": [],
    }
    for i, (unit, filename) in enumerate(zip(f.UNITS, f.SQL_FILES, strict=True)):
        (tmp_path / filename).write_bytes((f.PACKAGE / filename).read_bytes())
        before = "prepared" if not i else f.UNITS[i - 1]
        manifest["units"].append(
            {
                "id": unit,
                "file": filename,
                "sha256": f.file_sha(tmp_path / filename),
                "depends_on": list(f.UNITS[:i]),
                "before_sha256": sha(shapes[before]),
                "after_sha256": sha(shapes[unit]),
            }
        )
    (tmp_path / "release.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path, manifest


def test_package_loads_without_opening_database(package):
    directory, manifest = package
    assert f.load_release(directory)[0] == manifest


@pytest.mark.parametrize(
    "mutation",
    ["sql", "expected", "shape_version", "dependencies", "tool", "legacy", "scope"],
)
def test_package_mutation_blocks(package, mutation):
    directory, manifest = package
    if mutation == "sql":
        (directory / f.SQL_FILES[0]).write_text("SELECT 1;", encoding="utf-8")
    elif mutation == "expected":
        (directory / "expected-shapes.json").write_text("{}", encoding="utf-8")
    else:
        if mutation == "shape_version":
            manifest["shape_version"] = "unknown"
        if mutation == "dependencies":
            manifest["units"][2]["depends_on"] = []
        if mutation == "tool":
            manifest["tool_files"][0]["sha256"] = "0" * 64
        if mutation == "legacy":
            manifest["legacy_sources"] = []
        if mutation == "scope":
            manifest["scope"] = "institutional"
        (directory / "release.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(f.Blocked):
        f.load_release(directory)


@pytest.mark.parametrize(
    "name",
    ["HORARIOSSIIE", "master", "msdb", "DBSIIE", "CBN_C3_TRIAL_20261024_xxxxxxxx"],
)
def test_wrong_target_rejected_before_any_sql(name):
    cursor = Mock()
    with pytest.raises(f.Blocked, match="restored_name_required"):
        f.guard(cursor, {"identity": {"database": name}})
    cursor.execute.assert_not_called()


def test_audit_blocks_unknown_and_unfinished_attempts(tmp_path):
    audit = f.Audit(tmp_path / "audit.jsonl", "synthetic-target")
    audit.add("a", "CBN-B000", "STARTED")
    assert len(audit.unresolved()) == 1
    audit.add("a", "CBN-B000", "UNKNOWN")
    assert len(audit.unresolved()) == 1
    audit.add("a", "CBN-B000", "RECONCILED_COMMITTED")
    assert not audit.unresolved()
    with pytest.raises(f.Blocked, match="audit_target_mismatch"):
        f.Audit(audit.path, "different-target").rows()


def history_fixture():
    ticket = {
        "identity": {"database": "synthetic-restored"},
        "evidence_ref": "synthetic-evidence",
        "approval_ref": "synthetic-approval",
        "backup_ref": "synthetic-backup",
    }
    units = [
        {
            "id": u,
            "sha256": str(i + 1) * 64,
            "before_sha256": str(i + 4) * 64,
            "after_sha256": str(i + 5) * 64,
        }
        for i, u in enumerate(f.UNITS)
    ]
    manifest = {"units": units, "release_id": "synthetic"}
    row = {
        "attempt": "synthetic-a",
        "unit": units[0]["id"],
        "kind": "COMMITTED",
        "manifest_hash": "a" * 64,
        "unit_hash": units[0]["sha256"],
        "target_hash": sha(ticket["identity"]),
        "before_hash": units[0]["before_sha256"],
        "after_hash": units[0]["after_sha256"],
        "shape_version": f.SHAPE_VERSION,
        "principal": f.PRINCIPAL,
        "release_id": "synthetic",
        "tool_version": f.TOOL_VERSION,
        "success_key": units[0]["id"],
        "error_code": None,
        "related_attempt": None,
        "related_unit": None,
        "evidence_ref": ticket["evidence_ref"],
        "approval_ref": ticket["approval_ref"],
        "backup_ref": ticket["backup_ref"],
    }
    return ticket, manifest, row


@pytest.mark.parametrize(
    "field",
    [
        "manifest_hash",
        "unit_hash",
        "target_hash",
        "before_hash",
        "after_hash",
        "shape_version",
        "principal",
        "release_id",
        "tool_version",
        "success_key",
    ],
)
def test_history_tampering_blocks(monkeypatch, field):
    ticket, manifest, row = history_fixture()
    row[field] = "changed"
    monkeypatch.setattr(f, "records", lambda *_: [row])
    with pytest.raises(f.Blocked):
        f.current_history(Mock(), ticket, manifest, "a" * 64)


def test_duplicate_terminal_and_out_of_order_success_block(monkeypatch):
    ticket, manifest, row = history_fixture()
    monkeypatch.setattr(f, "records", lambda *_: [row, copy.deepcopy(row)])
    with pytest.raises(f.Blocked, match="invalid_attempt_event_sequence"):
        f.current_history(Mock(), ticket, manifest, "a" * 64)
    with pytest.raises(f.Blocked, match="invalid_history_vector"):
        f.successful_prefix([{"unit": "CBN-B001", "kind": "COMMITTED", "attempt": "a"}])


def test_unfinished_sql_attempt_needs_reconciliation():
    with pytest.raises(f.Blocked, match="incomplete_attempt"):
        f.successful_prefix([{"unit": "CBN-B001", "kind": "STARTED", "attempt": "a"}])


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [(1, "{}", 0)],
        [(1, "[]", 1)],
        [(1, "invalid", 1)],
        [(1, '{"stages":[]}', 1)],
    ],
)
def test_missing_or_invalid_configuration_blocks_noop(rows):
    cursor = Mock()
    cursor.execute.return_value.fetchmany.return_value = rows
    with pytest.raises(f.Blocked):
        f.validate_data(cursor, "CBN-B006")


def test_edited_valid_configuration_is_preserved():
    cursor = Mock()
    edited = {
        "stages": [{"key": "review", "label": "Review", "active": True}],
        "tags": [],
        "inactiveTags": [],
        "fields": [],
    }
    cursor.execute.return_value.fetchmany.return_value = [(1, json.dumps(edited), 3)]
    f.validate_data(cursor, "CBN-B006")
    assert cursor.execute.call_count == 1
    assert cursor.execute.call_args.args[0].lstrip().startswith("SELECT")


def test_private_binary_digest_encoding_is_unambiguous():
    from tools.foundation_snapshot import encode

    assert sha([None]) != sha([b""])
    assert encode([b"\x00\xff"]) == b'[{"binary":"00ff"}]'


def test_reconcile_committed_sql_uppercase_uuid_matches_lowercase_external_audit(
    monkeypatch, tmp_path
):
    attempt = "abcdefab-cdef-abcd-efab-cdefabcdefab"
    unit = {"id": "CBN-B001", "before_sha256": "1" * 64, "after_sha256": "2" * 64}
    manifest = {"units": [unit], "release_id": "synthetic"}
    shape = {"reference": "already_committed"}
    audit = f.Audit(tmp_path / "ack.jsonl", "target")
    audit.add(attempt, unit["id"], "UNKNOWN")
    history = [
        {
            "unit": "CBN-B000",
            "kind": "COMMITTED",
            "attempt": "00000000-0000-0000-0000-000000000001",
        },
        {"unit": unit["id"], "kind": "COMMITTED", "attempt": attempt.upper()},
    ]
    monkeypatch.setattr(
        f, "load_release", lambda _: (manifest, {unit["id"]: shape}, "0" * 64)
    )
    monkeypatch.setattr(f, "guard", lambda *_: None)
    monkeypatch.setattr(f, "acquire", lambda *_: None)
    monkeypatch.setattr(f, "current_history", lambda *_: history)
    monkeypatch.setattr(f, "metadata", lambda *_, **__: shape)
    event = Mock()
    monkeypatch.setattr(f, "append_event", event)
    connection = Mock()
    connection.cursor.return_value.execute.return_value.fetchval.return_value = 0
    connection.cursor.return_value.nextset.return_value = False
    f.reconcile(connection, {}, audit, directory=tmp_path)
    assert event.call_args.args[5] == "RECONCILED_COMMITTED"
    assert event.call_args.args[7] == sha(shape)
    assert f.uuid.UUID(event.call_args.kwargs["related"]) == f.uuid.UUID(attempt)
    assert all(
        not any(word in call.args[0].upper() for word in ("CREATE ", "ALTER ", "DROP "))
        for call in connection.cursor.return_value.execute.call_args_list
    )
    assert not audit.unresolved()
