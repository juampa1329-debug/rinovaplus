"""Offline C7 trust boundaries. SQL execution is exercised only by the harness."""

import copy
import json
import sys
from pathlib import Path
from uuid import UUID

import pytest

from tools import crm_extension as runner
from tools import crm_extension_snapshot as snapshot
from tools.cbn_foundation import Audit
from tools.crm_extension_contract import verify_final_shape

ROOT = Path(__file__).resolve().parents[2]


def shape():
    return {
        "version": snapshot.VERSION,
        "principals": [
            {
                "name": snapshot.ACTOR,
                "type_desc": "SQL_USER",
                "authentication_type_desc": "NONE",
                "default_schema_name": "dbo",
                "sid": "C7-SID",
            },
            {"name": "cbn_foundation_migrator", "sid": "C3-SID"},
            {"name": "cbn_foundation_runtime_c4", "sid": "C4-SID"},
        ],
        "all_permissions": [
            {
                "grantee": snapshot.ACTOR,
                "grantor": "dbo",
                "class_desc": cls,
                "target": target,
                "permission_name": permission,
                "state_desc": "GRANT",
                "minor_id": 0,
            }
            for cls, target, permission in sorted(runner.PERMISSIONS)
        ]
        + [
            {
                "grantee": snapshot.ACTOR,
                "grantor": "dbo",
                "class_desc": "SCHEMA",
                "target": "dbo",
                "permission_name": permission,
                "state_desc": "DENY",
                "minor_id": 0,
            }
            for permission in sorted(runner.DENIED_DBO)
        ],
        "role_membership": [],
        "schemas": [
            {"name": "dbo", "owner": "dbo"},
            {"name": "crm_channels", "owner": "dbo"},
        ],
        "catalog": [
            {"schema_name": "dbo", "name": "AcademicView", "type": "V"},
            {"schema_name": "crm_channels", "name": "Account", "type": "U"},
        ],
        "columns": [],
    }


def test_explicit_partition():
    assert snapshot.partition_tables(list(snapshot.table_sets())) == {
        "academic": 50,
        "foundation": 7,
        "extension": 0,
    }
    assert (
        snapshot.partition_tables(list(snapshot.table_sets(True)), True)["extension"]
        == 8
    )


def test_sql_catalog_char_padding_is_not_a_missing_table():
    raw = {
        "catalog": [
            {"schema_name": "crm", "name": "Contact", "type": "U "},
            {"schema_name": "crm", "name": "PK_Contact", "type": "PK"},
        ]
    }
    assert snapshot.table_names(raw) == ["crm.Contact"]


@pytest.mark.parametrize("mutation", ["extra", "missing", "case", "duplicate"])
def test_partition_never_adopts_unknown_objects(mutation):
    names = list(snapshot.table_sets(True))
    if mutation == "extra":
        names.append("crm_hidden.Contact")
    elif mutation == "missing":
        names.remove("crm.Contact")
    elif mutation == "case":
        names[names.index("crm.Contact")] = "crm.contact"
    else:
        names.append(names[0])
    with pytest.raises(ValueError):
        snapshot.partition_tables(names, True)


def test_c3_and_c4_security_are_preserved():
    raw = shape()
    runner.verify_direct_acl(raw, "C7-SID")
    projected = snapshot.protected(raw)
    assert {p["name"] for p in projected["principals"]} == {
        "cbn_foundation_migrator",
        "cbn_foundation_runtime_c4",
    }
    assert projected["catalog"] == [raw["catalog"][0]]
    assert projected["schemas"] == [{"name": "dbo", "owner": "dbo"}]
    assert raw["principals"][0]["sid"] == "C7-SID"
    assert snapshot.canonical(raw, "C7-SID")["principals"][0]["sid"] != "C7-SID"
    assert snapshot.canonical(raw, "C7-SID")["principals"][1]["sid"] == "C3-SID"


