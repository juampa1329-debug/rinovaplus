import asyncio
import base64
import copy
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pglast import parse_sql

from app.institutional import channel_events, channel_media, grounded_replies, image_inputs, language_resilience, postgres_queue
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql
from app.modules.ai.infrastructure.providers import AiError


@pytest.mark.parametrize("channel,provider,expected", [
    ("whatsapp", {"type": "image", "image": {"id": "real-provider-id"}}, True),
    ("whatsapp", {"type": "image", "image": {}}, False),
    ("whatsapp", {"type": "image", "image": {"id": "valid", "caption": "No recibir mensajes"}}, False),
    ("instagram", {"message": {"attachments": [{"type": "image", "payload": {"url": "https://media.example/asset"}}]}}, True),
    ("messenger", {"message": {"attachments": [{"type": "image", "payload": {"url": "https://media.example/asset"}}]}}, True),
    ("instagram", {"message": {"attachments": None}}, False),
    ("messenger", {"message": {"attachments": [{"type": "image", "payload": {"url": "http://private.example"}}]}}, False),
    ("whatsapp", {"type": "reaction", "reaction": {"emoji": "❤️"}}, False),
    ("whatsapp", {"type": "unsupported", "id": "verified-id"}, True),
    ("whatsapp", {"type": "unsupported"}, False),
])
def test_authentic_image_messages_enter_reply_queue_without_turning_reactions_into_questions(channel, provider, expected):
    assert channel_events.replyable_message(channel, provider) is expected


def image_fixture(monkeypatch, tmp_path, *, state="ready", foreign=False, unavailable=False):
    inst, integration, identity, conversation, incoming, media = [str(uuid4()) for _ in range(6)]
    settings = SimpleNamespace(ticket={"context": [[1, inst]]})
    data = dict(integration=integration, identity=identity, conversation=conversation, incoming=incoming)
    raw = b"\x89PNG\r\n\x1a\nfixture"
    path = tmp_path / "private-image"
    path.write_bytes(raw)
    def rows(_c, sql, *params):
        assert params == (inst, integration, identity, conversation, incoming)
        parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
        return [dict(MediaId=media, MessageId=incoming, State=state)]
    def file_for(*_a, **kw):
        assert kw["conversation"] == conversation
        if unavailable:
            raise HTTPException(404, "media_not_found")
        return dict(MessageId=incoming, IntegrationId=str(uuid4()) if foreign else integration,
                    IdentityId=identity, ContentHash=b"verified-hash"), dict(mime="image/png", size=len(raw), path=path)
    monkeypatch.setattr(image_inputs.db, "rows", rows)
    monkeypatch.setattr(channel_media, "file_for", file_for)
    return settings, data, raw


def test_only_inspected_same_conversation_asset_is_forwarded_inline(monkeypatch, tmp_path):
    settings, data, raw = image_fixture(monkeypatch, tmp_path)
    images, evidence = image_inputs.for_turn(None, settings, data, {"incoming_ids": [data["incoming"]]})
    body = image_inputs.request_with_images(grounded_replies.request_body({"system": image_inputs.GUIDANCE, "query": "Consulta"}), images)
    assert evidence[0]["status"] == "ready" and "raw" not in evidence[0]
    parts = body["contents"][0]["parts"]
    assert base64.b64decode(parts[-1]["inlineData"]["data"]) == raw
    assert "https://" not in str(parts)
    assert "no confirma" in image_inputs.GUIDANCE


@pytest.mark.parametrize("kwargs", [{"foreign": True}, {"unavailable": True}])
def test_missing_or_cross_account_file_has_text_clarification_without_leaking_bytes(monkeypatch, tmp_path, kwargs):
    settings, data, _ = image_fixture(monkeypatch, tmp_path, **kwargs)
    images, evidence = image_inputs.for_turn(None, settings, data, None)
    assert not images and evidence[0]["status"] == "image_input_unavailable"
    assert "raw" not in evidence[0]


@pytest.mark.parametrize("state", ["pending", "processing"])
def test_worker_waits_for_existing_media_downloader_before_paid_inference(monkeypatch, tmp_path, state):
    settings, data, _ = image_fixture(monkeypatch, tmp_path, state=state)
    with pytest.raises(HTTPException, match="image_input_pending"):
        image_inputs.for_turn(None, settings, data, None)


