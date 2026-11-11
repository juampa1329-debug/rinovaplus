"""Fixed public academic SELECTs; no personal records, SPs, tools or free SQL."""

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone

from app.modules.ai.infrastructure.providers import AiError

CATALOG = """SELECT o.Id_PrgOfrecido,p.Id_Programa,p.NombrePrograma,p.CodigoPrograma,p.Semestres,
 m.Modalidad,j.DetalleJornada FROM dbo.ACProgramaOfrecido o
 JOIN dbo.ACProgramas p ON p.Id_Programa=o.Id_Programa
 LEFT JOIN dbo.ACModalidad m ON m.Id_Modalidad=p.Id_Modalidad
 LEFT JOIN dbo.ACJornada j ON j.Id_Jornada=p.Id_Jornada
 WHERE o.Id_Periodo=? ORDER BY p.NombrePrograma,p.Id_Programa
 OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"""


def plain(value):
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c))))


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str)


def period(cursor):
    # Range locks keep each public source snapshot coherent and end before network.
    cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;")
    rows = cursor.execute("SELECT TOP(2) Id_Periodo,Periodo,FechaInicio,FechaFinal FROM dbo.GEPeriodo WHERE EstadoPeriodo=1 ORDER BY Id_Periodo").fetchall()
    if len(rows) != 1:
        raise AiError("institutional_active_period_ambiguous", 409)
    row = rows[0]
    return {"id": row[0], "label": row[1], "starts_at": str(row[2]), "ends_at": str(row[3])}


def program_row(row):
    return dict(zip(("offering_id", "program_id", "name", "code", "semesters", "modality", "schedule"), row, strict=True))


def programs(cursor, offset=0, limit=150):
    active = period(cursor)
    total = cursor.execute("SELECT COUNT(*) FROM dbo.ACProgramaOfrecido WHERE Id_Periodo=?", active["id"]).fetchval()
    rows = cursor.execute(CATALOG, active["id"], offset, limit + 1).fetchall()
    return {"period": active, "items": [program_row(r) for r in rows[:limit]], "total": total, "has_more": len(rows) > limit, "offset": offset}


def semester_from(question, explicit):
    if explicit is not None:
        return explicit, "selected"
    normalized = plain(question)
    matched = re.search(r"\b(?:semestre|nivel)\s+([1-9]|1[0-2])\b", normalized)
    if not matched:
        matched = re.search(r"\b([1-9]|1[0-2])\s+(?:semestre|nivel)\b", normalized)
    if matched:
        return int(matched[1]), "question"
    for word, number in (("primer", 1), ("primero", 1), ("segundo", 2), ("tercer", 3), ("tercero", 3), ("cuarto", 4)):
        if re.search(rf"\b{word}\s+(?:semestre|nivel)\b", normalized):
            return number, "question"
    return 1, "default_first_semester_explicitly_labeled"


