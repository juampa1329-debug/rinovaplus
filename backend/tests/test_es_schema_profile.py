"""A correctly sealed but incorrectly prepared partition must still fail."""

import json
import time
from types import SimpleNamespace
from unittest.mock import Mock

import app.es_schema_profile as p
import pytest
import tools.es_schema_catalog_v2 as catalog


@pytest.fixture
def ticket(monkeypatch):
    layout = json.loads((p.PACKAGE / "table_map.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(p, "release", Mock())
    return {
        "version": p.VERSION,
        "expires_at": int(time.time()) + 300,
        "migration_manifest_sha256": "0" * 64,
        "core_map": dict(p.CORE_MAP),
        "tables": sorted(
            set(layout["CRM_map"].values())
            | set(layout["academic_tables"])
            | {"crm_meta.MigrationJournal"}
        ),
        "academic_tables": layout["academic_tables"],
    }


def test_exact_approved_partition(ticket):
    assert len(p.partition(ticket)[1]) == 99


def test_prepared_academic_as_core_rejected_before_connect(ticket):
    ticket["core_map"]["crm.Contact"] = ticket["academic_tables"][0]
    with pytest.raises(ValueError, match="partition_mismatch"):
        p.partition(ticket)


def test_incomplete_universe_rejected(ticket):
    ticket["tables"].pop()
    with pytest.raises(ValueError, match="partition_mismatch"):
        p.partition(ticket)


def test_omitted_academic_rejected(ticket):
    ticket["academic_tables"] = ticket["academic_tables"][:-1]
    with pytest.raises(ValueError, match="partition_mismatch"):
        p.partition(ticket)


@pytest.mark.parametrize(
    "name", ["HORARIOSSIIE", "DBSIIE", "CBN_C13_TRIAL_20261025_1f10a824"]
)
def test_foreign_target_rejected_before_transport(ticket, name):
    settings = SimpleNamespace(
        ticket=ticket,
        connection={
            "database": name,
            "username": "x",
            "server": "localhost",
            "port": 1433,
            "certificate_hostname": "localhost",
            "password": "not-used",
        },
    )
    with pytest.raises(ValueError):
        p.connection_text(settings)


def test_TLS_cannot_be_disabled_by_extra_connection_fields(ticket):
    database = "CBN_P1ES_RECOVERY_20261026_12345678"
    settings = SimpleNamespace(
        ticket=ticket,
        connection={
            "database": database,
            "username": p.principal(database),
            "server": "localhost",
            "port": 1433,
            "certificate_hostname": "localhost",
            "password": "not-used",
            "encrypt": False,
            "trust_server_certificate": True,
        },
    )
    value = p.connection_text(settings)
    assert "Encrypt=Yes;TrustServerCertificate=No;" in value


@pytest.mark.parametrize(
    "field", ["optimize_for_sequential_key", "statistics_norecompute"]
)
def test_declared_index_options_are_part_of_catalog(field):
    expected = json.loads(
        (p.PACKAGE / "expected_catalog.json").read_text(encoding="utf-8")
    )
    changed = json.loads(json.dumps(expected))
    changed["indexes"][0][field] = True
    assert not catalog.compare(changed, expected)["passed"]
