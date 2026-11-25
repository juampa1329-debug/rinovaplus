import copy

import httpx2 as httpx
import pytest
from fastapi import HTTPException

from app.institutional import siie_catalogs as catalogs, siie_forms as forms
from app.institutional import siie_registration_client as client


def native_data():
    def row(value, name=None):
        return {"valor": value, "nombre": name or str(value)}

    return {
        "idPeriodo": 17,
        "permiteCrearInscripcion": True,
        "tiposDocumento": [row(1, "CC")],
        "generos": [row(2, "Género de ensayo")],
        "jornadas": [row(9, "Jornada de ensayo")],
        "modalidades": [row("PRESENCIAL")],
        "tiposEstudio": [row(7, "TECNICO")],
        "programasFamilia": [
            row("PROGRAMA DE ENSAYO"),
            {**row("X" * 51), "admiteCarrera": False},
        ],
        "paises": [row(1, "País de ensayo")],
        "departamentos": [
            {
                **row(47, "Departamento de ensayo"),
                "valorTexto": "Departamento de ensayo",
            }
        ],
        "municipios": {
            "items": [{**row(47001, "Municipio de ensayo"), "valorTexto": "47001"}],
            "hayMas": False,
            "siguienteOffset": None,
        },
        "opciones": {
            name: [row(value)]
            for name, value in {
                "estadosCiviles": "SOLTERO(A)",
                "gruposSanguineos": "O",
                "factoresRh": "+",
                "estratos": 2,
                "gradosSecundaria": "11°",
                "titulosSecundaria": "BACHILLER ACADEMICO",
                "semestresCursados": "2",
                "tiemposLaborales": "COMPLETO",
                "costeaEstudios": "PADRES",
                "financiadores": "MinTic",
                "prestamos": "NINGUNA",
                "siNo": "NO",
                "nivelesSisben": 1,
                "eps": "EPS DE ENSAYO",
                "gruposEtnicos": "OTRO",
                "parentescosPadres": "PADRE",
            }.items()
        },
        "campos": [
            {
                "campo": "estudiante.CiudadNacimiento",
                "catalogo": "municipios",
                "propiedad": "valorTexto",
                "tipo": "string",
            }
        ],
    }


@pytest.fixture
def official(monkeypatch):
    data, calls = native_data(), []

    def remote(kind, payload):
        assert kind == "catalogs"
        calls.append(dict(payload))
        return {
            "state": "confirmed",
            "data": copy.deepcopy(data),
            "correlation_id": "fixture-support",
        }

    monkeypatch.setattr(catalogs.source, "request", remote)
    return data, calls


def test_r7_maps_native_ids_text_values_and_labels_without_truncating_names(official):
    data, calls = official
    result = catalogs.read(
        {"idOferta": 12, "idPeriodo": 17}, {"idPais": 1, "idDepartamento": 47}
    )
    assert calls == [
        {"idOferta": 12, "idPeriodo": 17, "idPais": 1, "idDepartamento": 47}
    ]
    assert result["missing"] == []
    assert result["items"]["socioeconomica.NombreEps"] == [
        {"value": "EPS DE ENSAYO", "label": "EPS DE ENSAYO"}
    ]
    assert result["items"]["estudiosSecundarios.Modalidad"][0]["value"] == "PRESENCIAL"
    assert result["items"]["otrosEstudios[].Id_TipoEstudio"][0]["value"] == 7
    assert result["items"]["otrosEstudios[].TituloCarrera"][0]["value"] == "TECNICO"
    assert result["municipalities"][0]["value"] == 47001
    assert result["municipal_text"][0]["value"] == "47001"
    assert result["department_names"][0]["value"] == "Departamento de ensayo"
    assert len(result["items"]["familiaCbn[].Carrera"]) == 1
    assert data["programasFamilia"][1]["valor"] == "X" * 51


@pytest.mark.parametrize(
    "filters",
    [
        {"offset": 0},
        {"q": "Municipio"},
        {"idDepartamento": 47},
        {"idPais": 0},
        {"idPais": True},
        {"idPais": "1"},
        {"idPais": 1, "idDepartamento": 47, "offset": -1},
        {"idPais": 1, "idDepartamento": 47, "q": "x" * 81},
        {"unknown": 1},
    ],
)
def test_invalid_or_incomplete_geography_filters_never_reach_source(official, filters):
    _, calls = official
    with pytest.raises(HTTPException, match="siie_catalog_filters_invalid"):
        catalogs.read(None, filters)
    assert calls == []


def test_paginated_municipal_search_keeps_exact_geographic_scope(official):
    data, calls = official
    data["municipios"].update(hayMas=True, siguienteOffset=200)
    result = catalogs.read(
        None, {"idPais": 1, "idDepartamento": 47, "q": "Municipio", "offset": 100}
    )
    assert result["has_more"] and result["next_offset"] == 200
    assert calls[-1] == {
        "idPais": 1,
        "idDepartamento": 47,
        "q": "Municipio",
        "offset": 100,
    }
    data["municipios"]["siguienteOffset"] = 100
    with pytest.raises(HTTPException, match="siie_registration_invalid_catalog"):
        catalogs.read(None, calls[-1])