@pytest.mark.parametrize(
    "mutation",
    ["sid", "grant", "column", "state", "grantor", "login", "role", "owner", "missing"],
)
def test_actor_overlay_must_be_exact(mutation):
    raw = shape()
    if mutation == "sid":
        raw["principals"][0]["sid"] = "OTHER"
    elif mutation == "grant":
        raw["all_permissions"].append({"grantee": snapshot.ACTOR})
    elif mutation == "column":
        raw["all_permissions"][0]["minor_id"] = 1
    elif mutation == "state":
        raw["all_permissions"][0]["state_desc"] = "GRANT_WITH_GRANT_OPTION"
    elif mutation == "grantor":
        raw["all_permissions"][0]["grantor"] = "other"
    elif mutation == "login":
        raw["principals"][0]["authentication_type_desc"] = "INSTANCE"
    elif mutation == "role":
        raw["role_membership"].append({"member_name": snapshot.ACTOR})
    elif mutation == "owner":
        raw["schemas"][0]["owner"] = snapshot.ACTOR
    else:
        raw["all_permissions"].pop()
    with pytest.raises(ValueError):
        runner.verify_direct_acl(raw, "C7-SID")


class RowCursor:
    def __init__(self, value=None):
        self.value = value

    def execute(self, *args):
        self.sql = args[0]
        return self

    def fetchval(self):
        return self.value

    def fetchone(self):
        if "is_trustworthy_on" in self.sql:
            return (0, 0)
        return None


def test_missing_administrative_visibility_is_inconclusive():
    with pytest.raises(ValueError, match="visibility"):
        snapshot.metadata(RowCursor(0))


@pytest.mark.parametrize(
    "mutation",
    ["valid", "null", "role", "global", "academic", "journal", "missing", "visibility"],
)
def test_effective_rights_include_inherited_permissions_and_null(monkeypatch, mutation):
    class Cursor:
        calls = []

        def execute(self, sql, *args):
            self.calls.append(sql)
            self.sql = sql
            return self

        def fetchone(self):
            if "SELECT USER_NAME()" in self.sql:
                return (snapshot.ACTOR, int(mutation == "role"), 0, 0)
            return None

    def results(cursor, sql, params=()):
        if "sys.database_principals" in sql or "sys.synonyms" in sql:
            return []
        if "fn_my_permissions" in sql:
            return [
                {"permission_name": p}
                for p in runner.DATABASE_RIGHTS
                | ({"CONTROL"} if mutation == "global" else set())
            ]
        allowed = {
            "crm.Contact": {"REFERENCES"},
            "crm.Conversation": {"REFERENCES"},
            "crm.Message": {"REFERENCES"},
            "crm_meta.MigrationJournal": {"SELECT", "INSERT"},
        }
        values = [
            {
                "table_name": t,
                "permission_name": p,
                "value": int(p in allowed.get(t, set())),
            }
            for t in params
            for p in (
                "SELECT",
                "INSERT",
                "UPDATE",
                "DELETE",
                "ALTER",
                "REFERENCES",
                "CONTROL",
            )
        ]
        if mutation == "null":
            values[0]["value"] = None
        if mutation == "academic":
            values[0]["value"] = 1
        if mutation == "visibility":
            values.pop()
        for row in values:
            if (
                mutation == "journal"
                and row["table_name"] == snapshot.JOURNAL
                and row["permission_name"] == "DELETE"
            ):
                row["value"] = 1
            if (
                mutation == "missing"
                and row["table_name"] == "crm.Contact"
                and row["permission_name"] == "REFERENCES"
            ):
                row["value"] = 0
        return values

    monkeypatch.setattr(runner, "records", results)
    cursor = Cursor()
    if mutation == "valid":
        runner.verify_effective_acl(cursor)
    else:
        with pytest.raises(ValueError):
            runner.verify_effective_acl(cursor)
    assert cursor.calls[-1] == "REVERT;"


