"""Registration 2 native field contract. Catalog IDs are never guessed."""

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from app.institutional.siie_catalogs import GEOGRAPHY, MAPPING


def field(
    name, label, limit=100, *, optional=False, kind="text", options=None, catalog=None
):
    return {
        "name": name,
        "label": label,
        "max_length": limit,
        "required": not optional,
        "kind": kind,
        "options": options or [],
        "catalog": catalog,
    }


F = field
SCHEMA = [
    {
        "name": "estudiante",
        "label": "Datos del estudiante",
        "fields": [
            F("Id_DocEstudiante", "Documento", 16, kind="document"),
            F("TipoId", "Tipo de documento", kind="integer", catalog="tiposDocumento"),
            F(
                "Expedida",
                "Municipio de expedición",
                optional=True,
                kind="integer",
                catalog="municipios",
            ),
            F("Nombres", "Nombres", 40),
            F("PrimerApellido", "Primer apellido", 30),
            F("SegundoApellido", "Segundo apellido", 30, optional=True),
            F("Id_Genero", "Género", kind="integer", catalog="generos"),
            F(
                "EstadoCivil",
                "Estado civil",
                14,
                options=[
                    "SOLTERO(A)",
                    "CASADO(A)",
                    "UNIÓN LIBRE",
                    "SEPARADO(A)",
                    "VIUDO(A)",
                    "DIVORCIADO(A)",
                ],
            ),
            F("Direccion", "Dirección", 80),
            F(
                "Id_Poblacion",
                "Municipio de residencia",
                optional=True,
                kind="integer",
                catalog="municipios",
            ),
            F("Telefono", "Teléfono", 23),
            F("Celular", "Celular", 23),
            F("Mail", "Correo", 50, kind="email"),
            F("FechaNacimento", "Fecha de nacimiento", kind="date"),
            F(
                "CiudadNacimiento",
                "Municipio de nacimiento",
                50,
                optional=True,
                catalog="municipios",
            ),
            F(
                "GrupoSanguineo",
                "Grupo sanguíneo",
                2,
                optional=True,
                options=["O", "A", "B", "AB"],
            ),
            F("FactorRh", "Factor RH", 1, options=["+", "-"]),
            F(
                "Estrato",
                "Estrato",
                optional=True,
                kind="integer",
                options=[1, 2, 3, 4, 5, 6],
            ),
            F("Articulacion", "Articulación", 80, optional=True),
        ],
    },
    {
        "name": "acudiente",
        "label": "Acudiente o contacto de emergencia",
        "fields": [
            F("NombreAcudiente", "Nombres", 40),
            F("ApellidosAcudiente", "Apellidos", 30),
            F("Telefono", "Teléfono", 23),
            F("Celular", "Celular", 23),
            F("Mail", "Correo", 50, kind="email"),
            F("Ocupacion", "Ocupación", 50),
            F("DocumentoA", "Documento", 16, kind="document"),
        ],
    },
    {
        "name": "inscripcion",
        "label": "Jornada de inscripción",
        "fields": [F("Id_Jornada", "Jornada", kind="integer", catalog="jornadas")],
    },
    {
        "name": "estudiosSecundarios",
        "label": "Estudios secundarios",
        "fields": [
            F("Institucion", "Institución", 70),
            F(
                "Titulo",
                "Título",
                70,
                options=[
                    "BACHILLER ACADEMICO",
                    "BACHILLER TECNICO",
                    "BACHILLER PEDAGOGICO",
                ],
            ),
            F(
                "ultimoGrado",
                "Último grado",
                3,
                options=[str(n) + "°" for n in range(6, 12)],
            ),
            F("Año", "Fecha de terminación", kind="date"),
            F("Modalidad", "Modalidad", 20, optional=True, catalog="modalidades"),
            F("Municipio", "Municipio", 50, optional=True, catalog="municipios"),
        ],
    },
    {
        "name": "referencia",
        "label": "Referencia personal",
        "fields": [
            F("Nombres", "Nombre completo", 50),
            F("Direccion", "Dirección distinta a la del estudiante", 80),
            F("Telefono", "Teléfono", 23),
            F("ciudad", "Ciudad", 100),
            F("Celular", "Celular", 23, optional=True),
        ],
    },
    {
        "name": "socioeconomica",
        "label": "Información socioeconómica",
        "fields": [
            F(
                "CostodiaEstudios",
                "Quién costea los estudios",
                20,
                options=[
                    "INGRESOS PROPIOS",
                    "PADRES",
                    "FAMILIAR",
                    "FINANCIACIÓN",
                    "SIN INFORMACIÓN",
                    "FUNDACION CHILDREN",
                    "OTRO",
                ],
            ),
            F(
                "Becade",
                "Beca",
                40,
                options=["NINGUNA", "MinTic", "MinCit", "ICETEX", "COMUNA", "OTRO"],
            ),
            F("AfiliadoSisben", "Afiliación a Sisbén", 2, options=["SI", "NO"]),
            F("NivelSIS", "Nivel Sisbén", kind="integer", options=[1, 2, 3]),
            F("Discapacidad", "Discapacidad (NO si no aplica)", 200),
            F(
                "Prestamode",
                "Préstamo",
                30,
                optional=True,
                options=[
                    "NINGUNA",
                    "ENTIDAD BANCARIA",
                    "ENTIDAD PRIVADA",
                    "ENTIDAD PUBLICA",
                ],
            ),
            F("NombreEps", "EPS", 50, optional=True, catalog="eps"),
        ],
    },
    {
        "name": "padres",
        "label": "Padre o madre",
        "min_items": 1,
        "max_items": 2,
        "fields": [
            F("Nombres", "Nombres", 50),
            F("PrimerApellido", "Primer apellido", 25),
            F("SegundoApellido", "Segundo apellido", 25),
            F("Direccion", "Dirección", 100),
            F("Email", "Correo", 50, kind="email"),
            F("Celular", "Celular", 20),
            F("Parentesco", "Parentesco", 5, options=["PADRE", "MADRE"]),
        ],
    },
    {
        "name": "otrosEstudios",
        "label": "Otros estudios",
        "optional": True,
        "max_items": 3,
        "fields": [
            F("TituloCarrera", "Título o carrera", 80),
            F("NombreInstitucion", "Institución", 50),
            F("Municipio", "Municipio", 50, catalog="municipios"),
            F("ModEstdio", "Modalidad", 20, optional=True, catalog="modalidades"),
            F("Semestre", "Semestre", 6, optional=True),
            F("AñoTerminaion1", "Terminación", optional=True, kind="date"),
            F(
                "Id_TipoEstudio",
                "Tipo de estudio",
                optional=True,
                kind="integer",
                catalog="tiposEstudio",
            ),
        ],
    },
    {
        "name": "informacionLaboral",
        "label": "Información laboral",
        "optional": True,
        "fields": [
            F("NombreEmpresa", "Empresa", 50),
            F("TipoContrato", "Contrato", 50, optional=True),
            F(
                "Tiempo",
                "Tiempo",
                20,
                optional=True,
                options=["COMPLETO", "MEDIO TIEMPO", "POR HORAS", "DÍAS FESTIVOS"],
            ),
            F("Cargo", "Cargo", 50, optional=True),
            F("DireccionEmpresa", "Dirección", 80, optional=True),
            F("Telefono", "Teléfono", 23, optional=True),
            F("Municipio", "Municipio", 50, optional=True, catalog="municipios"),
            F(
                "Departamento",
                "Departamento",
                50,
                optional=True,
                catalog="departamentos",
            ),
        ],
    },
    {
        "name": "familiaCbn",
        "label": "Familiares en CBN",
        "optional": True,
        "max_items": 2,
        "fields": [
            F("NombreCompletoEst", "Familiar estudiante", 60, optional=True),
            F("NombreFamiliar", "Familiar trabajador", 60, optional=True),
            F("Carrera", "Carrera", 50, optional=True),
            F("ParentescoEst", "Parentesco con estudiante", 30, optional=True),
            F("Cargo", "Cargo", 30, optional=True),
            F("Parentesco", "Parentesco con trabajador", 15, optional=True),
        ],
    },
    {
        "name": "grupoEspecial",
        "label": "Grupo étnico",
        "optional": True,
        "fields": [
            F(
                "MinoriaEtnicas",
                "Grupo",
                50,
                options=[
                    "ARHUACO",
                    "KOGUI",
                    "AFRO",
                    "WAYUU",
                    "PALENQUERO",
                    "CHIMILA",
                    "PIAROA",
                    "MUISCA",
                    "ROOM",
                    "OTRO",
                ],
            ),
            F("Otro", "Cuál", 50, optional=True),
        ],
    },
]
APPLICANT = [
    F("documento", "Documento", 16, kind="document"),
    F("tipoId", "Tipo de documento", kind="integer", catalog="tiposDocumento"),
    F("nombres", "Nombres", 100),
    F("primerApellido", "Primer apellido", 30),
    F("segundoApellido", "Segundo apellido", 30, optional=True),
    F("telefono", "Teléfono", 50, optional=True),
    F("celular", "Celular", 50),
    F("correo", "Correo", 50, kind="email"),
]
for _section in SCHEMA:
    for _field in _section["fields"]:
        _path = _section["name"] + ("[]" if "max_items" in _section else "") + "." + _field["name"]
        if _path in MAPPING or _path in GEOGRAPHY:
            _field["catalog"] = _path
            _field["geography"] = "department" if _path.endswith(".Departamento") else "municipality" if _path in GEOGRAPHY else None
