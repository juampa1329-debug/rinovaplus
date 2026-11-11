"""Admissions scope, identity and transaction regressions without operator data."""

from contextlib import contextmanager
from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.modules.admissions.application.service import AdmissionsRepository, FollowupWrite, document_key, page
from app.config import Settings
from app.main import create_app


class ReadCursor:
    def __init__(self, result_sets):
        self.result_sets = iter(result_sets)
        self.calls = []

    def execute(self, sql, *args):
        if sql in (
            "SELECT SCHEMA_ID(N'crm_merge')",
            "SELECT SCHEMA_ID(N'crm_strategy')",
        ):
            self.result = [{"schema": None}]
            self.description = [("schema",)]
            return self
        self.calls.append((sql, args))
        self.result = next(self.result_sets)
        self.description = [(key,) for key in self.result[0]] if self.result else []
        return self

    def fetchone(self):
        return tuple(self.result[0].values()) if self.result else None

    def fetchall(self):
        return [tuple(row.values()) for row in self.result]


class Workspace:
    def __init__(self, cursor):
        self.cursor = cursor
        self.commits = self.rollbacks = 0

    @contextmanager
    def transaction(self, write=False):
        before = deepcopy(getattr(self.cursor, "data", {}))
        try:
            yield self.cursor
            self.commits += 1
        except BaseException:
            self.cursor.data = before
            self.rollbacks += 1
            raise


@pytest.mark.parametrize(
    "active,expected",
    [([False, True], 3), ([True, True], None), ([False, False], None)],
)
def test_unique_active_period_not_latest_id(active, expected):
    cursor = ReadCursor(
        [
            [
                {"id": 9, "label": "Future", "active": active[0]},
                {"id": 3, "label": "Active", "active": active[1]},
            ]
        ]
    )
    result = AdmissionsRepository(Workspace(cursor)).periods()
    assert result["activePeriodId"] == expected
    assert result["selectionRequired"] is (expected is None)


def test_list_scopes_source_period_and_bounded_literal_search():
    cursor = ReadCursor([[{"id": 3}], [{"id": n} for n in range(26)]])
    result = AdmissionsRepository(Workspace(cursor)).applicants(3, "[%_", 25)
    sql, args = cursor.calls[-1]
    assert "WHERE a.Id_Periodo=?" in sql
    assert "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY" in sql
    assert "[%_" not in sql
    assert args == (
        3,
        "[%_",
        "%[[][%][_]%",
        "%[[][%][_]%",
        None,
        None,
        None,
        None,
        25,
        26,
    )
    assert result["hasMore"] and len(result["items"]) == 25
    assert result["periodId"] == 3


def test_program_and_schedule_filters_precede_pagination_and_keep_source_period():
    cursor = ReadCursor([[{"id": 3}], []])
    result = AdmissionsRepository(Workspace(cursor)).applicants(3, "Test", 25, 8, 4)
    sql, args = cursor.calls[-1]
    assert sql.index("p.Id_Programa=?") < sql.index("OFFSET ?")
    assert sql.index("p.Id_Jornada=?") < sql.index("OFFSET ?")
    assert "WHERE a.Id_Periodo=?" in sql
    assert args == (3, "Test", "%Test%", "%Test%", 8, 8, 4, 4, 25, 26)
    assert result["items"] == []


def test_filter_options_come_from_applicants_in_selected_period_and_program_schedule():
    options = [{"programId": 8, "program": None, "scheduleId": 4, "schedule": "Test"}]
    cursor = ReadCursor([[{"id": 3}], options])
    assert AdmissionsRepository(Workspace(cursor)).filters(3) == {
        "periodId": 3,
        "items": options,
    }
    sql, args = cursor.calls[-1]
    assert "WHERE a.Id_Periodo=?" in sql and args == (3,)
    assert "j.Id_Jornada=p.Id_Jornada" in sql
    assert "ACDetalleJornada" not in sql


