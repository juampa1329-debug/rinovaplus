"""Reviewed R7 enrollment selectors. Native values, scoped geography, no writes."""

import re

from fastapi import HTTPException

from app.institutional import siie_registration_client as source

# Field -> native catalog path/property. Labels never substitute for these values.
MAPPING = {
    "estudiante.TipoId": ("tiposDocumento", "valor"),
    "estudiante.Id_Genero": ("generos", "valor"),
    "estudiante.EstadoCivil": ("opciones.estadosCiviles", "valor"),
    "estudiante.GrupoSanguineo": ("opciones.gruposSanguineos", "valor"),
    "estudiante.FactorRh": ("opciones.factoresRh", "valor"),
    "estudiante.Estrato": ("opciones.estratos", "valor"),
    "inscripcion.Id_Jornada": ("jornadas", "valor"),
    "estudiosSecundarios.ultimoGrado": ("opciones.gradosSecundaria", "valor"),
    "estudiosSecundarios.Titulo": ("opciones.titulosSecundaria", "valor"),
    "estudiosSecundarios.Modalidad": ("modalidades", "valor"),
    "otrosEstudios[].Id_TipoEstudio": ("tiposEstudio", "valor"),
    "otrosEstudios[].TituloCarrera": ("tiposEstudio", "nombre"),
    "otrosEstudios[].ModEstdio": ("modalidades", "valor"),
    "otrosEstudios[].Semestre": ("opciones.semestresCursados", "valor"),
    "informacionLaboral.Tiempo": ("opciones.tiemposLaborales", "valor"),
    "familiaCbn[].Carrera": ("programasFamilia", "valor"),
    "socioeconomica.CostodiaEstudios": ("opciones.costeaEstudios", "valor"),
    "socioeconomica.Becade": ("opciones.financiadores", "valor"),
    "socioeconomica.Prestamode": ("opciones.prestamos", "valor"),
    "socioeconomica.AfiliadoSisben": ("opciones.siNo", "valor"),
    "socioeconomica.NivelSIS": ("opciones.nivelesSisben", "valor"),
    "socioeconomica.NombreEps": ("opciones.eps", "valor"),
    "grupoEspecial.MinoriaEtnicas": ("opciones.gruposEtnicos", "valor"),
    "padres[].Parentesco": ("opciones.parentescosPadres", "valor"),
}
GEOGRAPHY = {
    "estudiante.Expedida": "valor",
    "estudiante.Id_Poblacion": "valor",
    "estudiante.CiudadNacimiento": "valorTexto",
    "estudiosSecundarios.Municipio": "valorTexto",
    "otrosEstudios[].Municipio": "valorTexto",
    "informacionLaboral.Municipio": "valorTexto",
    "informacionLaboral.Departamento": "valorTexto",
}


def schema_path(path):
    return re.sub(r"\.[0-2](?=\.)", "[]", path)


def filters(values):
    allowed = {"idPais", "idDepartamento", "q", "offset"}
    if not isinstance(values, dict) or values.keys() - allowed:
        raise HTTPException(422, "siie_catalog_filters_invalid")
    result = {}
    for name in ("idPais", "idDepartamento"):
        if name in values:
            value = values[name]
            if type(value) is not int or not 1 <= value <= 2147483647:
                raise HTTPException(422, "siie_catalog_filters_invalid")
            result[name] = value
    if "q" in values:
        if (
            not isinstance(values["q"], str)
            or len(values["q"]) > 80
            or any(ord(c) < 32 for c in values["q"])
        ):
            raise HTTPException(422, "siie_catalog_filters_invalid")
        result["q"] = values["q"]
    if "offset" in values:
        if type(values["offset"]) is not int or not 0 <= values["offset"] <= 1000000:
            raise HTTPException(422, "siie_catalog_filters_invalid")
        result["offset"] = values["offset"]
    if (
        "idDepartamento" in result
        and "idPais" not in result
        or ({"q", "offset"} & result.keys())
        and not {"idPais", "idDepartamento"} <= result.keys()
    ):
        raise HTTPException(422, "siie_catalog_filters_invalid")
    return result


def locations(values):
    if not isinstance(values, dict) or len(values) > 12:
        raise HTTPException(422, "siie_catalog_filters_invalid")
    result = {}
    for path, selection in values.items():
        if schema_path(path) not in GEOGRAPHY:
            raise HTTPException(422, "siie_catalog_filters_invalid")
        result[path] = filters(selection)
    return result


def collection(data, path):
    current = data
    for key in path.split("."):
        current = current.get(key) if isinstance(current, dict) else None
    return current


def choices(values, prop="valor", *, limit=1000, max_length=None):
    if not isinstance(values, list) or len(values) > limit:
        raise HTTPException(502, "siie_registration_invalid_catalog")
    result, seen = [], set()
    for item in values:
        if not isinstance(item, dict):
            raise HTTPException(502, "siie_registration_invalid_catalog")
        value, label = item.get(prop), item.get("nombre")
        if (
            type(value) not in (int, str)
            or isinstance(value, str)
            and (not value or len(value) > 200)
            or not isinstance(label, str)
            or not 1 <= len(label) <= 200
        ):
            raise HTTPException(502, "siie_registration_invalid_catalog")
        if type(value) is int and value <= 0:
            continue  # Never expose a placeholder as a native identifier.
        if max_length and (
            item.get("admiteCarrera") is False or len(str(value)) > max_length
        ):
            continue  # No truncation/abbreviation of family program names.
        identity = (type(value), value)
        if identity not in seen:
            result.append({"value": value, "label": label})
            seen.add(identity)
    return result


