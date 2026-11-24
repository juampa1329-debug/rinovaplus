import json
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pglast import parse_sql

from app.institutional import masterclass_interests as master, grounded_replies as grounding
from app.institutional.api import core_permission
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql

PROGRAMS = [
    {"program_id": 1, "name": "SERVICIOS HOTELEROS Y AGENCIAS TURISTICAS", "school": "TURISMO", "schedule": "DIURNA"},
    {"program_id": 2, "name": "AUXILIAR EN ENFERMERIA", "school": "SALUD", "schedule": "DIURNA"},
    {"program_id": 3, "name": "AUXILIAR EN SALUD ORAL", "school": "SALUD", "schedule": "DIURNA"},
    {"program_id": 4, "name": "DESARROLLO DE SOFTWARE", "school": "TIC", "schedule": "DIURNA"},
    {"program_id": 5, "name": "COCINA NACIONAL E INTERNACIONAL", "school": "GASTRONOMIA", "schedule": "DIURNA"},
    {"program_id": 6, "name": "REPOSTERIA Y PASTELERIA", "school": "GASTRONOMIA", "schedule": "DIURNA"},
    {"program_id": 7, "name": "BARISMO Y BARTENDER", "school": "GASTRONOMIA", "schedule": "DIURNA"},
    {"program_id": 8, "name": "PROEFICIENCIA EN INGLES", "school": "IDIOMAS", "schedule": "DIURNA"},
    {"program_id": 9, "name": "MASTERCLASS SALUD", "school": "SALUD", "schedule": "DIURNA"},
    {"program_id": 10, "name": "LOGISTICA PORTUARIA Y MARITIMA", "school": "LOGISTICA", "schedule": "DIURNA"},
    {"program_id": 11, "name": "ADUANAS Y PROCESOS LOGISTICOS", "school": "LOGISTICA", "schedule": "NOCTURNA"},
    {"program_id": 12, "name": "BARTENDER", "school": "GASTRONOMIA", "schedule": "DIURNA"},
]


def person(text):
    return {"ContactId": str(uuid4()), "Interests": text, "CustomValues": '{"pre_programas":"Original intacto"}'}


@pytest.mark.parametrize("source,ids", [("MASTERCLASS TURISMO", [1]), ("Master class Salud", [2, 3]),
    ("MASTERCLASS TIC", [4]), ("MASTERCLASS GASTRONOMÍA", [5, 6, 7]),
    ("MASTERCLASS EL MUNDO DE LOS CUPCAKES", [6]), ("MASTERCLASS EL ARTE DEL CAFÉ", [7]),
    ("MASTERCLASS COCINA NAVIDEÑA", [5]), ("MASTERCLASS CENTRO IDIOMAS", [8]),
    ("MASTERCLASS EL SECRETO DE LA PASTA ARTESANAL ITALIANA", [5]),
    ("MASTERCLASS SABORES DE LATINOAMÉRICA", [5]), ("MASTERCLASS LOGISTICA", [10]), ("MASTERCLASS ADUANAS", [11])])
def test_related_programs_follow_specific_topic_or_whole_school_without_selecting_schedule(source, ids):
    plan = master.proposal(person(source), PROGRAMS)
    assert not plan["reason"]
    assert [p["program_id"] for p in plan["programs"]] == ids
    assert plan["original_masterclasses"] == [source]


def test_unrelated_interests_and_original_import_are_preserved_and_unknown_topics_are_held():
    value = person("Inglés | MASTERCLASS TURISMO")
    plan = master.proposal(value, PROGRAMS)
    assert plan["interests"].startswith("Inglés | SERVICIOS HOTELEROS")
    assert value["CustomValues"] == '{"pre_programas":"Original intacto"}'
    assert master.proposal(person("Ahora prefiero Software"), PROGRAMS) is None
    assert master.proposal(person("MASTERCLASS ASTRONOMIA"), PROGRAMS)["reason"]
    oversized = [dict(PROGRAMS[2], program_id=n, name=str(n) + "X" * 95) for n in range(20, 25)]
    assert "300" in master.proposal(person("MASTERCLASS SALUD"), oversized)["reason"]


