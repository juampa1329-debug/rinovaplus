"""Provider-contract fixtures, never real SIIE rows or credentials."""

from contextlib import contextmanager
from datetime import datetime, timezone

import httpx2 as httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.institutional import siie_api as siie


@pytest.fixture(autouse=True)
def configuration(monkeypatch):
    monkeypatch.setenv("SIIE_API_BASE_URL", "https://siie.example.test/SIIEWebPlus")
    monkeypatch.setenv("SIIE_API_HOSTS", "siie.example.test")
    monkeypatch.setenv("SIIE_API_TOKEN", "single-fixture-not-a-real-key-12345678")
    monkeypatch.delenv("SIIE_CATALOG_API_TOKEN", raising=False)
    monkeypatch.delenv("SIIE_ADMISSIONS_API_TOKEN", raising=False)


def stamp(**fields):
    return dict(
        schema_version="siie-crm-commercial-v1",
        source_system="DBSIIE",
        source_revision="sha256:" + "a" * 64,
        generated_at=datetime.now(timezone.utc).isoformat(),
        **fields,
    )


def response(value, status=200):
    return httpx.MockTransport(lambda r: httpx.Response(status, json=value))


def test_failed_query_preserves_only_its_current_safe_provider_reference():
    transport = httpx.MockTransport(lambda r: httpx.Response(503, json={"code": "catalog_unavailable"}, headers={"X-Correlation-ID": "current-offer-reference"}))
    with pytest.raises(HTTPException) as failure:
        siie.read("offer", {"offer_id": "900-n1"}, transport=transport)
    assert failure.value.headers["X-SIIE-Correlation-ID"] == "current-offer-reference"


def test_missing_single_key_disables_all_reads_and_ignores_old_admissions_key(monkeypatch):
    monkeypatch.delenv("SIIE_API_TOKEN")
    monkeypatch.setenv("SIIE_ADMISSIONS_API_TOKEN", "old-key-must-not-be-used-1234567890")
    assert siie.status()["api_configured"] is False
    assert siie.status()["admissions_configured"] is False
    for route in ("programs", "periods", "students"):
        with pytest.raises(HTTPException, match="siie_not_configured"):
            siie.read(
                route, transport=httpx.MockTransport(lambda r: pytest.fail("network"))
            )


def test_real_aspx_path_header_and_opaque_cursor_are_preserved():
    def remote(request):
        assert request.method == "GET"
        assert request.url.path == "/SIIEWebPlus/Api/CRM/v1/Commercial/Programs.aspx"
        assert request.url.params["cursor"] == "opaque+/=cursor"
        assert request.headers["X-API-Key"].startswith("single-fixture")
        assert (
            "Authorization" not in request.headers and "Origin" not in request.headers
        )
        return httpx.Response(
            200,
            json=stamp(
                items=[],
                next_cursor=None,
                pagination="keyset_live_catalog",
                period_id="2",
                offered_period_id="2",
            ),
            headers={"X-Correlation-ID": "fixture-request"},
        )

    result = siie.read(
        "programs", {"cursor": "opaque+/=cursor"}, transport=httpx.MockTransport(remote)
    )
    assert result["correlation_id"] == "fixture-request"
    assert result["saved"] is False


@pytest.mark.parametrize("route", ["programs", "periods", "students"])
def test_single_key_is_used_for_every_scope_without_second_credential(monkeypatch, route):
    monkeypatch.setenv("SIIE_CATALOG_API_TOKEN", "old-catalog-never-send-123456789012345")
    monkeypatch.setenv("SIIE_ADMISSIONS_API_TOKEN", "old-admissions-never-send-1234567890")
    seen = []

    def remote(request):
        seen.append(request)
        assert request.method == "GET"
        assert request.headers["X-API-Key"] == "single-fixture-not-a-real-key-12345678"
        assert "Authorization" not in request.headers
        # An access refusal must not cause a retry with either old credential.
        return httpx.Response(401)

    with pytest.raises(HTTPException, match="siie_catalog_access_rejected"):
        siie.read(route, transport=httpx.MockTransport(remote))
    assert len(seen) == 1
    state = siie.status()
    assert state["api_configured"] and state["admissions_configured"]
    assert state["credential_mode"] == "unified"
    assert "fixture" not in str(state) and "never-send" not in str(state)


