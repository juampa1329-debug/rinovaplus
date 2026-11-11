"""Protocol negatives: caller ownership, bound attempt order and native media."""

from unittest.mock import Mock
from uuid import uuid4

import pytest
import tools.es_schema_migrate_v2 as m
import tools.es_schema_recovery_v2 as recovery
from tools.foundation_snapshot import sha


def start(unit="ES-B001", attempt=None):
    return {
        "event": "STARTED",
        "unit": unit,
        "attempt": attempt or str(uuid4()),
        "version": m.VERSION,
        "target": "1" * 64,
        "manifest": "2" * 64,
        "unit_sha256": "3" * 64,
        "before": "4" * 64,
    }


def test_owned_transaction_rejected_without_rollback():
    connection = Mock()
    connection.autocommit = True
    cursor = connection.cursor.return_value
    cursor.execute.return_value = cursor
    cursor.fetchval.return_value = 1
    with pytest.raises(ValueError, match="caller_transaction_not_owned"):
        m.enter(connection, {})
    cursor.execute.assert_called_once_with("SELECT @@TRANCOUNT")
    connection.close.assert_not_called()


def test_failed_cleanup_discards_connection():
    connection = Mock()
    cursor = Mock()
    cursor.execute.return_value = cursor
    cursor.fetchval.return_value = 0

    def execute(query, *args):
        if query == "REVERT":
            raise RuntimeError("broken session")
        return cursor

    cursor.execute.side_effect = execute
    with pytest.raises(ValueError, match="cleanup_connection_discarded"):
        m.leave(cursor, connection)
    connection.close.assert_called_once()
    cursor.close.assert_called_once()


def test_terminal_before_start_rejected():
    value = {**start(), "event": "COMMITTED", "after": "5" * 64}
    with pytest.raises(ValueError, match="terminal_order"):
        m.wal_state([value])


@pytest.mark.parametrize(
    "field,value",
    [
        ("unit", "ES-B000"),
        ("target", "f" * 64),
        ("manifest", "e" * 64),
        ("before", "c" * 64),
    ],
)
def test_crossed_terminal_rejected(field, value):
    first = start()
    last = {**first, "event": "COMMITTED", "after": "5" * 64, field: value}
    with pytest.raises(ValueError):
        m.wal_state([first, last])


def test_uncertain_attempt_cannot_be_reported_committed_twice():
    first = start()
    last = {**first, "event": "COMMITTED", "after": "5" * 64}
    with pytest.raises(ValueError, match="terminal_order"):
        m.wal_state([first, last, last])


def test_wal_cross_target_file_reuse_rejected():
    first = start()
    last = {**first, "event": "RECONCILED_NOT_APPLIED"}
    other = {**start(), "target": "a" * 64}
    with pytest.raises(ValueError, match="file_binding"):
        m.wal_state([first, last, other])


def sql_fixture(monkeypatch, *, old_not_applied=True):
    actual = {"database": "qualified"}
    manifest = "2" * 64
    package = {
        "units": [
            {"id": "ES-B000", "sha256": "3" * 64},
            {"id": "ES-B001", "sha256": "3" * 64},
        ]
    }
    boot, a, b = str(uuid4()), str(uuid4()), str(uuid4())

    def row(event_id, attempt, unit, kind, before, after=None):
        return {
            "EventId": event_id,
            "AttemptId": attempt,
            "UnitId": unit,
            "EventKind": kind,
            "ReleaseId": m.VERSION,
            "ToolVersion": "P1-ES-explicit-v2",
            "ShapeVersion": "p1-es-full-catalog-v2",
            "PrincipalRef": m.ACTOR,
            "EvidenceRef": "P1-ES-SQL2019",
            "ApprovalRef": "owner-20261026",
            "BackupRef": "native-restored-before-first-apply",
            "ErrorCode": None,
            "ManifestSha256": bytes.fromhex(manifest),
            "UnitSha256": bytes.fromhex("3" * 64),
            "TargetSha256": bytes.fromhex(sha(actual)),
            "BeforeShapeSha256": bytes.fromhex(before),
            "AfterShapeSha256": bytes.fromhex(after) if after else None,
            "SuccessKey": unit if kind == "COMMITTED" else None,
        }

    events = [
        row(1, boot, "ES-B000", "COMMITTED", "0" * 64, "4" * 64),
        row(2, a, "ES-B001", "STARTED", "4" * 64),
    ]
    if old_not_applied:
        events.append(row(3, a, "ES-B001", "RECONCILED_NOT_APPLIED", "4" * 64))
    events.extend(
        [
            row(4, b, "ES-B001", "STARTED", "4" * 64),
            row(5, b, "ES-B001", "COMMITTED", "4" * 64, "5" * 64),
        ]
    )
    monkeypatch.setattr(m, "records", lambda *args: events)
    monkeypatch.setattr(m, "journal_exists", lambda c: True)
    history = m.sql_history(Mock(), package, manifest, actual)
    last = events[-1]
    success = (
        last["ManifestSha256"],
        last["UnitSha256"],
        last["TargetSha256"],
        last["AfterShapeSha256"],
        b,
        5,
        "COMMITTED",
        m.VERSION,
        "P1-ES-explicit-v2",
        "p1-es-full-catalog-v2",
        last["BeforeShapeSha256"],
        "ES-B001",
    )
    return actual, manifest, package, a, history, success