def read(context=None, geo=None):
    params = {k: context[k] for k in ("idOferta", "idPeriodo")} if context else {}
    params.update(filters(geo or {}))
    response = source.request("catalogs", params)
    data = response["data"]
    if (
        type(data.get("idPeriodo")) is not int
        or data["idPeriodo"] <= 0
        or type(data.get("permiteCrearInscripcion")) is not bool
    ):
        raise HTTPException(502, "siie_registration_invalid_catalog")
    if context and data["idPeriodo"] != context["idPeriodo"]:
        raise HTTPException(409, "siie_offer_selection_changed")
    native = data.get("catalogos", data)
    if not isinstance(native, dict):
        raise HTTPException(502, "siie_registration_invalid_catalog")
    # Some producers group the dictionaries but keep fixed options alongside.
    native = {**native, "opciones": data.get("opciones", native.get("opciones", {}))}
    if "campos" in data:
        if not isinstance(data["campos"], list) or len(data["campos"]) > 200:
            raise HTTPException(502, "siie_registration_invalid_catalog")
        for item in data["campos"]:
            if not isinstance(item, dict):
                raise HTTPException(502, "siie_registration_invalid_catalog")
            path = item.get("campo")
            expected = MAPPING.get(path)
            if path in GEOGRAPHY:
                expected = (
                    "departamentos" if path.endswith(".Departamento") else "municipios",
                    GEOGRAPHY[path],
                )
            if expected and (item.get("catalogo"), item.get("propiedad")) != expected:
                raise HTTPException(502, "siie_registration_catalog_contract_changed")
    result = {}
    for path, (name, prop) in MAPPING.items():
        values = collection(native, name)
        if values is not None:
            result[path] = choices(
                values, prop, max_length=50 if path == "familiaCbn[].Carrera" else None
            )
    result["tipoId"] = result.get("estudiante.TipoId", [])
    countries = choices(native.get("paises", []))
    departments = choices(native.get("departamentos", []))
    department_names = (
        choices(native.get("departamentos", []), "valorTexto") if departments else []
    )
    municipal = native.get("municipios", {})
    if not isinstance(municipal, dict) or not isinstance(
        municipal.get("items", []), list
    ):
        raise HTTPException(502, "siie_registration_invalid_catalog")
    municipalities = choices(municipal.get("items", []), limit=100)
    municipal_text = choices(municipal.get("items", []), "valorTexto", limit=100)
    more = municipal.get("hayMas", False)
    next_offset = municipal.get("siguienteOffset")
    if (
        type(more) is not bool
        or more
        and (
            type(next_offset) is not int
            or not params.get("idDepartamento")
            or not params.get("idPais")
            or not params.get("offset", 0) < next_offset <= 1000000
        )
    ):
        raise HTTPException(502, "siie_registration_invalid_catalog")
    missing = [
        p
        for p in MAPPING
        if not result.get(p) and (p != "inscripcion.Id_Jornada" or context)
    ]
    if not countries:
        missing.append("paises")
    return {
        "items": result,
        "missing": missing,
        "countries": countries,
        "departments": departments,
        "department_values": [
            {"id": item["valor"], "value": item["valorTexto"]}
            for item in native.get("departamentos", [])
            if isinstance(item, dict)
            and type(item.get("valor")) is int
            and isinstance(item.get("valorTexto"), str)
        ],
        "department_names": department_names,
        "municipalities": municipalities,
        "municipal_text": municipal_text,
        "has_more": more,
        "next_offset": next_offset,
        "period_id": data["idPeriodo"],
        "allows_creation": data["permiteCrearInscripcion"],
        "correlation_id": response.get("correlation_id"),
    }


def final_choices(context, form, selections, kind):
    base = read(context)
    if not base["allows_creation"]:
        raise HTTPException(409, "siie_catalog_period_not_creatable")
    result = dict(base["items"])
    cache = {}
    for path, selection in locations(selections).items():
        canonical = schema_path(path)
        segments = path.split(".")
        value = form
        for part in segments:
            value = (
                value[int(part)]
                if isinstance(value, list) and part.isdigit() and int(part) < len(value)
                else value.get(part)
                if isinstance(value, dict)
                else None
            )
        if value is None or value == "":
            continue
        if "idPais" not in selection or (
            not canonical.endswith(".Departamento")
            and "idDepartamento" not in selection
        ):
            raise HTTPException(409, "siie_geography_selection_required")
        key = tuple(sorted(selection.items()))
        if key not in cache:
            cache[key] = read(context, selection)
        page = cache[key]
        result[path] = (
            page["department_names"]
            if canonical.endswith(".Departamento")
            else page["municipalities"]
            if GEOGRAPHY[canonical] == "valor"
            else page["municipal_text"]
        )
    if kind == "registration":
        work = form.get("informacionLaboral", {})
        if work.get("Departamento") and work.get("Municipio"):
            scopes = [
                selections.get("informacionLaboral." + name, {})
                for name in ("Departamento", "Municipio")
            ]
            if any(
                scopes[0].get(key) != scopes[1].get(key)
                for key in ("idPais", "idDepartamento")
            ):
                raise HTTPException(422, "siie_work_location_mismatch")
        for row in form.get("otrosEstudios", []):
            if row.get("Id_TipoEstudio"):
                ids = base["items"].get("otrosEstudios[].Id_TipoEstudio", [])
                selected = next(
                    (v for v in ids if v["value"] == row["Id_TipoEstudio"]), None
                )
                if not selected or selected["label"] != row.get("TituloCarrera"):
                    raise HTTPException(422, "siie_study_title_mismatch")
    return result