@pytest.mark.parametrize("key", ["", "short", "x" * 31, "x" * 32 + "\ninside"])
def test_invalid_primary_key_cannot_fall_back_to_old_credentials(monkeypatch, key):
    monkeypatch.setenv("SIIE_API_TOKEN", key)
    monkeypatch.setenv("SIIE_CATALOG_API_TOKEN", "old-fixture-key-never-send-1234567890")
    expected = "siie_not_configured" if not key else "siie_credential_invalid"
    with pytest.raises(HTTPException, match=expected):
        siie.read(
            "periods", transport=httpx.MockTransport(lambda r: pytest.fail("network"))
        )


def test_old_catalog_variable_is_temporary_single_key_compatibility(monkeypatch):
    monkeypatch.delenv("SIIE_API_TOKEN")
    monkeypatch.setenv("SIIE_CATALOG_API_TOKEN", "legacy-fixture-original-key-1234567890")

    def remote(request):
        assert request.headers["X-API-Key"] == "legacy-fixture-original-key-1234567890"
        return httpx.Response(200, json={"status": "ok", "data": {"items": []}})

    assert siie.read("periods", transport=httpx.MockTransport(remote))["data"]["items"] == []
    assert siie.status()["credential_mode"] == "legacy_catalog"


@pytest.mark.parametrize(
    "route,values",
    [
        ("student", {}),
        ("applicant", {"idPeriodo": "1"}),
        ("offers", {"program_id": True}),
        ("offers", {"program_id": "2147483648"}),
        ("offer", {"offer_id": "1"}),
        ("offer", {"offer_id": "1-n0"}),
        ("offer", {"offer_id": "1-n12345"}),
        ("offer", {"offer_id": "../../1-n1"}),
        ("history", {"idPeriodo": "1", "idAspirante": "2", "offset": "1000001"}),
        ("applicants", {"idPeriodo": "1", "q": "a" * 101}),
        ("programs", {"cursor": "a" * 129}),
        ("programs", {"url": "https://evil.invalid"}),
        ("Seguimientos.aspx", {}),
    ],
)
def test_parameters_fail_before_network(route, values):
    with pytest.raises(HTTPException, match="siie_invalid_parameter"):
        siie.read(
            route,
            values,
            transport=httpx.MockTransport(lambda r: pytest.fail("network")),
        )


def test_incomplete_offer_retains_financial_source_but_never_builds_agent_draft():
    partial = stamp(
        offer_id="900006-n1",
        program_id="900003",
        quotable=False,
        campus_id=None,
        commercial={
            "price_cop": 1000000,
            "price_scope": "semester_tuition_only",
            "requirements": None,
            "financial_plans": [None],
        },
    )
    result = siie.read(
        "offer",
        {"offer_id": "900006-n1"},
        transport=response(
            {
                "code": "source_data_incomplete",
                "quotable": False,
                "data_quality": [
                    {
                        "field": "campus_id",
                        "code": "source_relationship_missing",
                        "message": "Falta sede",
                    }
                ],
                "partial_offer": partial,
            },
            422,
        ),
    )["data"]
    assert result["quotable"] is False and result["complete"] is False
    assert result["offer"]["commercial"]["price_cop"] == 1000000
    assert result["siie_written"] is False and result["saved"] is False
    assert "draft" not in result


