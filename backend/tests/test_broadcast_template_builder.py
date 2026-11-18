import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.institutional import broadcast_templates as templates
from app.institutional.broadcast_models import TemplateWrite, Variable
from app.institutional.broadcast_models import TemplateSample
from app.institutional import broadcast_sample
from app.institutional.broadcast_variables import bindings, catalog


def draft(**extra):
    values = dict(operation_id=uuid4(), reason="Revisión", name="prueba_cbn",
                  body_text="Hola {{customer_name}}, conoce {{program}}.")
    return TemplateWrite(**dict(values, **extra))


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


def test_standard_meta_buttons_support_ten_and_enforce_grouping():
    quick = {"type": "QUICK_REPLY", "text": "Confirmar"}
    link = {"type": "URL", "text": "Ver detalle", "url": "https://cbn.example/solicitud"}
    assert len(templates.definition(draft(buttons=[quick] * 10))[-1]["buttons"]) == 10
    with pytest.raises(ValidationError):
        draft(buttons=[quick] * 11)
    with pytest.raises(HTTPException, match="template_button_type_limit"):
        templates.definition(draft(buttons=[link] * 3))
    with pytest.raises(HTTPException, match="template_button_grouping_invalid"):
        templates.definition(draft(buttons=[quick, link, quick]))
    assert len(templates.definition(draft(buttons=[quick, quick, link]))[-1]["buttons"]) == 3


@pytest.mark.parametrize("url", ["https://cbn.example/{{1}}/detalle", "https://cbn.example/{{2}}/{{1}}", "https://cbn.example/{{nombre}}"])
def test_dynamic_url_is_one_final_parameter(url):
    with pytest.raises(HTTPException, match="template_button_url_variable_invalid"):
        templates.definition(draft(buttons=[{"type":"URL","text":"Ver","url":url,"url_example":"ejemplo"}]))


def test_dynamic_url_requires_sample_and_encodes_its_crm_value():
    button={"type":"URL","text":"Ver","url":"https://cbn.example/solicitud/{{1}}"}
    with pytest.raises(HTTPException, match="template_button_url_example_required"):
        templates.definition(draft(buttons=[button]))
    definition=templates.definition(draft(body_text="Solicitud disponible",buttons=[dict(button,url_example="codigo_ficticio")]))
    assert definition[-1]["buttons"][0]["example"]==["codigo_ficticio"]
    template={"Definition":json.dumps(definition),"Name":"test","Language":"es"}
    person={"Name":"Ana", "CustomValues":"{}", "City":"", "Phone":"", "Program":"", "Stage":"", "Schedule":""}
    result,_=templates.parameters(template,{"variables":{"button.0.1":{"source":"literal","value":"Ana & CBN/á"}}},person,"Prueba")
    assert result["components"][0]["parameters"][0]["text"]=="Ana%20%26%20CBN%2F%C3%A1"


def test_sample_inspector_accepts_png_and_cleans_temporary_files(tmp_path,monkeypatch):
    import base64
    import io
    from PIL import Image
    from app.modules.inbox.infrastructure import media_files
    monkeypatch.setattr(media_files,"root",lambda:tmp_path)
    stream=io.BytesIO()
    Image.new("RGB",(32,32),(18,52,59)).save(stream,format="PNG")
    body=TemplateSample(operation_id=uuid4(),reason="Muestra",filename="muestra.png",kind="image",content_base64=base64.b64encode(stream.getvalue()).decode(),confirmed=True)
    data,info=broadcast_sample.checked(body)
    assert data.startswith(b"\x89PNG") and info["mime"]=="image/png"
    assert not list(tmp_path.iterdir())
    with pytest.raises(HTTPException,match="template_sample_format_invalid"):
        broadcast_sample.checked(body.model_copy(update={"kind":"document"}))
    assert not list(tmp_path.iterdir())


def test_meta_resumable_upload_sends_binary_and_token_only_in_authorization(monkeypatch):
    import httpx2
    calls=[]
    def start(adapter,method,path,params):
        assert (method,path)==("POST","123/uploads")
        assert params=={"file_name":"muestra.png","file_length":3,"file_type":"image/png"}
        return {"id":"upload:opaque?sig=signed"}
    def binary(request):
        assert request.url.host=="graph.facebook.com" and request.url.path=="/v27.0/upload:opaque"
        assert request.headers["Authorization"]=="OAuth fixture-private-token"
        assert request.headers["file_offset"]=="0" and request.content==b"png"
        assert "fixture-private-token" not in str(request.url)
        return httpx2.Response(200,json={"h":"4::sample-handle"})
    client=httpx2.Client
    monkeypatch.setattr(broadcast_sample.providers,"request",start)
    monkeypatch.setattr(broadcast_sample.httpx,"Client",lambda **kw:client(transport=httpx2.MockTransport(binary),**kw))
    adapter={"channel":"whatsapp","configuration":{"appId":"123","apiVersion":"v27.0"},"secrets":{"accessToken":"fixture-private-token"}}
    assert broadcast_sample.graph_upload(adapter,b"png",{"name":"muestra.png","mime":"image/png"},lambda:calls.append("context"))=="4::sample-handle"
    assert calls==["context","context"]


