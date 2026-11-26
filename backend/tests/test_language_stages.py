import copy
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.institutional import language_stages as stages, whatsapp_gemini as worker
from app.modules.agents.skill_policy import turn_plan, for_turn
from app.modules.ai.domain.resilience import LanguageResilience


def route(model):
    return {"provider": "openrouter", "model": model,
            "input_usd_per_million": 3.0, "output_usd_per_million": 15.0}


def document():
    return {"enabled": True, "primary": route("anthropic/commercial"),
            "opening": route("google/opening"), "opening_stage_keys": ["nuevo", "calificacion"],
            "routes": [route("anthropic/backup")], "reply_max_tokens": 4000}


@pytest.mark.parametrize("question,expected", [
    ("Hola, me interesa Barismo", "opening"),
    ("¿Cuánto dura y qué materias tiene?", "opening"),
    ("Quiero abrir mi negocio", "opening"),
    ("Hola, me parece caro", "commercial"),
    ("¿Cuánto es el abono y las cuotas?", "commercial"),
    ("Quiero inscribirme", "commercial"),
    ("Voy a revisar otras opciones", "commercial"),
    ("Te escribo después", "commercial"),
])
def test_current_need_overrides_early_stage(question, expected):
    policy = LanguageResilience.model_validate(document())
    selected, trace = stages.choose(policy, for_turn(question), {"key": "nuevo"})
    assert trace["route"] == expected
    assert selected.model == ("google/opening" if expected == "opening" else "anthropic/commercial")


@pytest.mark.parametrize("crm_stage", [None, {"key": None}, {"key": "inscripcion"}, {"key": "objeciones"}])
def test_missing_or_advanced_stage_never_downgrades(crm_stage):
    selected, trace = stages.choose(LanguageResilience.model_validate(document()), {"turn_plan": {"phase": "orientation"}}, crm_stage)
    assert selected.model == "anthropic/commercial"
    assert trace["route"] == "commercial"


def test_whole_pending_turn_objection_wins_over_last_greeting():
    selected, _ = stages.choose(LanguageResilience.model_validate(document()),
        {"turn_plan": turn_plan("Me parece caro\nHola")}, {"key": "nuevo"})
    assert selected.model == "anthropic/commercial"


def test_disabled_policy_and_incomplete_configs_are_explicit():
    assert stages.choose(LanguageResilience.model_validate({**document(), "enabled": False})) == (None, None)
    for patch in ({"primary": None}, {"opening_stage_keys": []}, {"opening_stage_keys": ["nuevo", "nuevo"]},
                  {"opening_stage_keys": ["bad key"]}, {"reply_max_tokens": 0}, {"reply_max_tokens": 8001}):
        with pytest.raises(ValidationError):
            LanguageResilience.model_validate({**document(), **patch})


def test_stage_reads_canonical_contact_and_renamed_active_definition(monkeypatch):
    calls = []
    def one(_c, sql, *args):
        calls.append(sql)
        return {"Stage": "Primer contacto"} if "crm.Contact" in sql else {
            "Document": json.dumps({"stages": [{"key": "nuevo", "label": "Primer contacto", "active": True}]}), "Revision": 12}
    monkeypatch.setattr(stages, "one", one)
    assert stages.stage(None, "conversation") == {"key": "nuevo", "revision": 12}
    assert "crm_workspace.Merge" in calls[0]


def test_general_and_specialists_inherit_without_changing_prompts_or_trials(monkeypatch):
    monkeypatch.setattr(stages, "stage", lambda *_: {"key": "nuevo"})
    cursor = SimpleNamespace(agent_turn_policy={"turn_plan": {"phase": "orientation"}})
    config = {"provider": "gemini", "primary_model": "gemini-old-lite", "max_tokens": 700,
              "instructions": "Skills y fuentes del programa", "memories": ["short", "customer_profile"]}
    for level in ("guide", "program", "stage"):
        selected = {"level": level, "configuration": copy.deepcopy(config)}
        stages.compose(cursor, selected, {"document": {"language_resilience": document()}}, "thread")
        effective = selected["configuration"]
        assert effective["primary_model"] == "google/opening"
        assert effective["max_tokens"] == 4000
        assert effective["instructions"] == config["instructions"]
        assert effective["memories"] == config["memories"]
        assert effective["fallback_model"] == "anthropic/commercial"
    trial = {"trial_temperature_supported": True, "configuration": config}
    stages.compose(cursor, trial, {"document": {"language_resilience": document()}})
    assert trial["configuration"] == config