@pytest.mark.parametrize(
    "change",
    [
        {"offer_id": "2-n1"},
        {"generated_at": "2020-01-01T00:00:00Z"},
        {"generated_at": "2026-11-18T00:00:00"},
        {"source_revision": "not-hash"},
    ],
)
def test_offer_identity_and_freshness_are_checked(change):
    payload = stamp(offer_id="1-n1", quotable=False, **{})
    payload.update(change)
    with pytest.raises(HTTPException):
        siie.read(
            "offer",
            {"offer_id": "1-n1"},
            transport=response(
                {
                    "code": "source_data_incomplete",
                    "quotable": False,
                    "partial_offer": payload,
                    "data_quality": [],
                },
                422,
            ),
        )


def test_catalog_pagination_bound_to_program_and_period():
    payload = stamp(
        program_id="1",
        period_id="2",
        items=[],
        next_cursor=None,
        pagination="keyset_live_catalog",
    )
    assert (
        siie.read(
            "offers", {"program_id": "1", "period_id": "2"}, transport=response(payload)
        )["data"]["items"]
        == []
    )
    with pytest.raises(HTTPException, match="siie_catalog_stale_or_mismatched"):
        siie.read(
            "offers", {"program_id": "3", "period_id": "2"}, transport=response(payload)
        )


def test_admissions_envelope_and_current_period_binding():
    def remote(request):
        assert request.headers["X-API-Key"].startswith("single-fixture")
        assert request.url.params["idPeriodo"] == "1"
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "data": {
                    "aspirante": {
                        "idAspirante": 2,
                        "idPeriodo": 1,
                        "confirmadoOrigen": True,
                    }
                },
            },
        )

    result = siie.read(
        "applicant",
        {"idPeriodo": "1", "idAspirante": "2"},
        transport=httpx.MockTransport(remote),
    )
    assert result["data"]["aspirante"]["confirmadoOrigen"] is True
    with pytest.raises(HTTPException, match="siie_catalog_stale_or_mismatched"):
        siie.read(
            "applicant",
            {"idPeriodo": "1", "idAspirante": "3"},
            transport=httpx.MockTransport(remote),
        )


@pytest.mark.parametrize(
    "status,error",
    [
        (301, "siie_catalog_unavailable"),
        (401, "siie_catalog_access_rejected"),
        (403, "siie_catalog_access_rejected"),
        (404, "siie_reference_not_found"),
        (429, "siie_rate_limited"),
        (503, "siie_catalog_unavailable"),
    ],
)
def test_provider_errors_are_sanitized_without_retry_or_credentials(status, error):
    with pytest.raises(HTTPException, match=error) as raised:
        siie.read(
            "periods", transport=response({"message": "private server detail"}, status)
        )
    assert "private" not in str(raised.value.detail)


@pytest.mark.parametrize(
    "payload",
    [b"not json", b"NaN", b"[]", b'{"x":' + b'"' + b"a" * 524288 + b'"}'],
    ids=["invalid-json", "nan", "array", "oversized"],
)
def test_malformed_and_oversize_responses_are_rejected(payload):
    with pytest.raises(HTTPException, match="siie_catalog_invalid_response"):
        siie.read(
            "periods",
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, content=payload)
            ),
        )


def test_unapproved_host_is_not_contacted(monkeypatch):
    monkeypatch.setenv("SIIE_API_BASE_URL", "https://evil.invalid")
    with pytest.raises(HTTPException, match="siie_catalog_endpoint_invalid"):
        siie.read(
            "periods", transport=httpx.MockTransport(lambda r: pytest.fail("network"))
        )


def test_personal_data_not_returned_if_authority_revoked_during_io(monkeypatch):
    class Service:
        calls = 0

        @contextmanager
        def transaction(self):
            self.calls += 1
            if self.calls == 2:
                raise HTTPException(403, "permission_denied")
            yield

    app = FastAPI()
    service = Service()
    siie.install(app, service)
    monkeypatch.setattr(
        siie, "read", lambda *a: {"data": {"private_fixture": "never return"}}
    )
    result = TestClient(app).get("/api/v1/agents/siie/applicants?idPeriodo=1")
    assert result.status_code == 403 and "private_fixture" not in result.text


