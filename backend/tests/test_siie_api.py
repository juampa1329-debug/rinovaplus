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
    monkeypatch.setenv("SIIE_CATALOG_API_TOKEN", "catalog-fixture-not-a-real-key-12345")
    monkeypatch.setenv("SIIE_ADMISSIONS_API_TOKEN", "admissions-fixture-not-a-real-key")


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


def test_disabled_scopes_are_separate_and_never_send_other_key(monkeypatch):
    monkeypatch.delenv("SIIE_CATALOG_API_TOKEN")
    assert siie.status()["admissions_configured"] is True
    with pytest.raises(HTTPException, match="siie_catalog_not_configured"):
        siie.read(
            "programs", transport=httpx.MockTransport(lambda r: pytest.fail("network"))
        )
    monkeypatch.delenv("SIIE_ADMISSIONS_API_TOKEN")
    with pytest.raises(HTTPException, match="siie_admissions_not_configured"):
        siie.read(
            "periods", transport=httpx.MockTransport(lambda r: pytest.fail("network"))
        )


def test_real_aspx_path_header_and_opaque_cursor_are_preserved():
    def remote(request):
        assert request.method == "GET"
        assert request.url.path == "/SIIEWebPlus/Api/CRM/v1/Commercial/Programs.aspx"
        assert request.url.params["cursor"] == "opaque+/=cursor"
        assert request.headers["X-API-Key"].startswith("catalog-fixture")
        assert (
            "Authorization" not in request.headers and "Origin" not in request.headers
        )
        return httpx.Response(
            200,
            json=stamp(items=[], next_cursor=None, pagination="keyset_live_catalog"),
            headers={"X-Correlation-ID": "fixture-request"},
        )

    result = siie.read(
        "programs", {"cursor": "opaque+/=cursor"}, transport=httpx.MockTransport(remote)
    )
    assert result["correlation_id"] == "fixture-request"
    assert result["saved"] is False


@pytest.mark.parametrize(
    "route,values",
    [
        ("applicants", {}),
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
        assert request.headers["X-API-Key"].startswith("admissions-fixture")
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


def test_legacy_import_cannot_bypass_incomplete_offer_inspection():
    from app.institutional.siie_catalog import preview

    payload = {
        "code": "source_data_incomplete",
        "quotable": False,
        "partial_offer": stamp(offer_id="1-n1", quotable=False),
        "data_quality": [],
    }
    with pytest.raises(HTTPException, match="siie_source_incomplete"):
        preview("1-n1", transport=response(payload, 422))