def test_final_validation_uses_separate_scopes_and_current_catalogs(official):
    _, calls = official
    context = {"idOferta": 12, "idPeriodo": 17}
    form = {"estudiante": {"Expedida": 47001, "CiudadNacimiento": "47001"}}
    scope = {"idPais": 1, "idDepartamento": 47, "q": "Municipio", "offset": 0}
    result = catalogs.final_choices(
        context,
        form,
        {"estudiante.Expedida": scope, "estudiante.CiudadNacimiento": scope},
        "registration",
    )
    # Same selector page is fetched once in the final review, never per field.
    assert len(calls) == 2
    assert type(result["estudiante.Expedida"][0]["value"]) is int
    assert type(result["estudiante.CiudadNacimiento"][0]["value"]) is str
    student_fields = forms.SCHEMA[0]["fields"]
    forms.validate_fields(student_fields, form["estudiante"], final=False)
    for field in [v for v in student_fields if v["name"] in form["estudiante"]]:
        forms.validate_fields(
            [field],
            {field["name"]: form["estudiante"][field["name"]]},
            final=True,
            catalogs=result,
            prefix="estudiante.",
        )
    with pytest.raises(HTTPException, match="siie_geography_selection_required"):
        forms.validate_fields(
            [student_fields[2]],
            {"Expedida": 47001},
            final=True,
            catalogs={},
            prefix="estudiante.",
        )


def test_historical_period_and_changed_study_title_stop_before_registration(official):
    data, _ = official
    context = {"idOferta": 12, "idPeriodo": 17}
    data["permiteCrearInscripcion"] = False
    with pytest.raises(HTTPException, match="siie_catalog_period_not_creatable"):
        catalogs.final_choices(context, {}, {}, "registration")
    data["permiteCrearInscripcion"] = True
    with pytest.raises(HTTPException, match="siie_study_title_mismatch"):
        catalogs.final_choices(
            context,
            {"otrosEstudios": [{"Id_TipoEstudio": 7, "TituloCarrera": "Inventado"}]},
            {},
            "registration",
        )


def test_changed_mapping_metadata_is_not_used_to_guess_another_value(official):
    data, _ = official
    data["campos"][0]["propiedad"] = "nombre"
    with pytest.raises(
        HTTPException, match="siie_registration_catalog_contract_changed"
    ):
        catalogs.read()


def test_employment_department_and_municipality_must_share_the_selected_scope(official):
    with pytest.raises(HTTPException, match="siie_work_location_mismatch"):
        catalogs.final_choices(
            {"idOferta": 12, "idPeriodo": 17},
            {
                "informacionLaboral": {
                    "Departamento": "Departamento de ensayo",
                    "Municipio": "47001",
                }
            },
            {
                "informacionLaboral.Departamento": {"idPais": 1, "idDepartamento": 47},
                "informacionLaboral.Municipio": {"idPais": 1, "idDepartamento": 48},
            },
            "registration",
        )


@pytest.mark.parametrize("section", ["otrosEstudios", "familiaCbn"])
def test_optional_arrays_may_be_empty_but_not_null(section):
    forms.validate("registration", {section: []})
    with pytest.raises(HTTPException, match="siie_form_invalid_fields"):
        forms.validate("registration", {section: None})


@pytest.mark.parametrize("value", ["CON", "prn", "AUX", "NUL", "COM1", "LPT9"])
def test_document_reserved_by_windows_cannot_become_a_storage_path(value):
    with pytest.raises(HTTPException, match="siie_form_invalid_document"):
        forms.validate("applicant", {"documento": value})


def test_conflict_retains_only_numeric_conciliation_references():
    assert client.reconciliation_references(
        {
            "data": {
                "items": [
                    {
                        "idEstudiante": 12,
                        "documento": "PRIVATE",
                        "nombre": "PRIVATE",
                        "idInscripcion": True,
                    }
                ]
            }
        }
    ) == [{"idEstudiante": 12}]
    assert client.support_metadata(
        {"Retry-After": "60", "X-RateLimit-Limit": "120", "X-RateLimit-Remaining": "3"}
    ) == {"retry_after": 60, "rate_limit": 120, "rate_remaining": 3}


def test_catalog_reads_use_one_protected_get_and_keep_rate_metadata(monkeypatch):
    monkeypatch.setattr(
        client,
        "endpoint",
        lambda _: (
            "https://siie.test/SIIEWebPlus/Api/CRM/v1/CatalogosInscripcion.aspx",
            {"X-API-Key": "fixture-only"},
        ),
    )
    calls = []

    def remote(request):
        calls.append(request)
        assert (
            request.method == "GET" and request.headers["X-API-Key"] == "fixture-only"
        )
        return httpx.Response(
            200,
            json={"status": "ok", "data": native_data()},
            headers={"X-Correlation-ID": "support-r7", "X-RateLimit-Remaining": "119"},
        )

    result = client.request(
        "catalogs", {"idPais": 1}, transport=httpx.MockTransport(remote)
    )
    assert len(calls) == 1 and result["rate_remaining"] == 119
    assert result["correlation_id"] == "support-r7"


def test_read_429_preserves_retry_after_without_an_automatic_retry(monkeypatch):
    monkeypatch.setattr(
        client,
        "endpoint",
        lambda _: (
            "https://siie.test/SIIEWebPlus/Api/CRM/v1/CatalogosInscripcion.aspx",
            {},
        ),
    )
    calls = []

    def remote(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "24"})

    with pytest.raises(HTTPException) as error:
        client.request("catalogs", {}, transport=httpx.MockTransport(remote))
    assert error.value.status_code == 429 and error.value.headers["Retry-After"] == "24"
    assert len(calls) == 1