APPLICANT[1]["catalog"] = "tipoId"
CATALOGS = sorted({f["catalog"] for s in SCHEMA for f in s["fields"] if f["catalog"]})


def validate_fields(fields, values, *, final=False, catalogs=None, prefix=""):
    if not isinstance(values, dict) or set(values) - {f["name"] for f in fields}:
        raise HTTPException(422, "siie_form_invalid_fields")
    for f in fields:
        value = values.get(f["name"])
        if value is None or value == "":
            if final and f["required"]:
                raise HTTPException(422, "siie_form_required_fields")
            continue
        if f["kind"] == "integer":
            if type(value) is not int or not 1 <= value <= 2147483647:
                raise HTTPException(422, "siie_form_invalid_fields")
        elif (
            not isinstance(value, str)
            or len(value) > f["max_length"]
            or any(ord(c) < 32 for c in value)
        ):
            raise HTTPException(422, "siie_form_invalid_fields")
        elif f["kind"] == "document" and not re.fullmatch(r"[A-Za-z0-9]{1,16}", value):
            raise HTTPException(422, "siie_form_invalid_document")
        elif f["kind"] == "document" and re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", value, re.I):
            raise HTTPException(422, "siie_form_invalid_document")
        elif f["kind"] == "email" and not re.fullmatch(
            r"[^\s@]+@[^\s@]+\.[^\s@]+", value
        ):
            raise HTTPException(422, "siie_form_invalid_email")
        elif f["kind"] == "date":
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            except ValueError:
                raise HTTPException(422, "siie_form_invalid_date") from None
        if f["options"] and not f["catalog"] and value not in f["options"]:
            raise HTTPException(422, "siie_form_invalid_option")
        if final and f["catalog"]:
            field_path = prefix + f["name"]
            choices = (catalogs or {}).get(field_path, (catalogs or {}).get(f["catalog"], []))
            if f.get("geography") and field_path not in (catalogs or {}):
                raise HTTPException(409, "siie_geography_selection_required")
            if not choices:
                raise HTTPException(409, "siie_registration_catalogs_required")
            if not any(type(value) is type(v["value"]) and value == v["value"] for v in choices):
                raise HTTPException(422, "siie_form_catalog_changed")