def test_only_get_routes_installed_and_duplicate_parameters_rejected(monkeypatch):
    class Service:
        @contextmanager
        def transaction(self):
            yield

    app = FastAPI()
    siie.install(app, Service())
    client = TestClient(app)
    monkeypatch.setattr(siie, "read", lambda *a: pytest.fail("network"))
    assert (
        client.get("/api/v1/agents/siie/programs?cursor=a&cursor=b").status_code == 422
    )
    assert client.post("/api/v1/agents/siie/applicants").status_code == 405
    assert client.get("/api/v1/agents/siie/unknown").status_code == 404


def test_incomplete_offer_without_program_identity_still_cannot_be_imported():
    from app.institutional.siie_catalog import preview

    payload = {
        "code": "source_data_incomplete",
        "quotable": False,
        "partial_offer": stamp(offer_id="1-n1", quotable=False),
        "data_quality": [],
    }
    with pytest.raises(HTTPException, match="siie_catalog_invalid_response"):
        preview("1-n1", transport=response(payload, 422))


def test_offered_period_can_be_future_and_not_academically_active():
    payload = stamp(
        period_id="7",
        offered_period_id="7",
        offered_period_source="GEParametros:38",
        items=[],
        next_cursor=None,
        pagination="keyset_live_catalog",
    )
    assert (
        siie.read("programs", transport=response(payload))["data"]["period_id"] == "7"
    )
    periods = {
        "status": "ok",
        "data": {
            "items": [{"id": 7, "nombre": "Ofrecido fixture", "activo": False}],
            "idPeriodoOfrecido": 7,
            "idPeriodoActivo": 6,
            "requiereSeleccion": False,
        },
    }
    assert (
        siie.read("periods", transport=response(periods))["data"]["idPeriodoOfrecido"]
        == 7
    )
    with pytest.raises(HTTPException, match="siie_catalog_stale_or_mismatched"):
        siie.read("programs", {"period_id": "6"}, transport=response(payload))


def test_base_catalog_without_period_is_available_without_claiming_offered_period():
    result = siie.read(
            "programs",
            transport=response(
                stamp(items=[], next_cursor=None, pagination="keyset_live_catalog")
            ),
        )["data"]
    assert result["period_id"] is None
    assert result["period_binding_status"] == "unconfirmed"


@pytest.mark.parametrize(
    "route", ["applicants", "students", "filters", "student_filters"]
)
def test_offered_period_may_be_omitted_in_new_reads(route):
    assert siie.parameters(route, {}) == {}


def test_students_preserve_state_zero_contacts_and_use_single_key():
    item = {
        "idEstudiante": 9,
        "idMatricula": 8,
        "idPeriodo": 7,
        "nombre": "Persona fixture",
        "telefono": None,
        "celular": None,
        "correo": "fixture@example.invalid",
        "idEstadoMatricula": 0,
        "estadoMatricula": "Inscrito",
        "idPersona": None,
        "idAspirante": None,
    }

    def remote(request):
        assert request.url.path.endswith("/Estudiantes.aspx")
        assert request.url.params["idEstadoMatricula"] == "0"
        assert request.headers["X-API-Key"].startswith("single-fixture")
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "data": {
                    "idPeriodo": 7,
                    "items": [item],
                    "offset": 0,
                    "limit": 25,
                    "hasMore": False,
                },
            },
        )

    result = siie.read(
        "students",
        {"idEstadoMatricula": "0", "idPeriodo": "7"},
        transport=httpx.MockTransport(remote),
    )
    assert result["data"]["items"][0] == item
    assert siie.status()["students_supported"] is True


@pytest.mark.parametrize("value", ["-1", "2147483648", True, "x"])
def test_invalid_student_state_rejected_before_io(value):
    with pytest.raises(HTTPException, match="siie_invalid_parameter"):
        siie.read(
            "students",
            {"idEstadoMatricula": value},
            transport=httpx.MockTransport(lambda r: pytest.fail("network")),
        )