def test_openrouter_text_does_not_require_gemini_key_or_profile_model(monkeypatch):
    from app.institutional import sales_context
    monkeypatch.setattr(sales_context, "configure", lambda *_: None)
    monkeypatch.setattr(worker, "setting", lambda *_: {"revision": 9, "document": {"enabled": True, "language_resilience": document()}})
    monkeypatch.setattr(stages, "stage", lambda *_: {"key": "nuevo", "revision": 2})
    original = {"provider": "gemini", "primary_model": "gemini-old-lite", "allow_reply": True,
                "capabilities": ["conversation.reply"], "max_tokens": 700}
    monkeypatch.setattr(worker, "resolve_conversation", lambda *_: {"agent_id": "agent", "binding": "binding", "configuration": original})
    credential = str(uuid4())
    calls = []
    def one(_c, _sql, *args):
        calls.append(args)
        assert args[-1] == "openrouter"
        return {"SecretId": credential}
    monkeypatch.setattr(worker, "one", one)
    monkeypatch.setattr(worker, "institution", lambda *_: "institution")
    config, _, binding = worker.model_config(None, None, {"conversation": "thread"})
    assert config["primary_model"] == "anthropic/commercial"
    assert binding["provider"] == "openrouter" and config["max_tokens"] == 4000
    assert original["primary_model"] == "gemini-old-lite"
    assert len(calls) == 1


def test_opening_snapshot_tries_commercial_then_approved_backup(monkeypatch):
    from app.institutional import language_resilience as runtime
    monkeypatch.setattr(runtime, "setting", lambda *_: {"revision": 9, "document": {"language_resilience": document()}})
    secret_id = str(uuid4())
    monkeypatch.setattr(runtime, "one", lambda *_: {"SecretId": secret_id, "VersionNo": 1, "Nonce": b"", "Ciphertext": b""})
    monkeypatch.setattr(runtime, "institution", lambda *_: "institution")
    monkeypatch.setattr(runtime, "key", lambda *_: b"fixture")
    monkeypatch.setattr(runtime, "unseal", lambda *_: "fixture")
    snapshot = runtime.snapshot(None, None, turn={"turn_plan": {"phase": "orientation"}}, crm_stage={"key": "nuevo"})
    assert snapshot["primary"]["model"] == "google/opening"
    assert [r["model"] for r in snapshot["routes"]] == ["anthropic/commercial", "anthropic/backup"]


def test_audio_model_is_independent_of_legacy_language_profile(monkeypatch):
    from app.institutional import sales_context
    monkeypatch.setattr(sales_context, "configure", lambda *_: None)
    ai = {"enabled": True, "language_resilience": document(), "media": {"audio_provider": "gemini", "audio_model": "gemini-3.8-flash"}}
    monkeypatch.setattr(worker, "setting", lambda *_: {"revision": 10, "document": ai})
    monkeypatch.setattr(stages, "stage", lambda *_: {"key": "nuevo", "revision": 2})
    config = {"provider": "gemini", "primary_model": "gemini-old-lite", "allow_reply": True,
              "capabilities": ["conversation.reply"], "input_usd_per_million": 1.0, "output_usd_per_million": 2.0}
    monkeypatch.setattr(worker, "resolve_conversation", lambda *_: {"agent_id": "agent", "binding": "binding", "configuration": config})
    monkeypatch.setattr(worker, "institution", lambda *_: "institution")
    def secret(_c, _sql, *args):
        assert args[-1] == "gemini"
        return {"SecretId": str(uuid4())}
    monkeypatch.setattr(worker, "one", secret)
    effective, _, binding = worker.model_config(None, None, {"conversation": "thread", "interpreting_audio": True})
    assert effective["primary_model"] == "gemini-3.8-flash" and binding["provider"] == "gemini"
    assert config["primary_model"] == "gemini-old-lite"
