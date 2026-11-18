import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.institutional import broadcast_templates as templates
from app.institutional.broadcast_models import TemplateWrite, Variable
from app.institutional.broadcast_variables import bindings, catalog


def draft(**extra):
    return TemplateWrite(operation_id=uuid4(), reason="Revisión", name="prueba_cbn",
                         body_text="Hola {{customer_name}}, conoce {{program}}.", **extra)


def test_crm_catalog_and_repeated_named_tokens_preserve_their_source():
    fields = [SimpleNamespace(key="sede", label="Sede", type="Text", active=True),
              SimpleNamespace(key="retirado", label="Retirado", type="Text", active=False)]
    variables = catalog(fields)
    assert "crm.sede" in {v["token"] for v in variables}
    assert "crm.retirado" not in {v["token"] for v in variables}
    result = bindings([{"type":"BODY", "text":"{{customer_name}} {{crm.sede}} {{customer_name}}"}], variables, templates.TOKEN)
    assert result == {"body.1":{"source":"customer_name"}, "body.2":{"source":"custom_field","field_key":"sede"}}
    with pytest.raises(HTTPException, match="broadcast_crm_variable_unknown"):
        bindings([{"type":"BODY","text":"{{crm.retirado}}"}], variables, templates.TOKEN)


def test_meta_receives_numeric_slots_and_explicit_synthetic_examples():
    result = templates.definition(draft(examples={"body.1":"Laura", "body.2":"Programa de ejemplo"}))
    assert result[0] == {"type":"BODY", "text":"Hola {{1}}, conoce {{2}}.",
                         "example":{"body_text":[["Laura", "Programa de ejemplo"]]}}


@pytest.mark.parametrize("extra,code", [
    ({"header_type":"TEXT","header_text":"{{customer_name}} {{stage}}"}, "template_header_one_variable"),
    ({"footer_text":"{{customer_name}}"}, "template_footer_variables_unsupported"),
    ({"examples":{"body.3":"No corresponde"}}, "template_example_unused"),
])
def test_invalid_meta_structure_is_rejected_before_request(extra, code):
    with pytest.raises(HTTPException, match=code):
        templates.definition(draft(**extra))


@pytest.mark.parametrize("value,rendered", [(0,"0"), (False,"No"), (True,"Sí"), ("Cartagena","Cartagena")])
def test_custom_crm_fields_are_explicit_and_preserve_zero_and_boolean(value, rendered):
    template = {"Definition":json.dumps([{"type":"BODY","text":"Dato: {{1}}."}]),"Name":"prueba_cbn","Language":"es"}
    document = {"variables":{"body.1":{"source":"custom_field","field_key":"sede"}}}
    person = {"Name":"Ana", "CustomValues":json.dumps({"sede":value}), "City":"", "Phone":"", "Program":"", "Stage":"", "Schedule":""}
    _, text = templates.parameters(template, document, person, "Prueba", allowed_custom_fields={"sede"})
    assert text == f"Dato: {rendered}."
    with pytest.raises(HTTPException, match="broadcast_crm_field_unavailable"):
        templates.parameters(template, document, person, "Prueba", allowed_custom_fields=set())


def test_custom_binding_cannot_fall_back_to_another_unreviewed_field():
    with pytest.raises(ValidationError):
        Variable(source="custom_field")
    with pytest.raises(ValidationError):
        Variable(source="customer_name", field_key="sede")


@pytest.mark.parametrize("changed", [False, True])
def test_provider_sync_preserves_crm_mapping_only_for_unchanged_content(monkeypatch, changed):
    components = [{"type":"BODY","text":"Hola {{1}}.","example":{"body_text":[["Ana"]]}}]
    old = {"TemplateId":str(uuid4()), "VersionNo":1, "Paused":False, "Definition":json.dumps(components),
           "ProviderMetadata":json.dumps({"variable_bindings":{"body.1":{"source":"customer_name"}}})}
    monkeypatch.setattr(templates, "one", lambda *args: old)
    monkeypatch.setattr(templates, "institution", lambda _: "institution")
    captured = []
    class Cursor:
        def execute(self, sql, *values):
            captured.append(values)
    raw = {"id":"123", "name":"prueba_cbn", "language":"es", "category":"UTILITY", "status":"APPROVED",
           "components":[{"type":"BODY","text":"Nuevo {{1}}." if changed else "Hola {{1}}."}],
           "quality_score":{"score":"UNKNOWN","date":1},"rejected_reason":"NONE"}
    templates.append(Cursor(), None, {"IntegrationId":str(uuid4()),"RowVersion":b"12345678"},raw,{"SecretId":str(uuid4())},"provider")
    metadata = json.loads(captured[0][12])
    assert metadata["quality_score"] == "UNKNOWN" and metadata["rejection_reason"] == ""
    assert metadata["variable_bindings"] == ({} if changed else {"body.1":{"source":"customer_name"}})


def test_Meta_component_reordering_preserves_bindings_but_button_order_is_significant():
    body={"type":"BODY","text":"Hola {{1}}"}
    header={"type":"HEADER","format":"TEXT","text":"CBN"}
    assert templates.binding_content([body,header]) == templates.binding_content([header,body])
    buttons={"type":"BUTTONS","buttons":[{"type":"QUICK_REPLY","text":"Uno"},{"type":"QUICK_REPLY","text":"Dos"}]}
    assert templates.binding_content([buttons]) != templates.binding_content([dict(buttons,buttons=list(reversed(buttons["buttons"])) )])


@pytest.mark.parametrize("content_changed",[False,True])
def test_sync_recovers_lost_bindings_append_only_without_crossing_content_changes(monkeypatch,content_changed):
    body={"type":"BODY","text":"Hola {{1}}"}
    header={"type":"HEADER","format":"TEXT","text":"CBN"}
    old={"TemplateId":str(uuid4()),"VersionNo":4,"Paused":False,"Definition":json.dumps([header,body]),"ProviderMetadata":"{}"}
    prior={"VersionNo":2,"Definition":json.dumps([body if not content_changed else dict(body,text="Otro {{1}}"),header]),"ProviderMetadata":json.dumps({"variable_bindings":{"body.1":{"source":"customer_first_name"}}})}
    monkeypatch.setattr(templates,"one",lambda *a:old)
    monkeypatch.setattr(templates,"rows",lambda *a:[prior])
    monkeypatch.setattr(templates,"institution",lambda *a:"institution")
    captured=[]
    cursor=SimpleNamespace(execute=lambda sql,*values:captured.append((sql,values)))
    templates.append(cursor,None,{"IntegrationId":str(uuid4()),"RowVersion":b"12345678"},{"id":"123","name":"test","language":"es","status":"APPROVED","components":[header,body]},{"SecretId":str(uuid4())},"provider")
    assert len(captured)==1 and captured[0][0].startswith("INSERT")
    metadata=json.loads(captured[0][1][12])
    assert metadata["variable_bindings"] == ({} if content_changed else {"body.1":{"source":"customer_first_name"}})
    assert metadata.get("binding_recovered_from_version") == (None if content_changed else 2)