def guard_fixture(monkeypatch):
    raw = shape()
    prefix = [{"EventId": bytes([i])} for i in range(5)]
    ticket = {
        "scope": "SQL-C7-isolated-extension-only",
        "identity": {
            "database": "CBN_C7_TRIAL_20261025_01234567",
            "engine": 16,
            "compatibility": 160,
        },
        "actor_sid": "C7-SID",
        "legacy_rows": 5,
        "legacy_journal_sha256": snapshot.sha(prefix),
        "protected_metadata_sha256": snapshot.sha(snapshot.protected(raw)),
    }
    monkeypatch.setattr(runner, "target_identity", lambda c: ticket["identity"])
    monkeypatch.setattr(runner, "metadata", lambda c: raw)
    monkeypatch.setattr(runner, "verify_effective_acl", lambda c: None)
    monkeypatch.setattr(runner, "journal_binary", lambda c, n: prefix)
    return raw, prefix, ticket


@pytest.mark.parametrize(
    "mutation", ["C3_sid", "C4_sid", "empty_schema", "view", "prefix"]
)
def test_guard_protects_full_c5_universe(monkeypatch, mutation):
    raw, prefix, ticket = guard_fixture(monkeypatch)
    assert runner.guard(RowCursor(), ticket)["version"] == snapshot.VERSION
    if mutation == "C3_sid":
        raw["principals"][1]["sid"] = "different"
    elif mutation == "C4_sid":
        raw["principals"][2]["sid"] = "different"
    elif mutation == "empty_schema":
        raw["schemas"].append({"name": "crm_extra", "owner": "dbo"})
    elif mutation == "view":
        raw["catalog"].append({"schema_name": "dbo", "name": "Unknown", "type": "V"})
    else:
        prefix[0]["EventId"] = b"different"
    with pytest.raises(ValueError):
        runner.guard(RowCursor(), ticket)


@pytest.mark.parametrize(
    "database", ["HORARIOSSIIE", "DBSIIE", "master", "CBN_C3_TRIAL_20261024_ac8505b8"]
)
def test_c7_refuses_source_and_other_destinations(monkeypatch, database):
    _, _, ticket = guard_fixture(monkeypatch)
    ticket["identity"]["database"] = database
    with pytest.raises(ValueError, match="target_name"):
        runner.guard(RowCursor(), ticket)


def history_fixture(monkeypatch, kind="COMMITTED"):
    ticket = {
        "legacy_rows": 5,
        "identity": {"database": "new-copy"},
        "evidence_ref": "e",
        "approval_ref": "a",
        "backup_ref": "b",
    }
    release = {
        "sql_sha256": "1" * 64,
        "before_sha256": "2" * 64,
        "after_sha256": "3" * 64,
    }
    row = {
        "attempt": "ABCDABCD-ABCD-ABCD-ABCD-ABCDABCDABCD",
        "unit": runner.UNIT,
        "release_id": runner.RELEASE,
        "tool": runner.TOOL_VERSION,
        "shape_version": snapshot.VERSION,
        "principal": snapshot.ACTOR,
        "manifest": "A" * 64,
        "unit_hash": "1" * 64,
        "target_hash": snapshot.sha(ticket["identity"]).upper(),
        "before_hash": "2" * 64,
        "after_hash": None,
        "error": None,
        "evidence": "e",
        "approval": "a",
        "backup": "b",
        "success_key": None,
        "kind": "STARTED",
    }
    tail = [copy.deepcopy(row)]
    if kind != "STARTED":
        row.update(
            kind=kind,
            after_hash="3" * 64 if kind == "COMMITTED" else None,
            success_key=runner.UNIT if kind == "COMMITTED" else None,
        )
        tail.append(row)
    monkeypatch.setattr(runner, "records", lambda *a: [{} for _ in range(5)] + tail)
    return ticket, release, tail


def test_new_history_keeps_old_identity_and_normalizes_sql_uuid(monkeypatch):
    ticket, release, _ = history_fixture(monkeypatch)
    rows, committed = runner.history(None, ticket, release, "a" * 64)
    assert committed
    assert rows[0]["attempt"] == str(UUID(rows[0]["attempt"]))


