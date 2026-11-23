"""Convert the private classification into the reviewed import upload. No CRM IO."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5


def build(classification):
    evidence = defaultdict(list)
    apps = defaultdict(list)
    for row in classification["evidence"]:
        evidence[row["contact_ref"]].append(row)
    for row in classification["applications"]:
        apps[row["contact_ref"]].append(row)
    sources = {s["file"]: s["sha256"] for s in classification["summary"]["sources"]}
    entries = []
    for contact in classification["contacts"]:
        reference = contact["contact_ref"]
        observations = evidence[reference]
        interests = apps[reference]
        notes = []
        for row in observations:
            note = {
                "origen": row["source"],
                "sha256": sources[row["source"]],
                "hoja": row["sheet"],
                "fila": row["row"],
                "fecha_excel": row.get("excel_date_serial"),
                "sistema_fecha_excel": row.get("excel_date_mode"),
                "datos_exportados": row["raw"],
            }
            notes.append(
                "Preinscripción: evidencia de origen. No acredita contacto, "
                "matrícula ni consentimiento.\n" + json.dumps(note, ensure_ascii=False)
            )
        last = max(
            (a for a in interests if a["last_management"]),
            key=lambda a: a["last_management"],
            default=None,
        )
        entries.append(
            {
                "ref": reference,
                "name": contact["name"],
                "phone": contact["phones"].split(" | ")[0],
                "email": contact["emails"].split(" | ")[0],
                "programs": sorted({a["program"] for a in interests}),
                "stages": sorted({a["stage"] for a in interests}),
                "first_date": contact["first_registered"][:10],
                "last_date": contact["latest_registered"][:10],
                "management_date": contact["last_management"],
                "advisor": last["advisor"] if last else "",
                "channels": " | ".join(
                    sorted({str(r["raw"]["Inscripcion"]).strip() for r in observations})
                ),
                "source_files": " | ".join(sorted({r["source"] for r in observations})),
                "review": [v for v in contact["review"].split(" | ") if v],
                "notes": notes,
            }
        )
    return {
        "version": "rinovaplus-prospects-v1",
        "batch_id": str(uuid5(NAMESPACE_URL, json.dumps(sources, sort_keys=True))),
        "entries": entries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("classification", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    destination = args.output.resolve()
    if destination.is_relative_to(repo) and not destination.is_relative_to(
        repo / ".local"
    ):
        parser.error("Personal data inside this repository must stay under .local/")
    result = build(json.loads(args.classification.read_text(encoding="utf-8")))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "entries": len(result["entries"]),
                "held_from_source": sum(bool(e["review"]) for e in result["entries"]),
                "notes": sum(len(e["notes"]) for e in result["entries"]),
            }
        )
    )


if __name__ == "__main__":
    main()