def test_unknown_filter_period_does_not_return_global_options():
    cursor = ReadCursor([[]])
    with pytest.raises(HTTPException) as failure:
        AdmissionsRepository(Workspace(cursor)).filters(3)
    assert failure.value.status_code == 404
    assert len(cursor.calls) == 1


def test_unknown_period_has_no_unfiltered_fallback():
    cursor = ReadCursor([[]])
    with pytest.raises(HTTPException) as failure:
        AdmissionsRepository(Workspace(cursor)).applicants(3, "", 0)
    assert failure.value.status_code == 404
    assert len(cursor.calls) == 1


@pytest.mark.parametrize(
    "document,known,matched",
    [(" 0012-A ", True, True), ("  ", True, False), ("0012", False, False)],
)
def test_matching_uses_exact_type_and_trimmed_doc_across_all_periods(
    document, known, matched
):
    identity = {"document": document, "documentTypeId": 2, "identityTypeKnown": known}
    sets = [[{"id": 12, "periodId": 3, "offerId": None}], [identity]]
    if matched:
        sets.append([{"id": 41, "periodId": 1}])
    sets.append([])
    cursor = ReadCursor(sets)
    result = AdmissionsRepository(Workspace(cursor)).detail(12, 3)
    queries = [
        (sql, args) for sql, args in cursor.calls if "FROM dbo.GEEstudiante e" in sql
    ]
    assert result["matchingAvailable"] is matched
    if matched:
        sql, args = queries[0]
        assert args == (2, "0012-A", 0)
        assert "WHERE e.TipoId=?" in sql
        assert "Latin1_General_100_BIN2" in sql
        assert "o.Id_Periodo=?" not in sql and "e.Id_Periodo=?" not in sql
        assert result["matches"]["items"][0]["periodId"] == 1
    else:
        assert not queries


def test_detail_rejects_stale_period_before_reading_person():
    cursor = ReadCursor([[]])
    with pytest.raises(HTTPException) as failure:
        AdmissionsRepository(Workspace(cursor)).detail(12, 3)
    assert failure.value.status_code == 404
    assert len(cursor.calls) == 1


def test_document_normalization_preserves_identity_significant_characters():
    assert document_key(" 0012-A ") == "0012-A"
    assert document_key("1.234") != document_key("1234")
    assert document_key("0012") != document_key("12")


class WriteCursor:
    def __init__(self):
        self.data = {"cases": {}, "followups": {}, "operations": {}}
        self.result = None
        self.fail_operation = False
        self.calls = []

    def execute(self, sql, *args):
        self.calls.append((sql, args))
        self.result = None
        if "SELECT Id_Aspirante" in sql or "SELECT Id_EstadoSeguimiento" in sql:
            self.result = (args[0],)
        elif "SELECT PayloadHash" in sql:
            digest = self.data["operations"].get(args[0])
            self.result = (digest,) if digest else None
        elif "SELECT CaseId" in sql:
            case = self.data["cases"].get(args[0])
            self.result = (case,) if case else None
        elif "SELECT FollowupId" in sql:
            self.result = (args[0],) if args[0] in self.data["followups"] else None
        elif "SELECT f.Revision" in sql:
            item = self.data["followups"].get(args[0])
            self.result = (
                (item["revision"],)
                if item and item["case"] == self.data["cases"].get(args[1])
                else None
            )
        elif sql.startswith("INSERT crm_admissions.AdmissionCase"):
            self.data["cases"][args[1]] = args[0]
        elif sql.startswith("INSERT crm_admissions.Followup"):
            self.data["followups"][args[0]] = {
                "case": args[1],
                "body": args[2],
                "revision": 1,
            }
        elif sql.startswith("UPDATE crm_admissions.Followup"):
            item = self.data["followups"][args[-1]]
            item["body"] = args[0]
            item["revision"] += 1
        elif sql.startswith("INSERT crm_admissions.Operation"):
            if self.fail_operation:
                raise RuntimeError("injected audit failure")
            self.data["operations"][args[0]] = args[-1]
        return self

    def fetchone(self):
        return self.result