@pytest.mark.parametrize(
    "field,value",
    [
        ("target_hash", "0" * 64),
        ("manifest", "0" * 64),
        ("shape_version", "cbn-foundation-shape-v1"),
        ("principal", "cbn_foundation_migrator"),
        ("unit", "CBN-B001"),
        ("before_hash", "0" * 64),
        ("after_hash", "0" * 64),
        ("success_key", None),
        ("error", "unexplained"),
        ("backup", "other"),
        ("kind", "UNKNOWN"),
    ],
)
def test_history_rejects_mismatched_or_unknown_state(monkeypatch, field, value):
    ticket, release, tail = history_fixture(monkeypatch)
    tail[-1][field] = value
    with pytest.raises(ValueError):
        runner.history(None, ticket, release, "a" * 64)


def test_success_cannot_be_repeated_in_another_attempt(monkeypatch):
    ticket, release, tail = history_fixture(monkeypatch)
    duplicate = copy.deepcopy(tail)
    for row in duplicate:
        row["attempt"] = "11111111-1111-1111-1111-111111111111"
    tail.extend(duplicate)
    with pytest.raises(ValueError, match="duplicate_success"):
        runner.history(None, ticket, release, "a" * 64)


def test_sql_shape_matches_source_columns_and_final_identity_collations():
    sys.path.insert(0, str(ROOT / "backend/tools"))
    from tools.inventory_migrations import scan

    original = scan(ROOT / "backend/migrations/011_channels.sql")
    proposed = scan(snapshot.PACKAGE / "B011_channels.sql")
    old = {t["name"]: t for t in original["tables"]}
    assert len(proposed["tables"]) == 8
    assert sum(len(t["columns"]) for t in proposed["tables"]) == 57
    assert sum(len(t["foreign_keys"]) for t in proposed["tables"]) == 10
    for table in proposed["tables"]:

        def columns(t):
            return [
                (
                    c["name"],
                    c["type"].replace("datetime2(7)", "datetime2"),
                    c["nullable"],
                    c["identity"],
                )
                for c in t["columns"]
            ]

        assert columns(table) == columns(old[table["name"]])
    text = (snapshot.PACKAGE / "B011_channels.sql").read_text()
    assert text.count("COLLATE Latin1_General_100_BIN2 NOT NULL") == 4
    assert text.count("COLLATE Latin1_General_100_BIN2 NULL") == 1
    assert len(proposed["indexes"]) == 3
    assert not proposed["insert_targets"]


def test_audit_is_durable_target_bound_and_blocks_unknown(tmp_path):
    path = tmp_path / "audit.jsonl"
    audit = Audit(path, "new-target")
    audit.add("attempt", runner.UNIT, "STARTED")
    audit.add("attempt", runner.UNIT, "UNKNOWN")
    assert len(audit.unresolved()) == 1
    audit.add("attempt", runner.UNIT, "RECONCILED")
    assert not audit.unresolved()
    with pytest.raises(RuntimeError):
        Audit(path, "old-target").rows()


def test_changed_release_ticket_rejects_before_sql(monkeypatch):
    monkeypatch.setattr(runner, "assets", lambda: ({}, "pinned", {}))
    with pytest.raises(ValueError, match="release_ticket"):
        runner.run(None, {"release_sha256": "changed"}, None)


@pytest.mark.parametrize("operation", [runner.run, runner.reconcile])
def test_caller_transaction_is_refused_without_rollback(
    monkeypatch, tmp_path, operation
):
    cursor = RowCursor(1)
    cursor.closed = False
    cursor.close = lambda: setattr(cursor, "closed", True)

    class Connection:
        def cursor(self):
            return cursor

    monkeypatch.setattr(runner, "assets", lambda: ({}, "pinned", {}))
    with pytest.raises(ValueError, match="open_transaction"):
        operation(
            Connection(), {"release_sha256": "pinned", "identity": {}}, tmp_path / "a"
        )
    assert cursor.closed and cursor.sql == "SELECT @@TRANCOUNT"


