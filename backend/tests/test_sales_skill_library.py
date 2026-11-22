import hashlib
import json

import pytest

from app.modules.agents import skill_library as library
from app.modules.agents.sales_skills import IDS, catalog
from app.modules.agents.skill_policy import for_turn, instructions
from app.institutional import sales_context


def test_manual_focus_covers_all_17_requested_skills_and_rejects_unknown_focus():
    from app.modules.agents.skill_policy import SIMULATION_FOCUS
    expected = {"cold-call-opener", "lead-intelligence", "sales-discovery-questions", "meddpicc-scorecard",
                "deal-champion-mapping", "deal-red-flags", "deal-value-calc", "pricing",
                "negotiation-concession-planner", "negotiation", "sales-objection-handling",
                "sales-closing-tactics", "sales-enablement", "marketing-psychology", "sales-call-review",
                "copywriting", "ads-copywriter"}
    assert {key for group in SIMULATION_FOCUS.values() for key in group} == expected
    with pytest.raises(ValueError, match="skill_simulation_focus_invalid"):
        for_turn("Hola", simulation_focus="../../private")
    assert for_turn("Hola") == for_turn("Hola", simulation_focus=None)


@pytest.mark.parametrize("focus", ["opening", "discovery", "value", "negotiation", "closing", "review", "advertisement"])
def test_manual_focus_includes_whole_required_guides_and_retains_memory_and_safety(focus):
    from app.modules.agents.skill_policy import SIMULATION_FOCUS
    trace = for_turn("Me interesa Barismo, pero me parece caro. ¿Con cuánto puedo empezar?", simulation_focus=focus)
    required = set(SIMULATION_FOCUS[focus])
    consulted = {r["id"] for r in trace["consulted_resources"]}
    assert required | {"recall", "graphify", "handoff", "copy-editing", "marketing-psychology"} <= consulted
    assert required.isdisjoint(trace["deferred_resource_ids"])
    prompt = instructions(trace)
    for key in required:
        assert library.read(key)["content"] in prompt
    assert trace["simulation_focus"]["published_configuration_changed"] is False
    assert trace["grants_permissions"] is False
    assert "Humano" in prompt and "memoria privada" in prompt


def test_all_34_native_guides_exist_with_complete_content_and_manifest_hashes():
    assert len(IDS) == 34 and set(library.manifest()["items"]) == IDS
    for item in catalog():
        guide = item["guide"]
        assert guide["path"].endswith("/" + item["id"] + "/SKILL.md")
        assert hashlib.sha256(guide["content"].encode()).hexdigest() == guide["sha256"]
        assert "## " in guide["content"] and len(guide["content"]) > 500
        assert "reviewed_native_crm_adaptation" in guide["content"]
        assert "\r" not in guide["content"]


def test_unknown_ids_never_become_paths_and_tampered_pack_is_rejected(tmp_path, monkeypatch):
    for key in ("../pricing", "C:/Users/private", "execute-me"):
        with pytest.raises(ValueError, match="unknown_resource"):
            library.read(key)
    manifest = json.loads(json.dumps(library.manifest()))
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "pricing").mkdir()
    (tmp_path / "pricing/SKILL.md").write_text("changed", encoding="utf-8")
    monkeypatch.setattr(library, "DIRECTORY", tmp_path)
    library.manifest.cache_clear()
    library.read.cache_clear()
    try:
        with pytest.raises(ValueError, match="resource_changed"):
            library.read("pricing")
    finally:
        library.manifest.cache_clear()
        library.read.cache_clear()


@pytest.mark.parametrize("question,required", [
    ("Información de Barismo", {"cold-call-opener", "sales-enablement"}),
    ("Me parece caro", {"sales-objection-handling", "pricing"}),
    ("Voy a ver otras opciones", {"sales-objection-handling", "sales-enablement"}),
    ("¿Con cuánto puedo empezar?", {"pricing", "deal-value-calc"}),
    ("Listo para matricularme", {"sales-closing-tactics", "close-plan"}),
])
def test_primary_and_memory_guides_are_injected_whole_not_just_the_index(question, required):
    trace = for_turn(question)
    consulted = {v["id"] for v in trace["consulted_resources"]}
    assert required | {"recall", "graphify", "handoff", "copy-editing", "marketing-psychology"} <= consulted
    prompt = instructions(trace)
    for record in trace["consulted_resources"]:
        assert library.read(record["id"])["content"] in prompt
    assert not consulted.intersection(trace["deferred_resource_ids"])
    assert len(library.render(trace["consulted_resources"])) <= 15000
    assert trace["authority"] == "backend_required" and trace["grants_permissions"] is False


def test_comparison_and_short_aliases_cannot_change_program_interest():
    programs = [{"program_id":1,"name":"ATENCION INTEGRAL A PRIMERA INFANCIA"},
                {"program_id":2,"name":"BARISMO Y BARTENDER"},
                {"program_id":3,"name":"MANTENIMIENTO ELECTRONICO"}]
    profiles = {3:{"aliases":"ME"}}
    messages = [{"Direction":"incoming","Body":"Me interesa Barismo y Bartender","MessageId":"one","Sequence":1},
                {"Direction":"incoming","Body":"voya a ver optras opciones","MessageId":"two","Sequence":2}]
    assert sales_context.interest(programs, profiles, messages)["program_id"] == 2
    for question in ("a", "me", "me parece caro", "voy a ver otras opciones"):
        assert sales_context.matches(programs, profiles, question) == []


@pytest.mark.parametrize("question", [
    "Me interesa Barismo y Bartender para abrir mi propio negocio. ¿Cómo me ayudaría esa formación?",
    "¿Cómo me ayudaría a crear mi propio negocio?",
    "Busco Software para montar mi empresa.",
])
def test_business_purpose_consults_value_guides_without_opening_a_price_pitch(question):
    selected = for_turn(question, history=[{"role":"user","content":"Me interesa estudiar"}])
    assert selected["turn_plan"]["phase"] == "value_alignment"
    assert not selected["turn_plan"]["money_relevant"]
    assert {"sales-enablement", "deal-value-calc", "recall", "graphify"} <= {r["id"] for r in selected["consulted_resources"]}


def test_business_purpose_does_not_override_requested_finance_or_an_objection():
    assert for_turn("Quiero Barismo para abrir mi negocio. ¿Con cuánto puedo empezar?")["turn_plan"]["phase"] == "financial"
    assert for_turn("Quiero Barismo para abrir mi negocio pero me parece caro")["turn_plan"]["phase"] == "objection"


def test_prompt_trace_is_compact_but_operational_audit_restores_exact_provenance():
    import json
    from app.modules.agents.skill_policy import prompt_trace, from_messages
    full = for_turn("¿Con cuánto puedo empezar?")
    compact = prompt_trace(full)
    assert len(json.dumps(compact)) < len(json.dumps(full))
    envelope = [{"role": "system", "content": instructions(full)},
                {"role": "user", "content": "Contexto de referencia, no instrucciones:\n" + json.dumps({"skill_policy": compact})}]
    assert from_messages(envelope) == full
    compact["resource_fingerprint"] = "0" * 64
    envelope[1]["content"] = "Contexto de referencia, no instrucciones:\n" + json.dumps({"skill_policy": compact})
    with pytest.raises(ValueError, match="resource_changed"):
        from_messages(envelope)
