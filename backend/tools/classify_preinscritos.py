"""Offline prospect classification. Reads exports; never connects to CRM or sends.

Run with xlrd 2.0.2 available for legacy .xls input. Output contains personal
data and belongs in an ignored/private directory, never in Git.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

VERSION = "preinscritos-v1"
HEADERS = [
    "Aspirante", "Celular", "Telefono", "Mail", "Programa de Interes",
    "Fecha", "Inscripcion", "Seguimiento", "Estado",
]
STAGES = {
    "": "Pendiente de calificación",
    "en negociacion": "En negociación",
    "no contesto": "Intento sin respuesta",
    "negociacion no aceptada": "Negociación no aceptada",
    "inscrito": "Inscrito según origen",
    "repetido": "Duplicado marcado en origen",
}
BUCKETS = ["0–7 días", "8–14 días", "15–29 días", "30–59 días", "60–89 días", "90+ días"]


def text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def key(value):
    value = unicodedata.normalize("NFKD", text(value)).casefold()
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).split())


def mobile(value):
    """Conservative Colombian mobile syntax; does not verify ownership/WhatsApp."""
    value = text(value)
    if not re.fullmatch(r"[+\d ()-]+", value):
        return ""
    digits = re.sub(r"\D", "", value)
    if len(digits) == 10 and digits.startswith("3"):
        digits = "57" + digits
    if not re.fullmatch(r"573\d{9}", digits) or len(set(digits[2:])) < 3:
        return ""
    return "+" + digits


def email(value):
    value = text(value).casefold()
    return value if re.fullmatch(r"[^\s@\x00-\x1f]+@[^\s@\x00-\x1f]+\.[a-z]{2,63}", value) else ""


def days_since(value, as_of):
    if not value:
        return None
    return (as_of - date.fromisoformat(value[:10])).days


def bucket(days):
    if days is None:
        return "Sin fecha registrada"
    if days < 0:
        return "Fecha futura: revisar"
    for limit, label in zip([7, 14, 29, 59, 89], BUCKETS):
        if days <= limit:
            return label
    return BUCKETS[-1]


def read_exports(paths):
    import xlrd  # Optional extraction dependency; no macros/formulas executed.

    records, manifest = [], []
    for path in paths:
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        book = xlrd.open_workbook(file_contents=data)
        for sheet in book.sheets():
            if not sheet.nrows:
                continue
            headers = [text(v) for v in sheet.row_values(0)]
            if headers not in [HEADERS, HEADERS + ["Ultimo asesor"]]:
                raise ValueError(f"Unexpected headers: {path.name}/{sheet.name}")
            before = len(records)
            for i in range(1, sheet.nrows):
                if not any(text(v) for v in sheet.row_values(i)):
                    continue
                raw = dict(zip(headers, sheet.row_values(i)))
                if sheet.cell_type(i, 5) not in (xlrd.XL_CELL_DATE, xlrd.XL_CELL_NUMBER):
                    raise ValueError(f"Non-Excel date: {path.name}/{sheet.name}/{i + 1}")
                serial = raw["Fecha"]
                raw["Fecha"] = xlrd.xldate_as_datetime(serial, book.datemode).isoformat(timespec="seconds")
                records.append({"source": path.name, "sheet": sheet.name, "row": i + 1,
                                "excel_date_serial": serial, "excel_date_mode": book.datemode,
                                "raw": raw})
            manifest.append({"file": path.name, "sha256": digest, "sheet": sheet.name, "records": len(records) - before})
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Source changed during analysis")
    return records, manifest


def prepare(record):
    raw = record["raw"]
    phones = sorted({p for field in ("Celular", "Telefono") if (p := mobile(raw.get(field)))})
    addr = email(raw.get("Mail"))
    advisor_raw = text(raw.get("Ultimo asesor"))
    match = re.fullmatch(r"(.+?)\s+(\d{4}-\d{2}-\d{2})", advisor_raw)
    management, advisor = "", ""
    if match:
        try:
            management = date.fromisoformat(match[2]).isoformat()
            advisor = match[1].strip()
        except ValueError:
            pass
    return {
        **record, "name": text(raw.get("Aspirante")),
        "name_key": key(raw.get("Aspirante")), "phones": phones, "email": addr,
        "registered": raw["Fecha"], "program": text(raw.get("Programa de Interes")),
        "status": key(raw.get("Estado")), "management": management,
        "advisor": advisor, "advisor_unparsed": bool(advisor_raw and not management),
    }


def next_action(stage, management_bucket, registration_bucket, review):
    if review:
        return "Revisar identidad o datos", "revision_datos"
    if stage == "Inscrito según origen":
        return "Verificar inscripción; excluir captación", "sin_captacion"
    if stage == "Negociación no aceptada":
        return "Pausar seguimiento; revisar motivo con asesor", "pausado_no_aceptada"
    if stage == "En negociación":
        if management_bucket in BUCKETS[3:]:
            return "Revisar vigencia del interés con asesor", "reactivacion_30_mas"
        return "Resolver dudas sobre programa y siguiente paso", "seguimiento_negociacion"
    if stage == "Intento sin respuesta":
        return "Revisar intentos previos y ofrecer una respuesta sencilla", "seguimiento_sin_respuesta"
    if stage == "Pendiente de calificación":
        if registration_bucket in BUCKETS[3:]:
            return "Revisar historial; confirmar si conserva interés", "interes_antiguo_sin_gestion"
        return "Revisar historial; presentación y pregunta de interés", "presentacion_sin_gestion"
    return "Revisar etapa con asesor", "revision_etapa"


def classify(records, as_of):
    rows = [prepare(r) for r in records]
    parent = list(range(len(rows)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, row in enumerate(rows):
        if not row["name_key"]:
            continue
        for coordinate in row["phones"] + ([row["email"]] if row["email"] else []):
            token = (row["name_key"], coordinate)
            if token in seen:
                parent[root(i)] = root(seen[token])
            else:
                seen[token] = i
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[root(i)].append(row)
    coordinate_owners, name_owners = defaultdict(set), defaultdict(set)
    for group_id, group in groups.items():
        for row in group:
            if row["name_key"]:
                name_owners[row["name_key"]].add(group_id)
            for coordinate in row["phones"] + ([row["email"]] if row["email"] else []):
                coordinate_owners[coordinate].add(group_id)

    contacts, applications, evidence = [], [], []
    for group_id, group in groups.items():
        group.sort(key=lambda r: (r["registered"], r["source"], r["row"]))
        phones = sorted({p for r in group for p in r["phones"]})
        emails = sorted({r["email"] for r in group if r["email"]})
        name = group[-1]["name"]
        anchor = group[0]
        ref = "PRE-" + hashlib.sha256(json.dumps([anchor["name_key"], phones, emails], ensure_ascii=False).encode()).hexdigest()[:16]
        flags = []
        if not name:
            flags.append("Nombre ausente")
        elif not any(c.isalpha() for c in name):
            flags.append("Nombre no utilizable: revisar")
        if not phones:
            flags.append("Sin celular colombiano con formato válido")
        if not emails:
            flags.append("Sin correo con formato válido")
        if any(len(coordinate_owners[c]) > 1 for c in phones + emails):
            flags.append("Teléfono o correo compartido entre nombres distintos")
        if any(len(name_owners[r["name_key"]]) > 1 for r in group if r["name_key"]):
            flags.append("Mismo nombre con datos de contacto distintos: revisar")
        if len(phones) > 1:
            flags.append("Varios celulares: confirmar principal")
        if len(emails) > 1:
            flags.append("Varios correos: confirmar principal")
        if any(r["advisor_unparsed"] for r in group):
            flags.append("Último asesor sin fecha interpretable")
        if any(days_since(r["registered"], as_of) < 0 for r in group):
            flags.append("Preinscripción futura")
        if any(r["management"] and (days_since(r["management"], as_of) < 0 or r["management"] < r["registered"][:10]) for r in group):
            flags.append("Fecha de gestión futura o anterior a la preinscripción")

        # One pre-registration can appear in both exports with an updated status.
        # Different dates/programs remain separate opportunities and all rows survive.
        interests = defaultdict(list)
        for row in group:
            interests[(key(row["program"]), row["registered"])].append(row)
            evidence.append({"contact_ref": ref, **row})
        contact_apps = []
        for (_, registered), copies in interests.items():
            observed = {r["status"] for r in copies if r["status"]}
            app_flags = list(flags)
            if len(observed) > 1:
                stage = "Etapas contradictorias: revisar"
                app_flags.append("Estado contradictorio entre exportaciones")
            else:
                status = next(iter(observed), "")
                stage = STAGES.get(status, "Etapa desconocida: revisar")
                if status not in STAGES:
                    app_flags.append("Estado no reconocido")
                if status == "repetido":
                    app_flags.append("Duplicado marcado en origen")
            valid_management = [r for r in copies if r["management"] and 0 <= days_since(r["management"], as_of) and r["management"] >= registered[:10]]
            last = max(valid_management, key=lambda r: r["management"], default=None)
            management = last["management"] if last else ""
            management_days = days_since(management, as_of)
            management_bucket = bucket(management_days) if management else "Sin gestión registrada"
            registration_days = days_since(registered, as_of)
            registration_bucket = bucket(registration_days)
            blocking_review = [f for f in app_flags if f != "Sin correo con formato válido"]
            action, segment = next_action(stage, management_bucket, registration_bucket, bool(blocking_review))
            app = {
                "contact_ref": ref, "name": name, "program": copies[0]["program"],
                "registered": registered, "registration_days": registration_days,
                "registration_bucket": registration_bucket, "stage": stage,
                "source_status": " | ".join(sorted({text(r["raw"].get("Estado")) for r in copies})),
                "last_management": management, "management_days": management_days,
                "management_bucket": management_bucket, "advisor": last["advisor"] if last else "",
                "last_contact_verified": None, "segment": segment, "next_action": action,
                "review": " | ".join(app_flags), "sources": " | ".join(f'{r["source"]}/{r["sheet"]}!{r["row"]}' for r in copies),
                "copies": len(copies), "consent": "Sin evidencia en archivos",
                "send_eligible": False,
            }
            applications.append(app)
            contact_apps.append(app)
        stages = sorted({a["stage"] for a in contact_apps})
        last_management = max((a["last_management"] for a in contact_apps), default="")
        all_flags = sorted({f for a in contact_apps for f in a["review"].split(" | ") if f})
        contacts.append({
            "contact_ref": ref, "name": name, "phones": " | ".join(phones),
            "emails": " | ".join(emails), "programs": " | ".join(sorted({a["program"] for a in contact_apps})),
            "stages": " | ".join(stages), "last_management": last_management,
            "management_days": days_since(last_management, as_of),
            "management_bucket": bucket(days_since(last_management, as_of)) if last_management else "Sin gestión registrada",
            "first_registered": min(r["registered"] for r in group),
            "latest_registered": max(r["registered"] for r in group),
            "registrations": len(contact_apps), "source_rows": len(group),
            "review": " | ".join(all_flags), "last_contact_verified": None,
            "consent": "Sin evidencia en archivos", "send_eligible": False,
        })
    contacts.sort(key=lambda c: (c["name"], c["contact_ref"]))
    applications.sort(key=lambda a: (a["stage"], a["management_bucket"], a["name"]))
    assert len(evidence) == len(records)
    assert sum(c["source_rows"] for c in contacts) == len(records)
    assert sum(a["copies"] for a in applications) == len(records)
    summary = {
        "version": VERSION, "as_of": as_of.isoformat(), "timezone": "America/Bogota",
        "source_rows": len(rows), "contact_groups": len(contacts),
        "registrations": len(applications), "overlapping_snapshot_rows": len(rows) - len(applications),
        "contacts_with_review": sum(bool(c["review"]) for c in contacts),
        "contacts_with_management": sum(bool(c["last_management"]) for c in contacts),
        "contacts_without_management": sum(not c["last_management"] for c in contacts),
        "contacts_with_mobile_syntax": sum(bool(c["phones"]) for c in contacts),
        "contacts_with_email_syntax": sum(bool(c["emails"]) for c in contacts),
        "shared_coordinates": sum(len(owners) > 1 for owners in coordinate_owners.values()),
        "contact_management_buckets": dict(Counter(c["management_bucket"] for c in contacts)),
        "application_stages": dict(Counter(a["stage"] for a in applications)),
        "application_registration_buckets": dict(Counter(a["registration_bucket"] for a in applications)),
        "application_segments": dict(Counter(a["segment"] for a in applications)),
        "programs": dict(Counter(a["program"] for a in applications)),
        "verified_last_contacts": 0, "send_eligible": 0,
        "live_crm_checked": False, "imported": False,
    }
    return {"summary": summary, "contacts": contacts, "applications": applications, "evidence": evidence}


def safe_csv(value):
    value = "" if value is None else str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def write_outputs(result, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / "classification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "summary.json").write_text(json.dumps(result["summary"], ensure_ascii=False, indent=2), encoding="utf-8")
    for name in ["contacts", "applications"]:
        rows = result[name]
        if not rows:
            continue
        with (output / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows({k: safe_csv(v) for k, v in row.items()} for row in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    # Prevent accidental publication of personal data in this repository.
    repo = Path(__file__).resolve().parents[2]
    output = args.output_dir.resolve()
    if output.is_relative_to(repo) and not output.is_relative_to(repo / ".local"):
        parser.error("Personal-data output inside this repo must be under .local/")
    for path in args.input:
        if path.resolve().is_relative_to(output):
            parser.error("Output directory must not contain source files")
    records, manifest = read_exports(args.input)
    result = classify(records, args.as_of)
    result["summary"]["sources"] = manifest
    write_outputs(result, output)
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