@pytest.mark.parametrize(
    "mutation", ["valid", "unknown", "both", "missing", "type", "case"]
)
def test_only_synonyms_already_in_c5_universe_are_accepted(mutation):
    raw = {
        "objects": [{"schema_name": "dbo", "name": "Known", "type": "SN"}],
        "synonyms": [
            {
                "schema_name": "dbo",
                "name": "Known",
                "base_object_name": "private-target",
            }
        ],
        "user_types": [],
    }
    if mutation == "unknown":
        raw["synonyms"].append({"schema_name": "dbo", "name": "Extra"})
    if mutation == "both":
        raw["synonyms"].append({"schema_name": "dbo", "name": "Extra"})
        raw["objects"].append({"schema_name": "dbo", "name": "Extra", "type": "SN"})
    if mutation == "missing":
        raw["synonyms"] = []
    if mutation == "type":
        raw["objects"][0]["type"] = "V"
    if mutation == "case":
        raw["synonyms"][0]["name"] = "known"
    if mutation == "valid":
        snapshot.validate_extra_catalog(raw, ["dbo.Known"])
    else:
        with pytest.raises(ValueError):
            snapshot.validate_extra_catalog(raw, ["dbo.Known"])


def test_synonym_definition_is_new_protected_c7_metadata():
    raw = shape()
    raw["synonyms"] = [
        {"schema_name": "dbo", "name": "Known", "base_object_name": "target-one"}
    ]
    before = snapshot.sha(snapshot.protected(raw))
    raw["synonyms"][0]["base_object_name"] = "target-two"
    assert snapshot.sha(snapshot.protected(raw)) != before


def test_digest_cannot_query_a_view_or_synonym_target(monkeypatch):
    def columns(cursor, sql, params):
        assert "OBJECT_ID(?,'U')" in sql
        return []

    monkeypatch.setattr(snapshot, "records", columns)
    with pytest.raises(ValueError, match="missing_digest_columns"):
        snapshot.data_signature(None, ["crm.Contact"])


@pytest.mark.parametrize(
    "mutation", ["valid", "alias", "impersonate", "alias_null", "impersonate_null"]
)
def test_alias_and_impersonation_are_effective_permission_boundaries(
    monkeypatch, mutation
):
    class Cursor:
        def execute(self, sql, *params):
            self.sql, self.params = sql, params
            return self

        def fetchone(self):
            return (
                (snapshot.ACTOR, 0, 0, 0) if "SELECT USER_NAME()" in self.sql else None
            )

        def fetchval(self):
            category = "impersonate" if "'USER'" in self.sql else "alias"
            if mutation == category:
                return 1
            if mutation == category + "_null":
                return None
            return 0

    def result(cursor, sql, params=()):
        if "sys.synonyms" in sql:
            return [{"name": "dbo.Known"}]
        if "sys.database_principals" in sql:
            return [{"name": "cbn_foundation_migrator"}]
        if "fn_my_permissions" in sql:
            return [{"permission_name": p} for p in runner.DATABASE_RIGHTS]
        expected = {
            "crm.Contact": {"REFERENCES"},
            "crm.Conversation": {"REFERENCES"},
            "crm.Message": {"REFERENCES"},
            snapshot.JOURNAL: {"SELECT", "INSERT"},
        }
        return [
            {
                "table_name": t,
                "permission_name": p,
                "value": int(p in expected.get(t, set())),
            }
            for t in params
            for p in (
                "SELECT",
                "INSERT",
                "UPDATE",
                "DELETE",
                "ALTER",
                "REFERENCES",
                "CONTROL",
            )
        ]

    monkeypatch.setattr(runner, "records", result)
    cursor = Cursor()
    if mutation == "valid":
        runner.verify_effective_acl(cursor)
    else:
        with pytest.raises(ValueError):
            runner.verify_effective_acl(cursor)
    assert cursor.sql == "REVERT;"


