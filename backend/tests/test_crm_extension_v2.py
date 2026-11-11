"""Canonical v3 regression checks; the immutable v1 suite remains historical."""

import copy

import pytest

from tools import crm_extension as retired
from tools import crm_extension_snapshot_v2 as snapshot


class AdministrativeCursor:
    def execute(self, *_):
        return self

    def fetchval(self):
        return 1


@pytest.mark.parametrize("last_value", [None, 1, 2, 100])
def test_identity_gap_does_not_change_catalog_fingerprint(monkeypatch, last_value):
    def raw(_cursor, managed):
        if managed:
            return {"version": "old", "columns": [], "ddl_triggers": []}
        return {
            "version": "old",
            "columns": [
                {"schema_name": "dbo", "name": "Id", "identity_last_value": 42},
                {
                    "schema_name": "crm_channels",
                    "name": "Id",
                    "identity_last_value": last_value,
                },
            ],
            "ddl_triggers": [],
        }

    monkeypatch.setattr(snapshot, "legacy_metadata", raw)
    monkeypatch.setattr(snapshot, "records", lambda *_: [])
    actual = snapshot.metadata(AdministrativeCursor())
    assert actual["version"] == "cbn-extension-shape-v3"
    assert actual["columns"] == sorted(
        [
            {"schema_name": "dbo", "name": "Id"},
            {"schema_name": "crm_channels", "name": "Id"},
        ],
        key=snapshot.encode,
    )
    assert snapshot.sha(actual) == snapshot.sha(
        snapshot.metadata(AdministrativeCursor())
    )


def test_verified_sid_is_normalized_before_sorting():
    first = {
        "version": snapshot.VERSION,
        "principals": [
            {"name": snapshot.ACTOR, "sid": "A"},
            {"name": "other", "sid": "M"},
        ],
    }
    second = copy.deepcopy(first)
    second["principals"][0]["sid"] = "Z"
    second["principals"].reverse()
    assert snapshot.canonical(first, "A") == snapshot.canonical(second, "Z")
    assert first["principals"][0]["sid"] == "A"


def test_retired_release_and_transitive_schema_contract_are_immutable():
    assert retired.assets()[1] == (
        "e4f76c63592b4a99f35380496d25a34afb205645a0c4f5e885cf9ece8f901ca1"
    )