def test_openrouter_image_request_preserves_grounded_json_contract_and_private_inline_bytes():
    raw = b"\x89PNG\r\n\x1a\nfixture"
    original = image_inputs.request_with_images(grounded_replies.request_body({"system": image_inputs.GUIDANCE, "query": "La captura del formulario"}), [{"mime": "image/png", "raw": raw}])
    body = copy.deepcopy(original)
    calls = []
    class Gateway:
        async def request(self, _provider, _method, _path, request):
            calls.append(request)
            return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"decision": "responder", "text": "Gracias por la captura; falta verificar el registro.", "crm_observations": []})}}]}
    result = asyncio.run(language_resilience.generate(Gateway(), {"provider": "openrouter", "model": "anthropic/fixture", "input_usd_per_million": 3, "output_usd_per_million": 15}, body, lambda: None))
    assert grounded_replies.parse(result).startswith("Gracias por la captura")
    outgoing = calls[0]
    assert outgoing["response_format"]["json_schema"]["strict"]
    assert isinstance(outgoing["messages"][0]["content"], str)
    content = outgoing["messages"][1]["content"]
    assert content[0]["type"] == "text" and content[-1]["type"] == "image_url"
    assert content[-1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert outgoing["provider"]["allow_fallbacks"] is False
    assert original == body and len(calls) == 1


def test_audio_or_arbitrary_remote_files_cannot_be_silently_sent_to_a_vision_route():
    for part in [{"fileData": {"fileUri": "https://private.example/id"}},
                 {"inlineData": {"mimeType": "audio/ogg", "data": "YWJj"}},
                 {"inlineData": {"mimeType": "image/png", "data": "!invalid"}}]:
        with pytest.raises(AiError):
            language_resilience.message_content({"role": "user", "parts": [part]})


def test_image_preflight_requires_vision_catalog_and_reserves_image_tokens_before_inference():
    from app.modules.ai.domain.models import ModelInfo

    body = image_inputs.request_with_images(grounded_replies.request_body({"system": "Fuentes", "query": "Consulta"}),
                                           [{"mime": "image/png", "raw": b"fixture"}])
    calls = []
    route = {"provider": "openrouter", "model": "fixture/model", "input_usd_per_million": 3, "output_usd_per_million": 15}
    class Gateway:
        catalog_details = {"openrouter": {"fixture/model": {"context_length": 100000,
            "supported_parameters": ["max_tokens", "response_format", "temperature"],
            "input_usd_per_million": 3, "output_usd_per_million": 15, "request_usd": 0}}}
        async def models(self, provider, **kwargs):
            calls.append((provider, kwargs))
            return [ModelInfo(id="fixture/model", name="Fixture", output_limit=4000)]
    incoming, _ = asyncio.run(language_resilience.compatible(Gateway(), route, body))
    assert calls == [("openrouter", {"account_catalog": True, "kind": "vision"})]
    assert incoming >= 32768


@pytest.mark.parametrize("claimed,renewed,expected", [(False, None, False), (True, True, True), (True, False, "send_lease_lost")])
def test_live_lease_extension_is_atomic_and_never_revives_an_expired_claim(claimed, renewed, expected):
    calls = []
    class Cursor:
        def native(self, sql, *params):
            parse_sql(sql.replace("%s", "NULL"))
            calls.append(sql)
            return SimpleNamespace(fetchval=lambda: claimed if len(calls) == 1 else renewed)
    if isinstance(expected, str):
        with pytest.raises(HTTPException, match=expected):
            postgres_queue.lease(Cursor(), *[str(uuid4()) for _ in range(4)])
    else:
        assert postgres_queue.lease(Cursor(), *[str(uuid4()) for _ in range(4)]) is expected
    if claimed:
        assert "interval '180 seconds'" in calls[1]
        assert "q.leaseuntil>" in calls[1] and "o.leaseuntil>" in calls[1]
        assert "o.leaseid=active.leaseid" in calls[1]
        assert "attempts=" not in calls[1] and "state='queued'" not in calls[1]