@pytest.mark.parametrize("mutation", ["valid", "login", "role", "global_grant"])
def test_original_c3_actor_is_verified_before_new_baseline(mutation):
    name = "cbn_foundation_migrator"
    frozen = json.loads(
        (ROOT / "backend/migrations/cbn_foundation/expected-shapes.json").read_text()
    )
    permissions = [
        {
            "grantee": name,
            "grantor": "dbo",
            "minor_id": 0,
            "class_desc": "DATABASE",
            "target": "<database>",
            "permission_name": p,
            "state_desc": "GRANT",
        }
        for p in ("CONNECT", "CREATE TABLE", "VIEW DEFINITION")
    ]
    permissions += [
        {
            "grantee": r["grantee"],
            "grantor": r["grantor"],
            "minor_id": 0,
            "class_desc": r["class_desc"],
            "target": r["schema_name"],
            "permission_name": r["permission_name"],
            "state_desc": r["state_desc"],
        }
        for r in frozen["prepared"]["permissions"]
        if r["grantee"] == name
    ]
    raw = {
        "principals": [
            {
                "name": name,
                "type_desc": "SQL_USER",
                "authentication_type_desc": "NONE",
                "default_schema_name": "dbo",
            }
        ],
        "all_permissions": permissions,
        "role_membership": [],
        "schemas": [{"owner": "dbo"}],
    }
    if mutation == "login":
        raw["principals"][0]["authentication_type_desc"] = "INSTANCE"
    if mutation == "role":
        raw["role_membership"].append({"member_name": name})
    if mutation == "global_grant":
        raw["all_permissions"].append({"grantee": name})
    if mutation == "valid":
        runner.verify_legacy_actor(raw)
    else:
        with pytest.raises(ValueError):
            runner.verify_legacy_actor(raw)


def test_old_accepted_inputs_are_still_intact():
    release = json.loads(
        (ROOT / "backend/migrations/cbn_foundation/release.json").read_text()
    )
    for record in release["tool_files"]:
        assert runner.file_sha(ROOT / record["path"]) == record["sha256"]


def independent_shape_fixture():
    spec = json.loads((snapshot.PACKAGE / "shape-spec.json").read_text())
    value = {
        k: []
        for k in (
            "columns",
            "indexes",
            "checks",
            "foreign_keys",
            "catalog",
            "properties",
            "triggers",
            "synonyms",
            "user_types",
            "dependencies",
        )
    }
    value["version"] = snapshot.VERSION
    value["schemas"] = [{"name": "crm_channels", "owner": "dbo"}]
    for c in spec["columns"]:
        value["columns"].append(
            {
                "schema_name": "crm_channels",
                "table_name": c["table"],
                "name": c["name"],
                "ordinal": c["ordinal"],
                "type_name": c["type_name"],
                "max_length": c["max_length"],
                "precision": c["precision"],
                "scale": c["scale"],
                "is_nullable": c["nullable"],
                "is_identity": c["identity"],
                "is_computed": False,
                "computed_definition": None,
                "collation_name": "Modern_Spanish_CI_AS"
                if c["collation"] == "<database>"
                else c["collation"],
                "default_name": c["default_name"],
                "default_definition": c["default"],
                "identity_seed": "1" if c["identity"] else None,
                "identity_increment": "1" if c["identity"] else None,
            }
        )
    for i in spec["indexes"]:
        for position, column in enumerate(i["columns"], 1):
            value["indexes"].append(
                {
                    "schema_name": "crm_channels",
                    "table_name": i["table"],
                    "name": i["name"],
                    "column_name": column,
                    "key_ordinal": position,
                    "type_desc": "CLUSTERED" if i["kind"] == "PK" else "NONCLUSTERED",
                    "is_primary_key": i["kind"] == "PK",
                    "is_unique_constraint": i["kind"] == "UQ",
                    "is_unique": i["unique"],
                    "is_disabled": False,
                    "is_included_column": False,
                    "is_descending_key": False,
                    "fill_factor": 0,
                    "is_padded": False,
                    "ignore_dup_key": False,
                    "allow_row_locks": True,
                    "allow_page_locks": True,
                    "has_filter": bool(i["filter"]),
                    "filter_definition": i["filter"],
                }
            )
    for c in spec["checks"]:
        definition = (
            "ISJSON([" + c["column"] + "])=(1)"
            if c["kind"] == "json"
            else " OR ".join("[" + c["column"] + "]='" + v + "'" for v in c["values"])
        )
        value["checks"].append(
            {
                "schema_name": "crm_channels",
                "table_name": c["table"],
                "name": c["name"],
                "definition": definition,
                "is_disabled": False,
                "is_not_trusted": False,
                "is_not_for_replication": False,
            }
        )
    for f in spec["foreign_keys"]:
        target_schema, target_table = f["target_table"].split(".")
        value["foreign_keys"].append(
            {
                "schema_name": "crm_channels",
                "table_name": f["source_table"].split(".")[1],
                "name": f["name"],
                "column_name": f["source_columns"][0],
                "target_schema": target_schema,
                "target_table": target_table,
                "target_column": f["target_columns"][0],
                "ordinal": 1,
                "delete_referential_action": 0,
                "update_referential_action": 0,
                "is_disabled": False,
                "is_not_trusted": False,
                "is_not_for_replication": False,
            }
        )
    catalog = {(c["table"], "U", None) for c in spec["columns"]}
    catalog |= {
        (c["default_name"], "D", c["table"])
        for c in spec["columns"]
        if c["default_name"]
    }
    catalog |= {(c["name"], "C", c["table"]) for c in spec["checks"]}
    catalog |= {
        (i["name"], i["kind"], i["table"])
        for i in spec["indexes"]
        if i["kind"] in {"PK", "UQ"}
    }
    catalog |= {
        (f["name"], "F", f["source_table"].split(".")[1]) for f in spec["foreign_keys"]
    }
    value["catalog"] = [
        {"schema_name": "crm_channels", "name": n, "type": t, "parent_name": p}
        for n, t, p in catalog
    ]
    value["properties"] = [
        {
            "schema_name": "crm_channels",
            "name": n,
            "value": v,
            "class": 3,
            "minor_id": 0,
            "object_name": None,
        }
        for n, v in spec["properties"].items()
    ]
    return value