def test_preview_is_read_only_and_returns_signed_plans_without_contact_names(monkeypatch):
    cursor = SimpleNamespace()
    @contextmanager
    def tx(settings, write, **kwargs):
        assert not write and kwargs["permission"] == "crm.read"
        yield cursor
    monkeypatch.setattr(master, "transaction", tx)
    monkeypatch.setattr(master, "authorize", lambda *_: {})
    monkeypatch.setattr(master, "contact_rows", lambda *_: [person("MASTERCLASS SALUD"), person("MASTERCLASS DESCONOCIDA")])
    monkeypatch.setattr(master, "catalog", lambda *_: PROGRAMS)
    monkeypatch.setattr(master, "signature", lambda *_: "a" * 64)
    result = master.preview(None)
    assert result["ready"] == 1 and result["review"] == 1
    assert set(result["items"][0]) == {"contact_id", "signature"}
    assert result["groups"][0]["programs"] == [PROGRAMS[1]["name"], PROGRAMS[2]["name"]]


@pytest.mark.parametrize("replay,stale", [(False, False), (True, False), (False, True)])
def test_apply_is_idempotent_bound_to_preview_and_never_changes_program_or_consent(monkeypatch, replay, stale):
    value, sqls, saved, receipts = person("MASTERCLASS TURISMO"), [], [], []
    class Cursor:
        rowcount = 1
        def execute(self, sql, *params):
            parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
            sqls.append((sql, params))
            return self
    @contextmanager
    def tx(settings, write, **kwargs):
        assert write and kwargs["permission"] == "crm.write"
        yield Cursor()
    monkeypatch.setattr(master, "transaction", tx)
    monkeypatch.setattr(master, "authorize", lambda *_: {"UserId": str(uuid4())})
    monkeypatch.setattr(master, "contact_rows", lambda *_: [value])
    monkeypatch.setattr(master, "catalog", lambda *_: PROGRAMS)
    monkeypatch.setattr(master, "signature", lambda *_: ("b" if stale else "a") * 64)
    monkeypatch.setattr(master.db, "replay", lambda *_: (b"digest", {"updated": 1} if replay else None))
    monkeypatch.setattr(master.db, "record_operation", lambda *args: receipts.append(args))
    monkeypatch.setattr(master.db, "audit", lambda *_args, **_kw: None)
    monkeypatch.setattr(master.db, "institution", lambda _: str(uuid4()))
    monkeypatch.setattr(master.sales_contact, "read", lambda *_: ({"fields": {}}, 0))
    monkeypatch.setattr(master.sales_contact, "save", lambda *args: saved.append(args[-2]))
    body = master.Apply(operation_id=str(uuid4()), items=[{"contact_id": value["ContactId"], "signature": "a" * 64}])
    if stale:
        with pytest.raises(HTTPException, match="masterclass_preview_changed"):
            master.apply(None, body)
        assert not sqls
        return
    assert master.apply(None, body)["updated"] == 1
    if replay:
        assert not sqls and not saved
    else:
        assert saved[0]["masterclass_orientation"]["customer_choice"] is False
        assert saved[0]["fields"]["interests"]["authority"] == master.AUTHORITY
        assert any("UPDATE crm.Contact SET Interests=" in sql for sql, _ in sqls)
        assert not any(any(t in sql for t in ("SET Program", "SET ControlMode", "Consent", "INSERT crm.Message", "SIIE")) for sql, _ in sqls)
        assert receipts


@pytest.mark.parametrize("public", [False, True])
def test_related_program_suggestions_are_available_privately_but_are_not_customer_choices(monkeypatch, public):
    queries = []
    monkeypatch.setattr(grounding, "setting", lambda *_: {"revision": 1, "document": {}})
    monkeypatch.setattr(grounding, "Catalog", lambda *_: SimpleNamespace(read_context=lambda _, q, p: queries.append(q) or {"material": {}}))
    monkeypatch.setattr(grounding, "search", lambda *_: [])
    monkeypatch.setattr(grounding, "effective", lambda *_: {"shared": []})
    suggested = {"authority": master.AUTHORITY, "programs": PROGRAMS[1:3], "customer_choice": False}
    reply = grounding.context(None, SimpleNamespace(), "Quiero información", public=public,
                              selection={"configuration": {}, "masterclass_orientation": suggested})
    payload = json.loads(reply["query"])
    assert ("opciones_relacionadas_masterclass" in payload) is not public
    assert (master.POLICY in reply["system"]) is not public
    assert (PROGRAMS[1]["name"] in queries[-1]) is not public


def test_routes_retain_crm_read_write_permissions():
    assert core_permission("/api/institution/workspace/masterclass-interests/preview", "GET") == ("crm.read", "clients")
    assert core_permission("/api/institution/workspace/masterclass-interests/apply", "POST") == ("crm.write", "clients")