@pytest.fixture
def writer(monkeypatch):
    cursor = WriteCursor()
    workspace = Workspace(cursor)
    repository = AdmissionsRepository(workspace)
    monkeypatch.setattr(repository, "verify_followups", lambda cursor: None)
    monkeypatch.setattr(
        repository,
        "read_followups",
        lambda cursor, applicant: deepcopy(cursor.data["followups"]),
    )
    return repository, workspace, cursor


def body(**changes):
    return FollowupWrite.model_validate(
        {
            "operationId": str(uuid4()),
            "expectedRevision": 0,
            "body": "Test note",
            "stateId": 1,
            "dueDate": None,
            **changes,
        }
    )


def test_case_followup_and_operation_commit_atomically_and_retry_dedupes(writer):
    repository, workspace, cursor = writer
    value, identifier = body(), str(uuid4())
    first = repository.save_followup(12, 3, identifier, value, True)
    assert repository.save_followup(12, 3, identifier, value, True) == first
    assert [len(cursor.data[key]) for key in ("cases", "followups", "operations")] == [
        1,
        1,
        1,
    ]
    assert workspace.commits == 2
    assert all(
        not sql.startswith(("INSERT dbo.", "UPDATE dbo.", "INSERT crm."))
        for sql, _ in cursor.calls
    )


def test_failed_operation_rolls_back_case_and_note(writer):
    repository, workspace, cursor = writer
    cursor.fail_operation = True
    with pytest.raises(RuntimeError):
        repository.save_followup(12, 3, str(uuid4()), body(), True)
    assert workspace.rollbacks == 1
    assert not any(cursor.data.values())


def test_edit_conflict_and_retry_are_safe(writer):
    repository, workspace, cursor = writer
    identifier = str(uuid4())
    repository.save_followup(12, 3, identifier, body(), True)
    edit = body(expectedRevision=1, body="Changed")
    repository.save_followup(12, 3, identifier, edit, False)
    repository.save_followup(12, 3, identifier, edit, False)
    assert cursor.data["followups"][identifier]["revision"] == 2
    with pytest.raises(HTTPException) as failure:
        repository.save_followup(12, 3, identifier, body(expectedRevision=1), False)
    assert failure.value.status_code == 409
    assert cursor.data["followups"][identifier]["body"] == "Changed"


def test_operation_identity_cannot_be_reused_for_other_payload(writer):
    repository, _, _ = writer
    value, identifier = body(), str(uuid4())
    repository.save_followup(12, 3, identifier, value, True)
    with pytest.raises(HTTPException) as failure:
        repository.save_followup(
            12,
            3,
            identifier,
            body(operationId=value.operationId, body="Different"),
            True,
        )
    assert failure.value.detail == "operation_changed"


@pytest.mark.parametrize(
    "change",
    [
        {"body": "  "},
        {"dueDate": "2026-02-30"},
        {"expectedRevision": -1},
        {"stateId": 0},
    ],
)
def test_invalid_followup_fails_before_database(change):
    with pytest.raises(ValidationError):
        body(**change)


def test_sql_runtime_has_no_legacy_fixture_router_and_requires_period(monkeypatch):
    monkeypatch.setattr(
        Settings, "from_environment", lambda: Settings(mode="local_sql_copy")
    )
    app = create_app()
    assert not any(
        path.startswith("/api/local/clients") for path in app.openapi()["paths"]
    )
    client = TestClient(app, base_url="http://127.0.0.1:8002", client=("127.0.0.1", 10))
    assert client.get("/api/local/admissions/periods").status_code == 403
    response = client.get(
        "/api/local/admissions/applicants", headers={"X-CRM-Local": "1"}
    )
    assert response.status_code == 422
    assert response.json() == {"code": "invalid_request"}


def test_page_does_not_confuse_full_page_with_has_more():
    assert not page(list(range(25)), 0)["hasMore"]
    assert page(list(range(26)), 0)["hasMore"]