def test_independent_contract_accepts_complete_final_shape():
    verify_final_shape(independent_shape_fixture(), "Modern_Spanish_CI_AS")


@pytest.mark.parametrize(
    "mutation",
    [
        "type",
        "length",
        "precision",
        "scale",
        "nullable",
        "ordinal",
        "identity",
        "default",
        "default_name",
        "computed",
        "collation",
        "filter",
        "key_columns",
        "key_kind",
        "check",
        "trust",
        "fk_target",
        "cascade",
        "module",
        "property",
        "synonym",
    ],
)
def test_reference_cannot_learn_incomplete_or_altered_shape(mutation):
    raw = independent_shape_fixture()
    if mutation == "type":
        raw["columns"][0]["type_name"] = "nvarchar"
    elif mutation == "length":
        raw["columns"][0]["max_length"] += 1
    elif mutation == "precision":
        raw["columns"][0]["precision"] += 1
    elif mutation == "scale":
        raw["columns"][0]["scale"] += 1
    elif mutation == "nullable":
        raw["columns"][0]["is_nullable"] = None
    elif mutation == "ordinal":
        raw["columns"][0]["ordinal"] = 2
    elif mutation == "identity":
        raw["columns"][-5]["identity_seed"] = "2"
    elif mutation == "default":
        next(c for c in raw["columns"] if c["default_name"])["default_definition"] = (
            "'wrong'"
        )
    elif mutation == "default_name":
        next(c for c in raw["columns"] if c["default_name"])["default_name"] = "wrong"
    elif mutation == "computed":
        raw["columns"][0]["is_computed"] = True
    elif mutation == "collation":
        raw["columns"][0]["collation_name"] = "wrong"
    elif mutation == "filter":
        next(i for i in raw["indexes"] if i["has_filter"])["filter_definition"] = (
            "MessageId IS NULL"
        )
    elif mutation == "key_columns":
        raw["indexes"][0]["column_name"] = "wrong"
    elif mutation == "key_kind":
        raw["indexes"][0]["is_primary_key"] = False
    elif mutation == "check":
        raw["checks"][0]["definition"] = "1=1"
    elif mutation == "trust":
        raw["checks"][0]["is_not_trusted"] = True
    elif mutation == "fk_target":
        raw["foreign_keys"][0]["target_schema"] = "dbo"
    elif mutation == "cascade":
        raw["foreign_keys"][0]["delete_referential_action"] = 1
    elif mutation == "module":
        raw["catalog"].append(
            {
                "schema_name": "crm_channels",
                "name": "unexpected",
                "type": "P",
                "parent_name": None,
            }
        )
    elif mutation == "property":
        raw["properties"][0]["value"] = "wrong"
    else:
        raw["synonyms"].append({"schema_name": "crm_channels", "name": "unexpected"})
    with pytest.raises(ValueError):
        verify_final_shape(raw, "Modern_Spanish_CI_AS")