def read_context(cursor, question, program_id=None, semester=None):
    catalog = programs(cursor, 0, 300)
    active = catalog["period"]
    choices = catalog["items"]
    selected = None
    normalized = " " + plain(question) + " "
    if program_id is not None:
        exact = cursor.execute(CATALOG.replace("WHERE o.Id_Periodo=?", "WHERE o.Id_Periodo=? AND p.Id_Programa=?"), active["id"], program_id, 0, 2).fetchall()
        if len(exact) != 1:
            raise AiError("institutional_program_not_in_active_offer", 409)
        selected = program_row(exact[0])
    else:
        matches = [p for p in choices if " " + plain(p["name"]) + " " in normalized]
        if len(matches) > 1:
            narrowed = [p for p in matches if p["schedule"] and " " + plain(p["schedule"]) + " " in normalized]
            matches = narrowed or matches
        if len(matches) == 1 and not catalog["has_more"]:
            selected = matches[0]
    level, level_origin = semester_from(question, semester)
    material = {"period": active, "program_catalog": choices, "catalog_total": catalog["total"], "catalog_truncated": catalog["has_more"], "selected": selected, "semester": level, "tariffs": [], "curriculum": [], "admission_documents": []}
    if selected:
        identifier = selected["program_id"]
        tariffs = cursor.execute("SELECT TOP(11) t.Id_Tarifa,t.ValorSmtrOr,t.ValorSmtrEx,t.Semestre,t.Id_Plan,p.NombrePlan,p.TipoPlan,p.Id_Periodo "
            "FROM dbo.AFTarifas t LEFT JOIN dbo.AFPlanes p ON p.Id_Plan=t.Id_Plan "
            "WHERE t.Id_Programa=? AND t.Id_Periodo=? AND t.Semestre=? ORDER BY t.Id_Tarifa", identifier, active["id"], level).fetchall()
        if len(tariffs) > 10:
            raise AiError("institutional_tariff_limit", 409)
        for row in tariffs:
            tariff = {"tariff_id": row[0], "ordinary": row[1] if row[1] and row[1] > 0 else None, "extraordinary": row[2] if row[2] and row[2] > 0 else None, "semester": row[3], "plan_id": row[4], "plan_name": row[5], "plan_type": row[6], "plan_period_id": row[7], "currency": None, "currency_note": "Las tablas consultadas no declaran moneda; no inferirla.", "payment_schedule": []}
            if row[4] and row[7] == active["id"]:
                details = cursor.execute("SELECT TOP(31) Id_DetallePLan,Concepto,Porcentaje,Valor,ValorExtr,FechaPago FROM dbo.AFDetallePlanPago WHERE Id_Plan=? ORDER BY FechaPago,Id_DetallePLan", row[4]).fetchall()
                if len(details) > 30:
                    raise AiError("institutional_payment_schedule_limit", 409)
                tariff["payment_schedule"] = [{"id": d[0], "concept": d[1], "percentage_recorded": d[2], "ordinary_value_recorded": d[3], "extraordinary_value_recorded": d[4], "due_date": str(d[5])} for d in details]
            material["tariffs"].append(tariff)
        curriculum = cursor.execute("SELECT TOP(81) e.Id_PlanEducativo,e.NombrePLan,e.Id_Periodo,a.Id_AsignaturaPlan,a.Id_Asignatura,s.NombreAsignatura,a.Nivel,a.Creditos,a.Intensidad "
            "FROM dbo.ACPlanEducativo e JOIN dbo.ACAsignaturaPlan a ON a.Id_PlanEducativo=e.Id_PlanEducativo AND a.Inactiva=0 "
            "JOIN dbo.ACAsignatura s ON s.Id_Asignatura=a.Id_Asignatura WHERE e.Id_Programa=? AND e.Vigente=1 AND a.Nivel=? ORDER BY e.Id_PlanEducativo,a.Id_AsignaturaPlan", identifier, level).fetchall()
        if len(curriculum) > 80:
            raise AiError("institutional_curriculum_limit", 409)
        material["curriculum"] = [{"plan_id": r[0], "plan_name": r[1], "plan_period_id": r[2], "assignment_id": r[3], "subject_id": r[4], "subject": r[5][:500], "level": r[6], "credits": r[7], "intensity_recorded": r[8]} for r in curriculum]
        documents = cursor.execute("SELECT DISTINCT TOP(41) i.Id_TipoImagen,i.TipoImagen,i.Descripcion FROM dbo.GEImgenProg g JOIN dbo.GETipoImagen i ON i.Id_TipoImagen=g.Id_TipoImagen AND i.Estado=1 WHERE g.Id_Programa=? ORDER BY i.Id_TipoImagen", identifier).fetchall()
        if len(documents) > 40:
            raise AiError("institutional_document_types_limit", 409)
        material["admission_documents"] = [{"type_id": d[0], "type": d[1], "description": d[2]} for d in documents]
    fingerprint = hashlib.sha256(encode(material).encode()).hexdigest()
    retrieved = datetime.now(timezone.utc).isoformat()
    def source(kind, title, body, tables):
        return {"id": f"sql:{kind}:{active['id']}:{selected['program_id'] if selected else 'catalog'}:{level}:{fingerprint[:20]}", "source_kind": "sql", "title": title, "page": None, "text": encode(body), "period": active, "program_id": selected["program_id"] if selected else None, "semester": level, "retrieved_at": retrieved, "fingerprint": fingerprint, "provenance": tables}
    # A broad list is explicitly a page, never an assertion that omitted offers do not exist.
    program_data = {"period": active, "offered_total": catalog["total"], "shown": [selected] if selected else choices[:15], "has_more": False if selected else catalog["total"] > 15, "selection_kind": "exact_program" if selected else "catalog_page", "is_complete_catalog": not selected and catalog["total"] <= 15, "selected_program": selected, "requires_program_selection": selected is None, "note": "Si hay variantes con igual nombre, pedir selección exacta de programa/jornada; no escoger la primera. Una selección exacta no es el catálogo completo."}
    sources = [source("programs", "SIIE · oferta académica del período activo", program_data, ["GEPeriodo", "ACProgramaOfrecido", "ACProgramas", "ACModalidad", "ACJornada"])]
    if selected:
        sources.extend([
            source("tariffs", "SIIE · tarifas registradas del programa", {"program": selected, "semester": level, "semester_origin": level_origin, "tariffs": material["tariffs"], "status": "known" if len(material["tariffs"]) == 1 and material["tariffs"][0]["ordinary"] else "requires_advisor", "note": "Valores ordinario/extraordinario separados. Cero o ausencia no significan gratuidad. No sumar ni multiplicar tarifas, cuotas, descuentos o porcentajes. Plan ausente/de otro período no acredita condiciones de financiación."}, ["AFTarifas", "AFPlanes", "AFDetallePlanPago"]),
            source("curriculum", "SIIE · asignaturas activas del plan educativo vigente", {"program": selected, "level": level, "subjects": material["curriculum"], "status": "known" if len({s["plan_id"] for s in material["curriculum"]}) == 1 else "requires_advisor", "note": "Sólo el nivel mostrado, no es el pensum completo. Plan vigente puede proceder de un período anterior. Sin filas no significa programa sin asignaturas. Si hay varios planes vigentes, pedir aclaración al asesor, no mezclarlos como un solo pensum."}, ["ACPlanEducativo", "ACAsignaturaPlan", "ACAsignatura"]),
            source("admission_documents", "SIIE · tipos documentales asignados al programa", {"program": selected, "document_types": material["admission_documents"], "status": "assigned_types" if material["admission_documents"] else "requires_advisor", "note": "Son tipos asignados: no hay bandera obligatorio/opcional. Conservar literalmente condiciones como en caso de ser menor de edad. No acredita entrega ni elegibilidad personal. No son prerrequisitos entre asignaturas."}, ["GEImgenProg", "GETipoImagen"]),
        ])
    return {"sources": sources, "fingerprint": fingerprint, "period": active, "selected_program": selected, "semester": level, "semester_origin": level_origin, "catalog_total": catalog["total"], "catalog_has_more": program_data["has_more"], "catalog_read_truncated": catalog["has_more"], "selection_required": selected is None}
