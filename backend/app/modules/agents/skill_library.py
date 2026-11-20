"""Read reviewed CRM SKILL.md files, never host skills or executable plugins."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

DIRECTORY = Path(__file__).with_name("skills")


@lru_cache(maxsize=1)
def manifest():
    value = json.loads((DIRECTORY / "manifest.json").read_text(encoding="utf-8"))
    from app.modules.agents.sales_skills import IDS
    if value.get("version") != "cbn-skill-library-v1" or set(value["items"]) != IDS:
        raise ValueError("skill_library_manifest_invalid")
    return value


@lru_cache(maxsize=64)
def read(skill_id):
    item = manifest()["items"].get(skill_id)
    if item is None:
        raise ValueError("skill_library_unknown_resource")
    # IDs come from the packaged manifest. Caller paths cannot enter this read.
    raw = (DIRECTORY / skill_id / "SKILL.md").read_bytes()
    if len(raw) > 12000 or hashlib.sha256(raw).hexdigest() != item["sha256"]:
        raise ValueError("skill_library_resource_changed")
    return {"id": skill_id, "version": manifest()["version"], "source": item["source"],
            "path": "app/modules/agents/skills/" + skill_id + "/SKILL.md",
            "sha256": item["sha256"], "content": raw.decode("utf-8")}


def resources(ids):
    return [{k: v for k, v in read(key).items() if k != "content"} for key in dict.fromkeys(ids)]


def render(records):
    parts = []
    for record in records:
        guide = read(record["id"])
        if guide["sha256"] != record["sha256"]:
            raise ValueError("skill_library_resource_changed")
        parts.append("\nSKILL CONSULTADA: " + guide["id"] + "\n" + guide["content"])
    result = "\n".join(parts)
    if len(result) > 15000:
        raise ValueError("skill_library_context_review_required")
    return result
