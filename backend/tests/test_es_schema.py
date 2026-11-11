"""Full drift and SQLCMD boundary checks without any SQL connection."""

import copy
import json
from pathlib import Path

import pytest
from tools.es_schema_catalog import compare
from tools.es_schema_migrate import TARGET, batches, pending_wal, receipt, wal_events

PACKAGE = Path(__file__).resolve().parents[1] / "migrations/cbn_spanish_schema_v1"


@pytest.fixture
def catalog():
    return json.loads((PACKAGE / "expected_catalog.json").read_text(encoding="utf-8"))


def test_full_source_catalog(catalog):
    assert len(catalog["tables"]) == 98
    assert len(catalog["columns"]) == 795
    assert compare(catalog, catalog)["passed"]


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("columns", "type_name", "int"),
        ("columns", "max_length", 999),
        ("columns", "is_nullable", True),
        ("columns", "identity_seed", "999"),
        ("columns", "collation_name", "Latin1_General_100_BIN2"),
        ("columns", "default_definition", "((123))"),
        ("columns", "is_sparse", True),
        ("checks", "definition", "((1)=(1))"),
        ("checks", "is_not_trusted", True),
        ("foreign_keys", "referenced_table", "CRMContacto"),
        ("foreign_keys", "delete_action", "CASCADE"),
        ("indexes", "filter_definition", "([Field]>0)"),
        ("indexes", "is_unique", False),
        ("indexes", "fill_factor", 70),
        ("table_options", "lock_escalation_desc", "DISABLE"),
        ("ansi_padding", "is_ansi_padded", False),
    ],
)
def test_same_counts_are_insufficient(catalog, section, key, value):
    changed = copy.deepcopy(catalog)
    row = next(r for r in changed[section] if r.get(key) != value)
    row[key] = value
    result = compare(changed, catalog)
    assert not result["passed"] and section in result["differing_sections"]


def test_rejects_wrong_FK_column_pair(catalog):
    changed = copy.deepcopy(catalog)
    changed["foreign_keys"][0]["columns"][0]["referenced_column"] = "OtherId"
    assert not compare(changed, catalog)["passed"]


def test_rejects_wrong_index_order(catalog):
    changed = copy.deepcopy(catalog)
    index = next(i for i in changed["indexes"] if len(i["columns"]) > 1)
    index["columns"][0]["key_ordinal"] = 99
    assert not compare(changed, catalog)["passed"]


def test_GO_inside_literals_is_not_a_batch():
    assert len(batches("SELECT N'first\nGO\nlast';\nGO\nSELECT 2;\n")) == 2
    assert len(batches("/* outer\n/* nested */\nGO\n*/SELECT 1;\nGO\n")) == 1
    assert len(batches("SELECT [GO]],part];\nGO\nSELECT 2;")) == 2


@pytest.mark.parametrize(
    "text",
    [":!! whoami\n", ":r other.sql\n", "GO 2\n", "SELECT 'unclosed", "/* unclosed"],
)
def test_rejects_unsafe_or_ambiguous_batch_input(text):
    with pytest.raises(ValueError):
        batches(text)


@pytest.mark.parametrize(
    "name",
    [
        "HORARIOSSIIE",
        "DBSIIE",
        "master",
        "DBSIIE_CRM_Esquema_ES_20261026",
        "CBN_C13_TRIAL_20261025_1f10a824",
        "CBN_P1ES_TRIAL_20261026_bad",
    ],
)
def test_original_and_unknown_targets_rejected(name):
    assert TARGET.fullmatch(name) is None


def test_WAL_pending_and_integrity(tmp_path):
    p = tmp_path / "wal.jsonl"
    receipt(p, {"event": "STARTED", "attempt": "one"})
    assert len(pending_wal(wal_events(p))) == 1
    receipt(p, {"event": "RECONCILED_NOT_APPLIED", "attempt": "one"})
    assert not pending_wal(wal_events(p))
    p.write_text(p.read_text().replace("one", "two", 1))
    with pytest.raises(ValueError):
        wal_events(p)