@pytest.mark.parametrize("session",["https://evil.example/", "upload:../../other", "upload:x#fragment", "upload:x\r\nAuthorization: bad"])
def test_sample_session_cannot_redirect_or_inject_a_header(monkeypatch,session):
    monkeypatch.setattr(broadcast_sample.providers,"request",lambda *a,**kw:{"id":session})
    monkeypatch.setattr(broadcast_sample.httpx,"Client",lambda **kw:pytest.fail("Invalid session must not reach upload"))
    adapter={"channel":"whatsapp","configuration":{"appId":"123","apiVersion":"v27.0"},"secrets":{"accessToken":"synthetic"}}
    with pytest.raises(broadcast_sample.providers.ProviderFailure) as error:
        broadcast_sample.graph_upload(adapter,b"png",{"name":"muestra.png","mime":"image/png"},lambda:None)
    assert error.value.code=="template_sample_session_invalid" and error.value.uncertain


def test_sample_upload_requires_explicit_confirmation_before_auth_or_io():
    body=TemplateSample(operation_id=uuid4(),reason="Muestra",filename="image.png",kind="image",content_base64="eA==")
    with pytest.raises(HTTPException,match="template_sample_confirmation_required"):
        broadcast_sample.upload(None,{},str(uuid4()),body)


def test_campaign_media_is_uploaded_to_its_phone_and_is_never_a_template_handle(monkeypatch):
    calls=[]
    def request(adapter,method,path,files):
        assert (method,path)==("POST","987/media")
        assert files[0]==("messaging_product",(None,"whatsapp"))
        assert files[2]==("file",("image.png",b"png","image/png"))
        return {"id":"123456"}
    monkeypatch.setattr(broadcast_sample.providers,"request",request)
    assert broadcast_sample.phone_upload({"channel":"whatsapp","configuration":{"phoneNumberId":"987"}},b"png",{"name":"image.png","mime":"image/png"},lambda:calls.append(1))=="123456"
    assert calls==[1]
    template={"Name":"test","Language":"es","Definition":json.dumps([{"type":"HEADER","format":"IMAGE"},{"type":"BODY","text":"Archivo solicitado"}])}
    person={"Name":"Ana", "CustomValues":"{}", "City":"", "Phone":"", "Program":"", "Stage":"", "Schedule":""}
    result,_=templates.parameters(template,{"header_media_id":"123456","variables":{}},person,"Prueba")
    assert result["components"][0]["parameters"]==[{"type":"image","image":{"id":"123456"}}]


@pytest.mark.parametrize("fault",[None,"account_version","credential","media_id","purpose","kind","absent"])
def test_campaign_media_requires_current_confirmed_account_scoped_upload(monkeypatch,fault):
    integration,operation,secret=str(uuid4()),str(uuid4()),str(uuid4())
    item={"IntegrationId":integration,"RowVersion":b"12345678"}
    campaign={"Document":json.dumps({"header_media_id":"123456","header_media_operation":operation})}
    metadata={"media_id":"123456","purpose":"delivery","kind":"image","account_version":item["RowVersion"].hex(),"credential":secret}
    if fault:metadata[fault]="changed"
    def one(c,query,*params):
        assert "Status='confirmed'" in query and params[1:]==(integration,operation)
        return None if fault=="absent" else {"ResultMetadata":json.dumps(metadata)}
    monkeypatch.setattr(broadcast_sample,"one",one)
    monkeypatch.setattr(broadcast_sample,"institution",lambda s:"institution")
    args=(None,None,campaign,item,{"SecretId":secret},json.dumps([{"type":"HEADER","format":"IMAGE"}]))
    if fault:
        with pytest.raises(HTTPException,match="broadcast_media_upload_required"):
            broadcast_sample.delivery_binding(*args)
    else:
        broadcast_sample.delivery_binding(*args)


@pytest.mark.parametrize("context_changes",[False,True])
def test_sample_intent_replays_without_io_and_changed_context_cannot_return_handle(monkeypatch,context_changes):
    from contextlib import nullcontext
    item={"Channel":"whatsapp","RequestedStatus":"connected","VerifiedStatus":"verified","RowVersion":b"12345678","ApplicationId":str(uuid4())}
    state={"prior":None,"calls":0}
    class Cursor:
        rowcount=1
        def execute(self,query,*params):
            if query.startswith("INSERT"):
                state["prior"]={"RequestDigest":params[5],"Status":"running","ResultMetadata":"{}"}
            else:
                state["prior"].update(Status=params[0],ResultMetadata=params[2])
            return self
    cursor=Cursor()
    service=SimpleNamespace(settings=None,tx=lambda *a,**kw:nullcontext((cursor,{"UserId":"owner"})))
    monkeypatch.setattr(broadcast_sample,"account",lambda *a:item)
    monkeypatch.setattr(broadcast_sample,"checked",lambda body:(b"png",{"name":"image.png","mime":"image/png"}))
    monkeypatch.setattr(broadcast_sample,"provider_account",lambda *a:({}, {"SecretId":"credential"}))
    monkeypatch.setattr(broadcast_sample,"bound_hash",lambda *a:b"digest")
    monkeypatch.setattr(broadcast_sample,"institution",lambda *a:"institution")
    monkeypatch.setattr(broadcast_sample,"one",lambda *a:state["prior"])
    def send(adapter,data,info,current):
        state["calls"]+=1
        current()
        if context_changes:item["RequestedStatus"]="paused"
        current()
        return "4::handle"
    body=TemplateSample(operation_id=uuid4(),reason="Muestra",filename="image.png",kind="image",content_base64="eA==",confirmed=True)
    integration=str(uuid4())
    result=broadcast_sample.upload(service,{},integration,body,send)
    assert result["status"]==("failed" if context_changes else "confirmed")
    if context_changes:
        assert "handle" not in result and result["code"]=="broadcast_context_changed"
    else:
        assert broadcast_sample.upload(service,{},integration,body,send)==result
    assert state["calls"]==1


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
