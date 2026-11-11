"""Filter combinations preserve real contact representations and owner snapshots."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.sql_workspace import SqlWorkspace, matches_client


def record(**changes):
    return {
        "id": "one",
        "name": "Test Person",
        "phone": "0012",
        "city": " City ",
        "type": " Prospect ",
        "stage": "New",
        "tags": " Other, Follow up ",
        "programId": 7,
        "program": "Program",
        **changes,
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("query", "absent"),
        ("stage", "Other"),
        ("tag", "Follow"),
        ("city", "Other"),
        ("contact_type", "Other"),
        ("program_id", 8),
    ],
)
def test_every_filter_is_required(field, value):
    filters = dict(
        query=" person ",
        stage="New",
        tag="follow up",
        city="city",
        contact_type="prospect",
        program_id=7,
        program="Program",
    )
    assert matches_client(record(), **filters)
    filters[field] = value
    assert not matches_client(record(), **filters)


def test_program_id_retains_matching_legacy_text_without_matching_different_ids():
    assert matches_client(
        record(programId=None, program=" PROGRAM "), program_id=7, program="Program"
    )
    assert not matches_client(record(programId=8), program_id=7, program="Program")
    assert matches_client(record(programId=None), program=" program ")
    assert not matches_client(record(), program="program")
    assert not matches_client(
        record(programId=None, program=""), program_id=7, program=""
    )
    assert matches_client(record(programId=None, program=""))


def test_name_phone_search_does_not_silently_match_filter_fields():
    assert matches_client(record(), query="0012")
    assert not matches_client(record(), query="City")
    assert not matches_client(record(), query="Program")


def test_route_filters_complete_snapshot_and_preserves_owner_threads(monkeypatch):
    snapshot = {
        "clients": [
            record(),
            record(id="two", city="Other", type="x" * 100, programId=-1),
        ],
        "threads": [{"clientId": "two"}],
        "revision": "1",
        "contactGroups": [],
    }
    monkeypatch.setattr(SqlWorkspace, "read", lambda self: deepcopy(snapshot))
    monkeypatch.setattr(
        Settings, "from_environment", lambda: Settings(mode="local_sql_copy")
    )
    app = create_app()
    with TestClient(
        app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 1234)
    ) as client:
        response = client.get(
            "/api/local/crm/clients",
            params={
                "q": "person",
                "stage": "New",
                "tag": " follow up ",
                "city": "CITY",
                "contactType": "PROSPECT",
                "programId": 7,
                "program": "Program",
            },
            headers={"X-CRM-Local": "1"},
        )
        boundary = client.get(
            "/api/local/crm/clients",
            params={"contactType": "x" * 100, "programId": -1},
            headers={"X-CRM-Local": "1"},
        )
        assert boundary.status_code == 200
        assert [item["id"] for item in boundary.json()["clients"]] == ["two"]
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["clients"]] == ["one"]
    assert response.json()["threads"] == snapshot["threads"]
    assert len(snapshot["clients"]) == 2


def test_alias_name_search_returns_principal_once_without_reparenting_threads(
    monkeypatch,
):
    principal = record(id="principal", name="Primary")
    alias = record(id="alias", name="Searchable historical origin")
    snapshot = {
        "clients": [principal, alias],
        "threads": [{"clientId": "principal"}, {"clientId": "alias"}],
        "revision": "1",
        "contactGroups": [
            {
                "mergeId": "case",
                "sourceContactId": "alias",
                "targetContactId": "principal",
            }
        ],
    }
    monkeypatch.setattr(SqlWorkspace, "read", lambda self: deepcopy(snapshot))
    app = create_app()
    app.state.settings = Settings(mode="local_sql_copy")
    client = TestClient(
        app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 1234)
    )
    response = client.get(
        "/api/local/crm/clients?q=historical", headers={"X-CRM-Local": "1"}
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["clients"]] == ["principal"]
    assert response.json()["threads"] == snapshot["threads"]
    all_groups = client.get(
        "/api/local/crm/clients", headers={"X-CRM-Local": "1"}
    ).json()
    assert [item["id"] for item in all_groups["clients"]] == ["principal"]