@pytest.mark.parametrize("literal", ["que ued", "que[ued]"])
def test_sql_literal_contents_are_not_removed_by_normalization(literal):
    raw = independent_shape_fixture()
    row = next(c for c in raw["checks"] if c["name"] == "CK_Channels_Queue_State")
    row["definition"] = row["definition"].replace("'queued'", "'" + literal + "'")
    with pytest.raises(ValueError, match="check_definition"):
        verify_final_shape(raw, "Modern_Spanish_CI_AS")


@pytest.mark.parametrize("phase", ["started", "applied", "failure", "reconciled"])
@pytest.mark.parametrize(
    "outcome", ["normal", "committed_ack_lost", "rolled_back_ack_lost"]
)
def test_commit_boundary_executes_the_sql_outcome_before_reporting(phase, outcome):
    cursor = RowCursor()
    fault = (
        None
        if outcome == "normal"
        else phase + ("_rolled_back" if outcome == "rolled_back_ack_lost" else "")
    )
    if outcome == "normal":
        runner.commit(cursor, phase, fault)
    else:
        with pytest.raises(OSError):
            runner.commit(cursor, phase, fault)
    assert cursor.sql == (
        "ROLLBACK;" if outcome == "rolled_back_ack_lost" else "COMMIT;"
    )


def test_other_unit_audit_cannot_be_reconciled_as_b011(tmp_path):
    ticket = {"identity": {"database": "new-copy"}}
    path = tmp_path / "wrong-unit.jsonl"
    audit = Audit(path, snapshot.sha(ticket["identity"]))
    audit.add("attempt", "C7-PREPARE", "UNKNOWN")
    with pytest.raises(ValueError, match="audit_unit"):
        runner.migration_audit(path, ticket)


@pytest.mark.parametrize("extended,committed", [(False, True), (True, False)])
def test_reconciliation_rejects_global_history_shape_contradiction(
    monkeypatch, tmp_path, extended, committed
):
    ticket = {"identity": {}, "release_sha256": "pinned"}
    path = tmp_path / "audit.jsonl"
    attempt = "11111111-1111-1111-1111-111111111111"
    audit = Audit(path, snapshot.sha(ticket["identity"]))
    audit.add(attempt, runner.UNIT, "STARTED")
    audit.add(attempt, runner.UNIT, "UNKNOWN")
    cursor = RowCursor(0)
    cursor.close = lambda: None

    class Connection:
        def cursor(self):
            return cursor

    monkeypatch.setattr(runner, "assets", lambda: ({}, "pinned", {}))
    monkeypatch.setattr(runner, "acquire", lambda *a: None)
    monkeypatch.setattr(runner, "transaction", lambda *a: None)
    monkeypatch.setattr(runner, "verified_state", lambda *a: extended)
    monkeypatch.setattr(
        runner,
        "history",
        lambda *a: ([{"attempt": attempt, "kind": "STARTED"}], committed),
    )
    with pytest.raises(ValueError, match="history_shape_disagreement"):
        runner.reconcile(Connection(), ticket, path)
    assert len(audit.unresolved()) == 1


@pytest.mark.parametrize(
    "database", ["HORARIOSSIIE", "DBSIIE", "master", "CBN_C3_TRIAL_20261024_ac8505b8"]
)
def test_administrative_preparation_also_refuses_original_databases(
    monkeypatch, database
):
    from tools import rehearse_crm_extension as harness

    class Connection:
        def cursor(self):
            return None

    monkeypatch.setattr(
        harness,
        "target_identity",
        lambda c: {"database": database, "engine": 16, "compatibility": 160},
    )
    monkeypatch.setattr(
        harness, "capture", lambda *a: pytest.fail("source read before target guard")
    )
    with pytest.raises(ValueError, match="isolated_restoration"):
        harness.prepare_database(Connection(), {})