def test_unknown_student_state_not_rewritten_as_active():
    item = {
        "idEstudiante": 9,
        "idMatricula": 8,
        "idPeriodo": 7,
        "idEstadoMatricula": 91,
        "estadoMatricula": None,
        "requiereRevisionEstado": True,
    }
    payload = {
        "status": "ok",
        "data": {
            "idPeriodo": 7,
            "items": [item],
            "offset": 0,
            "limit": 25,
            "hasMore": False,
        },
    }
    result = siie.read("students", {"idPeriodo": "7"}, transport=response(payload))
    assert result["data"]["items"][0] == item


@pytest.mark.parametrize("change", [{"idPeriodo": 8}, {"idEstudiante": 10}])
def test_student_detail_rejects_foreign_identity_or_period(change):
    enrollment = {"idMatricula": 8, "idPeriodo": 7, "idEstudiante": 9, **change}
    payload = {
        "status": "ok",
        "data": {
            "idPeriodo": 7,
            "estudiante": {"idEstudiante": 9},
            "matriculas": [enrollment],
        },
    }
    with pytest.raises(HTTPException, match="siie_catalog_stale_or_mismatched"):
        siie.read(
            "student",
            {"idEstudiante": "9", "idPeriodo": "7"},
            transport=response(payload),
        )


def test_student_detail_and_filters_keep_missing_person_links_null():
    payload = {
        "status": "ok",
        "data": {
            "idPeriodo": 7,
            "estudiante": {"idEstudiante": 9, "idPersona": None, "idAspirante": None},
            "matriculas": [{"idMatricula": 8, "idPeriodo": 7, "jornada": None}],
        },
    }
    result = siie.read("student", {"idEstudiante": "9"}, transport=response(payload))
    assert result["data"]["estudiante"]["idAspirante"] is None
    filters = {
        "status": "ok",
        "data": {
            "idPeriodo": 7,
            "programas": [],
            "jornadas": [],
            "niveles": [],
            "estadosMatricula": [{"idEstadoMatricula": 0, "nombre": "Inscrito"}],
        },
    }
    assert (
        siie.read("student_filters", {"idPeriodo": "7"}, transport=response(filters))[
            "data"
        ]["estadosMatricula"][0]["idEstadoMatricula"]
        == 0
    )


@pytest.mark.parametrize(
    "code,expected",
    [
        ("offered_period_unavailable", "siie_offered_period_unavailable"),
        ("invalid_cursor", "siie_cursor_changed"),
        ("students_unavailable", "siie_students_unavailable"),
        ("api_credential_not_configured", "siie_source_credential_configuration"),
        ("api_credential_config_invalid", "siie_source_credential_configuration"),
        ("api_credential_config_conflict", "siie_source_credential_configuration"),
    ],
)
def test_updated_source_errors_are_explained_without_private_messages(code, expected):
    with pytest.raises(HTTPException, match=expected):
        siie.read(
            "students",
            transport=response({"code": code, "message": "private SQL detail"}, 503),
        )


def test_offered_offer_with_null_campus_and_validities_stays_inspection_only():
    partial = stamp(
        offer_id="8-n1",
        quotable=False,
        campus_id=None,
        active=True,
        period_active=False,
        offered_period_id="7",
        commercial={
            "price_valid_from": None,
            "price_valid_until": None,
            "financial_plans": [],
        },
    )
    payload = {
        "code": "source_data_incomplete",
        "quotable": False,
        "partial_offer": partial,
        "data_quality": [
            {
                "field": "commercial.requirements",
                "code": "admission_requirements_missing",
                "message": "Falta fuente",
            }
        ],
    }
    result = siie.read("offer", {"offer_id": "8-n1"}, transport=response(payload, 422))[
        "data"
    ]
    assert result["offer"]["campus_id"] is None and result["quotable"] is False
    assert result["saved"] is False and "draft" not in result
