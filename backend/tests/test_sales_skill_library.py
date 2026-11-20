import hashlib
import json

import pytest

from app.modules.agents import skill_library as library
from app.modules.agents.sales_skills import IDS, catalog
from app.modules.agents.skill_policy import for_turn, instructions
from app.institutional import sales_context


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