def test_lost_not_applied_ack_does_not_borrow_later_attempt_commit(
    tmp_path, monkeypatch
):
    actual, manifest, package, a, history, success = sql_fixture(monkeypatch)
    first = {**start(attempt=a), "target": sha(actual)}
    wal = tmp_path / "events.jsonl"
    m.receipt(wal, first)
    monkeypatch.setattr(m, "release", lambda value: package)
    monkeypatch.setattr(m, "digest", lambda value: manifest)
    monkeypatch.setattr(m, "enter", lambda *args: (Mock(), actual))
    monkeypatch.setattr(m, "leave", Mock())
    monkeypatch.setattr(m, "sql_history", lambda *args: history)
    monkeypatch.setattr(m, "success", lambda *args: success)
    monkeypatch.setattr(m, "shape", lambda cursor: "5" * 64)
    sink = Mock()
    monkeypatch.setattr(m, "append", sink)
    result = m.reconcile(Mock(), actual, wal, approved_manifest_sha256=manifest)
    assert result["reconciled"] == ["RECONCILED_NOT_APPLIED"]
    assert m.wal_state(m.wal_events(wal))[a]["status"] == "RECONCILED_NOT_APPLIED"
    sink.assert_not_called()


def test_different_commit_attempt_is_not_attributed_to_pending(tmp_path, monkeypatch):
    actual, manifest, package, a, history, success = sql_fixture(
        monkeypatch, old_not_applied=False
    )
    first = {**start(attempt=a), "target": sha(actual)}
    wal = tmp_path / "events.jsonl"
    m.receipt(wal, first)
    monkeypatch.setattr(m, "release", lambda value: package)
    monkeypatch.setattr(m, "digest", lambda value: manifest)
    monkeypatch.setattr(m, "enter", lambda *args: (Mock(), actual))
    monkeypatch.setattr(m, "leave", Mock())
    monkeypatch.setattr(m, "sql_history", lambda *args: history)
    monkeypatch.setattr(m, "success", lambda *args: success)
    monkeypatch.setattr(m, "shape", lambda cursor: "5" * 64)
    with pytest.raises(ValueError, match="committed_attempt_conflict"):
        m.reconcile(Mock(), actual, wal, approved_manifest_sha256=manifest)
    assert len(m.pending_wal(m.wal_events(wal))) == 1


def test_sql_terminal_with_wrong_unit_rejected(monkeypatch):
    actual, manifest, package, a, history, success = sql_fixture(monkeypatch)
    events = m.records(None, None)
    events[2]["UnitId"] = "ES-B000"
    with pytest.raises(ValueError):
        m.sql_history(Mock(), package, manifest, actual)


def test_native_media_guid_rechecked_before_restore(monkeypatch):
    source = {"database": "CBN_P1ES_BASE_20261026_12345678", "server": "server"}
    checkpoint = {
        "source": source,
        "path": "/var/opt/mssql/data/" + source["database"] + "_file.bak",
        "backup_uuid": str(uuid4()),
    }
    header = {
        "BackupSetGUID": uuid4(),
        "DatabaseName": source["database"],
        "SoftwareVersionMajor": 15,
        "BackupType": 1,
        "Position": 1,
        "HasBackupChecksums": True,
        "IsCopyOnly": True,
        "ServerName": "server",
    }
    execute = Mock(return_value=[header])
    monkeypatch.setattr(recovery, "execute_results", execute)
    with pytest.raises(ValueError, match="backup_identity_or_header"):
        recovery.verify_backup(Mock(), checkpoint)
    assert execute.call_count == 1
    assert execute.call_args.args[1].startswith("RESTORE HEADERONLY")
