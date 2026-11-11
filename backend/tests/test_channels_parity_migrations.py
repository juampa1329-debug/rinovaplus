"""C11 safety regressions. No SQL, HTTP, environment or application startup."""

import copy
import uuid

import pytest

from tools import channels_parity as runner
from tools import channels_parity_contract as contract
from tools import channels_parity_snapshot as snapshot
from tools.cbn_foundation import Blocked
from tools.check_channels_parity import normalize


@pytest.mark.parametrize(
    "name",
    [
        "dbo;DROP",
        "a.b",
        "[value]",
        "x]",
        "foo--",
        "",
        "x" * 129,
        "a b",
        "0name",
        "ñname",
    ],
)
def test_unsafe_SQL_identifier_is_rejected(name):
    with pytest.raises(ValueError, match="identifier"):
        contract.quote(name)


@pytest.mark.parametrize(
    "name",
    [
        "HORARIOSSIIE",
        "DBSIIE",
        "CBN_C9_TRIAL_20261025_23ac78d3",
        "CBN_C3_TRIAL_20261024_ac8505b8",
        "CBN_C11_TRIAL_20261025_abcdefgg",
        "CBN_C11_TRIAL_20261025_aabbccdd;DROP",
    ],
)
def test_C11_destination_does_not_match_sources_or_injected_names(name):
    assert contract.TARGET.fullmatch(name) is None


def test_legacy_allowlist_comes_from_the_eight_real_B011_tables():
    expression = contract.CHECKS["LegacyBinding"][0]
    import re

    actual = set(re.findall(r"'([^']+)'", expression))
    assert actual == set(snapshot.PARTITION["extension"])


def test_provider_operation_accepts_contract_confirmed_state():
    source = contract.model()
    expression = contract.CHECKS["ProviderOperation"][0]
    for state in source["remote_operations"]["states"]:
        assert "'" + state + "'" in expression
    assert "succeeded" not in expression


def test_unknown_SQL_type_cannot_be_emitted():
    source = copy.deepcopy(contract.model())
    source["tables"][0]["columns"]["ContextId"]["type"] = (
        "int); DROP TABLE dbo.Student;--"
    )
    with pytest.raises(ValueError, match="SQL_type"):
        contract.compile_units(source)


def test_new_unit_foreign_keys_follow_all_its_creates_for_the_OAuth_cycle():
    sql = contract.compile_units()["CBN-CHP002"]
    assert sql.index("ALTER TABLE") > sql.rindex("CREATE TABLE")
    assert "REFERENCES [dbo]" not in sql


def test_compiler_preserves_all_optional_owner_filters_and_SQL_guards():
    sql = "\n".join(contract.compile_units().values())
    assert "SESSION_CONTEXT" in sql and "USER_NAME()" in sql and "@@TRANCOUNT<>1" in sql
    assert "DROP TABLE" not in sql and "ALTER TABLE [dbo]" not in sql
    assert sql.count("FOREIGN KEY(") == 78
    assert "BodyKeyVersion IS NOT NULL AND BodyNonce IS NOT NULL" in sql


class FailingCursor:
    def __init__(self):
        self.closed = False
        self.commands = []

    def execute(self, command, *_):
        self.commands.append(command)
        raise OSError("disconnected")

    def close(self):
        self.closed = True
        raise OSError("disconnected-close")


def test_cleanup_attempts_every_step_without_masking_commit_unknown():
    c = FailingCursor()
    runner.cleanup(c, True)
    assert c.closed and len(c.commands) == 2


class OpenCursor:
    def __init__(self):
        self.closed = False
        self.commands = []

    def execute(self, command, *_):
        self.commands.append(command)
        return self

    def fetchval(self):
        return 1

    def close(self):
        self.closed = True


@pytest.mark.parametrize("function", [runner.run, runner.reconcile])
def test_rejecting_caller_transaction_never_rolls_it_back(
    monkeypatch, tmp_path, function
):
    monkeypatch.setattr(runner, "assets", lambda: ({"units": []}, "release"))
    c = OpenCursor()

    class Connection:
        def cursor(self):
            return c

    with pytest.raises(ValueError, match="C11_open_transaction"):
        function(
            Connection(),
            {"release_sha256": "release", "identity": {}},
            tmp_path / "audit.jsonl",
        )
    assert c.closed and c.commands == ["SELECT @@TRANCOUNT"]


def test_owner_change_is_part_of_the_protected_catalog():
    shape = {
        "version": "v",
        "object_owners": [
            {"schema_name": "crm", "object_name": "Contact", "effective_owner": "dbo"}
        ],
    }
    changed = copy.deepcopy(shape)
    changed["object_owners"][0]["effective_owner"] = "guest"
    assert snapshot.sha(snapshot.protected(shape)) != snapshot.sha(
        snapshot.protected(changed)
    )


@pytest.mark.parametrize(
    "first,second", [("N'a b'", "N'ab'"), ("N'(x)'", "N'x'"), ("N'[]'", "N''")]
)
def test_default_normalizer_preserves_literal_contents(first, second):
    assert normalize(first) != normalize(second)


def test_external_audit_cannot_mix_targets(tmp_path):
    path = tmp_path / "audit.jsonl"
    runner.Audit(path, "one").add("attempt", "unit", "UNKNOWN")
    with pytest.raises(Blocked, match="audit_target_mismatch"):
        runner.Audit(path, "two").rows()


@pytest.mark.parametrize("phase", ["started", "applied", "failure", "reconciled"])
@pytest.mark.parametrize("rolled_back", [False, True])
def test_lost_commit_response_remains_explicitly_unknown(phase, rolled_back):
    c = OpenCursor()
    with pytest.raises(runner.CommitUnknown):
        runner.commit(c, phase, phase + ("_rolled_back" if rolled_back else ""))
    assert c.commands == ["ROLLBACK;" if rolled_back else "COMMIT;"]


@pytest.mark.parametrize("future,interleave", [(True, False), (False, True)])
def test_history_cannot_start_future_unit_or_interleave_attempts(
    monkeypatch, future, interleave
):
    units = [
        {
            "id": "CBN-CHP00" + str(i),
            "sha256": "a" * 64,
            "before_sha256": "b" * 64,
            "after_sha256": "c" * 64,
        }
        for i in range(1, 6)
    ]
    index = 3 if future else 0
    row = {
        "attempt": str(uuid.uuid4()),
        "unit": units[index]["id"],
        "kind": "STARTED",
        "release_id": contract.RELEASE,
        "tool": "SQL-C11-v1",
        "shape_version": contract.VERSION,
        "principal": contract.ACTOR,
        "manifest": "d" * 64,
        "unit_hash": "a" * 64,
        "target_hash": snapshot.sha({}),
        "before_hash": "b" * 64,
        "after_hash": None,
        "evidence": "e",
        "approval": "a",
        "backup_ref": "b",
        "success_key": None,
        "error": None,
        "related_attempt": None,
        "related_unit": None,
    }
    rows = [{}] * 7 + [row]
    if interleave:
        rows.append({**row, "attempt": str(uuid.uuid4())})
    monkeypatch.setattr(runner, "records", lambda *_: copy.deepcopy(rows))
    monkeypatch.setattr(runner, "journal_binary", lambda *_: [])
    ticket = {
        "identity": {},
        "preservation": {"legacy_journal": snapshot.sha([])},
        "evidence_ref": "e",
        "approval_ref": "a",
        "backup_ref": "b",
    }
    with pytest.raises(ValueError, match="C11_history_pending_unit"):
        runner.history(None, ticket, {"units": units}, "d" * 64)
