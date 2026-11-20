from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.institutional import sales_contact as contacts, sales_memory


@pytest.mark.parametrize("body,item,previous,expected", [
    ("Mi nombre es Juan Pablo", {"field":"name","quote":"Mi nombre es Juan Pablo","value":"Juan Pablo"}, "", "Juan Pablo"),
    ("Juan Pablo", {"field":"name","quote":"Juan Pablo","value":"Juan Pablo"}, "¿Cómo te llamas?", "Juan Pablo"),
    ("Juan Pablo", {"field":"name","quote":"Juan Pablo","value":"Juan Pablo"}, "¿Qué programa te interesa?", None),
    ("Mi hermano se llama Carlos", {"field":"name","quote":"Mi hermano se llama Carlos","value":"Carlos"}, "", None),
    ("Me llamo Juan", {"field":"name","quote":"Me llamo Juan","value":"Pedro"}, "", None),
    ("Vivo en Barranquilla", {"field":"city","quote":"Vivo en Barranquilla","value":"Barranquilla"}, "", "Barranquilla"),
    ("Mi documento es123", {"field":"document","quote":"Mi documento es123","value":"123"}, "", None),
])
def test_only_exact_customer_declarations_can_project_display_fields(body, item, previous, expected):
    assert contacts.declared_value(item, {"Body":body}, previous) == expected


def test_name_sanitizing_does_not_turn_placeholders_or_numbers_into_a_person():
    assert contacts.display_name("Carlos 👻") == "Carlos"
    assert contacts.display_name("Contacto de Messenger") is None
    assert contacts.display_name("573001234567") is None
    assert contacts.display_name("DM sender") is None


def test_name_projection_has_provenance_and_does_not_invalidate_its_own_context(monkeypatch):
    conversation, contact, incoming = [str(uuid4()) for _ in range(3)]
    person = {"ContactId":contact,"Name":"Contacto de WhatsApp","City":"","Schedule":"","Interests":""}
    state = {"fields":{}}
    saved, sql, audits = [], [], []
    class Cursor:
        rowcount = 1
        def execute(self, query, *args):
            sql.append((query,args))
            if query.startswith("UPDATE crm.Contact SET Name="):
                person["Name"] = args[0]
            return self
    c = Cursor()
    monkeypatch.setattr(contacts,"contact",lambda *_:person)
    monkeypatch.setattr(contacts,"read",lambda *_:(state, len(saved)))
    monkeypatch.setattr(contacts,"save",lambda *args:saved.append(args[3].copy()))
    monkeypatch.setattr(contacts.db,"one",lambda *_:None)
    monkeypatch.setattr(contacts.db,"institution",lambda *_:"institution")
    monkeypatch.setattr(contacts.db,"audit",lambda *args,**kwargs:audits.append(kwargs))
    before = contacts.personalization(c,None,conversation,9)
    fact = {"field":"name","declared_value":"Carlos","source_message_id":incoming,"origin":"customer_quote"}
    result = contacts.project(c,None,{"conversation":conversation},[fact],{"Sequence":9})
    assert result[0]["state"] == "updated" and person["Name"] == "Carlos"
    assert contacts.personalization(c,None,conversation,9) == before
    assert contacts.personalization(c,None,conversation,10)["display_name"] == "Carlos"
    assert state["fields"]["name"]["source_message_id"] == incoming
    assert audits[0]["fields"] == ["name"]
    assert any("crm_workspace.State" in query for query,_ in sql)


def test_manual_name_is_preserved_and_corrections_stay_available_as_memory(monkeypatch):
    person = {"ContactId":str(uuid4()),"Name":"Carlos","City":"","Schedule":"","Interests":""}
    monkeypatch.setattr(contacts,"contact",lambda *_:person)
    monkeypatch.setattr(contacts,"read",lambda *_:({"fields":{"name":{"authority":"manual","value":"Carlos"}}},2))
    monkeypatch.setattr(contacts,"save",lambda *_:pytest.fail("No write to protected name"))
    c = SimpleNamespace(execute=lambda *_:pytest.fail("No SQL update"))
    incoming = {"Body":"Me llamo Juan Pablo","MessageId":str(uuid4()),"Sequence":3}
    facts = sales_memory.validated([{"field":"name","quote":"Me llamo Juan Pablo","value":"Juan Pablo"}],incoming)
    result = contacts.project(c,None,{"conversation":str(uuid4())},facts,incoming)
    assert result[0]["state"] == "manual_preserved" and facts[0]["declared_value"] == "Juan Pablo"


def test_manual_edits_protect_only_fields_that_changed(monkeypatch):
    state = {"fields":{"name":{"authority":"customer_declared_automatic","value":"Carlos"}}}
    saved = []
    monkeypatch.setattr(contacts,"read",lambda *_:(state,1))
    monkeypatch.setattr(contacts,"save",lambda *args:saved.append(args[3]))
    previous = {"name":"Carlos","city":"","schedule":"","interests":""}
    contacts.mark_manual(None,None,str(uuid4()),previous,SimpleNamespace(**{**previous,"city":"Bogotá"}))
    assert saved[0]["fields"]["name"]["authority"] == "customer_declared_automatic"
    assert saved[0]["fields"]["city"]["authority"] == "manual"