def validate(kind, values, *, final=False, catalogs=None, program_name=""):
    if not isinstance(values, dict):
        raise HTTPException(422, "siie_form_invalid_fields")
    if kind == "applicant":
        validate_fields(APPLICANT, values, final=final, catalogs=catalogs)
        return
    if kind != "registration" or set(values) - {s["name"] for s in SCHEMA} - {
        "aceptaTratamientoDatos",
        "condicion",
    }:
        raise HTTPException(422, "siie_form_invalid_fields")
    for s in SCHEMA:
        value = values.get(s["name"])
        if value is None:
            if s["name"] in values:
                raise HTTPException(422, "siie_form_invalid_fields")
            if final and not s.get("optional"):
                raise HTTPException(422, "siie_form_required_fields")
            continue
        if "max_items" in s:
            if (
                not isinstance(value, list)
                or not s.get("min_items", 0 if s.get("optional") else 1) <= len(value) <= s["max_items"]
            ):
                raise HTTPException(422, "siie_form_invalid_fields")
            for index, row in enumerate(value):
                validate_fields(s["fields"], row, final=final, catalogs=catalogs, prefix=f"{s['name']}.{index}.")
        else:
            validate_fields(s["fields"], value, final=final, catalogs=catalogs, prefix=s["name"] + ".")
    condition = values.get("condicion", "")
    if not isinstance(condition, str) or len(condition) > 4000:
        raise HTTPException(422, "siie_form_invalid_fields")
    if (
        "aceptaTratamientoDatos" in values
        and type(values["aceptaTratamientoDatos"]) is not bool
    ):
        raise HTTPException(422, "siie_form_invalid_fields")
    if final:
        if values.get("aceptaTratamientoDatos") is not True:
            raise HTTPException(422, "siie_consent_required")
        student = values["estudiante"]
        today = datetime.now(ZoneInfo("America/Bogota")).date()
        birth = date.fromisoformat(student["FechaNacimento"])
        age = (
            today.year
            - birth.year
            - ((today.month, today.day) < (birth.month, birth.day))
        )
        if birth >= today or age > 120:
            raise HTTPException(422, "siie_form_invalid_birth_date")
        if age < 16 and "PREICFES" not in re.sub(r"[^A-Z]", "", program_name.upper()):
            raise HTTPException(409, "siie_minimum_age_review_required")
        if (
            student["Direccion"].strip().casefold()
            == values["referencia"]["Direccion"].strip().casefold()
        ):
            raise HTTPException(422, "siie_reference_address_must_differ")
        parents = [v["Parentesco"] for v in values["padres"]]
        if len(set(parents)) != len(parents):
            raise HTTPException(422, "siie_duplicate_parent")
        if any(
            not v.get("NombreCompletoEst") and not v.get("NombreFamiliar")
            for v in values.get("familiaCbn", [])
        ):
            raise HTTPException(422, "siie_family_name_required")
