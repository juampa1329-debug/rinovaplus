"""SIIE registration contracts with synthetic data; no remote writes."""

import base64
import copy
import hmac
import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import httpx2 as httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.institutional import siie_forms as forms
from app.institutional import siie_records as records
from app.institutional import siie_registration as registration
from app.institutional import siie_registration_client as client
from app.institutional import siie_webhook as hook
from app.institutional.api import core_permission

INSTITUTION = "1cddfb14-d7e0-44e0-a731-f3345452835c"


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("SIIE_API_BASE_URL", "https://siie.test/SIIEWebPlus")
    monkeypatch.setenv("SIIE_API_HOSTS", "siie.test")
    monkeypatch.setenv("SIIE_API_TOKEN", "fixture-original-siie-token-1234567890")
    monkeypatch.setenv(
        "SIIE_WEBHOOK_SECRET", "fixture-separate-signature-secret-123456"
    )
    return SimpleNamespace(
        ticket={"context": [[1, INSTITUTION]]},
        connection={"database": "synthetic"},
        review={
            "secrets_key": base64.b64encode(b"k" * 32).decode(),
            "session_token": "fixture-session",
        },
    )


def signed(raw, stamp=None):
    stamp = str(int(time.time()) if stamp is None else stamp)
    return {
        "content-type": "application/json",
        "x-siie-timestamp": stamp,
        "x-siie-signature": "sha256="
        + hmac.digest(
            hook.secret().encode(),
            b"rinovaplus-siie-v1." + stamp.encode() + b"." + raw,
            "sha256",
        ).hex(),
    }


def event(**changes):
    return {
        "schema_version": "siie-crm-event-v1",
        "event_id": str(uuid4()),
        "event_type": "pre_registration.created",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "sequence": 1,
        "documento": "TEST123",
        "idOferta": 21,
        "idPeriodo": 9,
        "idPreinscripcion": 80,
        "programa": "PRE-ICFES",
        "persona": {
            "nombres": "NOMBRE DE ENSAYO",
            "primerApellido": "PRUEBA",
            "celular": "3000000000",
            "correo": "synthetic@example.invalid",
        },
        **changes,
    }


@pytest.fixture
def memory(monkeypatch, settings):
    data = {}
    active = {"write": 0}

    class Cursor:
        def execute(self, *args):
            return self

    @contextmanager
    def tx(*args, **kwargs):
        before = copy.deepcopy(data)
        write = args[1] if len(args) > 1 else kwargs.get("write", False)
        active["write"] += int(write)
        try:
            yield Cursor()
        except BaseException:
            data.clear()
            data.update(before)
            raise
        finally:
            active["write"] -= int(write)

    def get(c, s, kind, identity):
        return copy.deepcopy(data.get((kind, str(identity))))

    def put(c, s, kind, identity, metadata, private, previous=None):
        old = data.get((kind, str(identity)))
        assert (old["revision"] if old else 0) == (
            previous["revision"] if previous else 0
        )
        revision = (old["revision"] if old else 0) + 1
        data[(kind, str(identity))] = {
            "revision": revision,
            "metadata": copy.deepcopy(metadata),
            "private": copy.deepcopy(private),
        }
        return revision

    monkeypatch.setattr(registration, "transaction", tx)
    monkeypatch.setattr(hook, "transaction", tx)
    monkeypatch.setattr(records, "get", get)
    monkeypatch.setattr(records, "put", put)
    monkeypatch.setattr(
        registration, "authorize", lambda *a, **k: {"UserId": str(uuid4())}
    )
    monkeypatch.setattr(registration, "audit", lambda *a, **k: None)
    monkeypatch.setattr(hook, "audit", lambda *a, **k: None)
    monkeypatch.setattr(registration, "rate", lambda *a: True)
    cfg = {
        "revision": 1,
        "webhook_enabled": True,
        "writes_enabled": True,
        "stage_key": "nuevo",
    }
    monkeypatch.setattr(registration, "config", lambda *a: cfg)
    monkeypatch.setattr(hook, "config", lambda *a: cfg)
    return data, active, cfg


def test_webhook_hmac_raw_body_domain_and_freshness(settings):
    raw = json.dumps(event()).encode()
    hook.verify(signed(raw), raw)
    for headers, body in [
        (signed(raw, int(time.time()) - 301), raw),
        (signed(raw), raw + b" "),
        ({**signed(raw), "x-siie-timestamp": "+1234567890"}, raw),
    ]:
        with pytest.raises(HTTPException) as failure:
            hook.verify(headers, body)
        assert failure.value.status_code == 403


def test_webhook_key_is_separate_from_existing_outbound_key(settings, monkeypatch):
    monkeypatch.delenv("SIIE_WEBHOOK_SECRET")
    with pytest.raises(HTTPException, match="siie_webhook_not_configured"):
        hook.verify({}, b"{}")
    assert client.endpoint("applicant")[1]["X-API-Key"].startswith("fixture-original")


def test_duplicate_webhook_no_second_projection_and_conflicting_event_is_rejected(
    settings, memory, monkeypatch
):
    calls = []
    monkeypatch.setattr(
        hook,
        "project",
        lambda *a: (
            calls.append(True) or {"projection": "created", "contact_id": str(uuid4())}
        ),
    )
    data = event()
    service = hook.Ingress(settings)
    first = service.receive(
        signed(json.dumps(data).encode()), json.dumps(data).encode()
    )
    raw = json.dumps(data, indent=2).encode()
    assert first["received"] and service.receive(signed(raw), raw)["duplicate"]
    assert len(calls) == 1
    raw = json.dumps({**data, "idOferta": 22}).encode()
    with pytest.raises(HTTPException, match="siie_webhook_event_conflict"):
        service.receive(signed(raw), raw)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"health": "must not enter CRM"},
        {"sequence": True},
        {"idOferta": "21"},
        {"event_type": "registration.created", "idEstudiante": None},
        {"occurred_at": "2026-11-25"},
        {"documento": "../path"},
        {"event_type": "pre_registration.created", "idPreinscripcion": None},
    ],
)
def test_webhook_rejects_unknown_sensitive_fields_invalid_references_and_coercion(
    settings, memory, monkeypatch, change
):
    monkeypatch.setattr(
        hook, "project", lambda *a: pytest.fail("No projection of invalid event")
    )
    raw = json.dumps(event(**change)).encode()
    with pytest.raises(HTTPException) as failure:
        hook.Ingress(settings).receive(signed(raw), raw)
    assert failure.value.status_code == 422


def test_webhook_http_rejects_duplicate_headers_duplicate_json_keys_and_oversize(
    settings, memory
):
    app = FastAPI()
    hook.install(app, settings)
    browser = TestClient(app)
    raw = json.dumps(event()).encode()
    headers = signed(raw)
    assert (
        browser.post(
            hook.HOOK_PATH,
            content=raw,
            headers=[
                *headers.items(),
                ("X-SIIE-Timestamp", headers["x-siie-timestamp"]),
            ],
        ).status_code
        == 403
    )
    raw = b'{"event_id":"a","event_id":"b"}'
    assert (
        browser.post(hook.HOOK_PATH, content=raw, headers=signed(raw)).status_code
        == 422
    )
    raw = b"x" * (hook.MAX_BODY + 1)
    assert (
        browser.post(hook.HOOK_PATH, content=raw, headers=signed(raw)).status_code
        == 413
    )


@pytest.mark.parametrize(
    "kind,path",
    [
        ("applicant", "AspiranteRegistro.aspx"),
        ("registration", "Inscripcion.aspx"),
        ("documents", "Documentos.aspx"),
        ("requirements", "DocumentosRequeridos.aspx"),
        ("catalogs", "CatalogosInscripcion.aspx"),
    ],
)
def test_all_four_paths_keep_deployed_folder_and_original_key(settings, kind, path):
    url, headers = client.endpoint(kind)
    assert url == "https://siie.test/SIIEWebPlus/Api/CRM/v1/" + path
    assert headers["X-API-Key"] == "fixture-original-siie-token-1234567890"


def test_document_multipart_has_generated_name_boundary_and_no_retry(settings):
    calls = []

    def remote(request):
        calls.append(request)
        assert "boundary=" in request.headers["content-type"]
        body = request.read()
        assert b"documentos[1]" in body and b"documento-1.pdf" in body
        assert b"private-original-name" not in body
        raise httpx.ReadTimeout("synthetic", request=request)

    result = client.request(
        "documents",
        {"idEstudiante": 3, "idOferta": 21, "idPeriodo": 9},
        [(1, "private-original-name.pdf", b"%PDF-fixture")],
        transport=httpx.MockTransport(remote),
    )
    assert result["state"] == "uncertain" and len(calls) == 1


@pytest.mark.parametrize(
    "status,code,state",
    [
        (409, "registration_exists", "conflict"),
        (503, "commit_outcome_unknown", "uncertain"),
        (503, "storage_outcome_unknown", "uncertain"),
        (503, "file_cleanup_required", "uncertain"),
        (503, "retry_operation", "uncertain"),
        (422, "initial_document_missing", "rejected"),
        (429, "rate_limited", "rejected"),
    ],
)
def test_remote_results_do_not_leak_errors_or_replay(settings, status, code, state):
    result = client.request(
        "applicant",
        {"idOferta": 21, "idPeriodo": 9, "documento": "TEST123"},
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                status,
                json={
                    "code": code,
                    "message": "sensitive SQL error",
                    "data": {"documento": "TEST123"},
                },
            )
        ),
    )
    assert (
        result["state"] == state
        and "sensitive" not in json.dumps(result)
        and "TEST123" not in json.dumps(result)
    )


@pytest.mark.parametrize(
    "name,content,identity",
    [
        ("file.pdf", b"not a PDF", 1),
        ("photo.pdf", b"%PDF-fixture", 5),
        ("file.exe", b"%PDF-fixture", 1),
        ("file.png", b"\x89PNG\r\n\x1a\n", 19),
    ],
)
def test_invalid_files_never_enter_transport(settings, name, content, identity):
    with pytest.raises(HTTPException):
        client.request(
            "documents",
            {},
            [(identity, name, content)],
            transport=httpx.MockTransport(lambda r: pytest.fail("network")),
        )


def test_unknown_success_or_redirect_is_uncertain_and_not_followed(settings):
    calls = []

    def remote(request):
        calls.append(request)
        return httpx.Response(
            302, headers={"Location": "https://untrusted.test"}, json={}
        )

    assert (
        client.request("applicant", {}, transport=httpx.MockTransport(remote))["state"]
        == "uncertain"
    )
    assert len(calls) == 1
    assert (
        client.request(
            "applicant",
            {"idOferta": 21, "idPeriodo": 9},
            transport=httpx.MockTransport(
                lambda r: httpx.Response(
                    201,
                    json={
                        "status": "ok",
                        "data": {"idAspirante": 2, "idOferta": 22, "idPeriodo": 9},
                    },
                )
            ),
        )["state"]
        == "uncertain"
    )


def test_native_document_catalog_supports_only_same_origin_friendly_url_redirect(
    settings,
):
    seen = []

    def remote(request):
        seen.append(request)
        if request.url.path.endswith(".aspx"):
            return httpx.Response(
                301,
                headers={
                    "Location": "/SIIEWebPlus/Api/Preinscripciones/v1/TiposDocumento"
                },
            )
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "data": [
                    {"Identificacion": "0", "Abreviatura": "SELECCIONE ..."},
                    {"Identificacion": "1", "Abreviatura": "CC"},
                ],
            },
        )

    assert client.document_types(transport=httpx.MockTransport(remote)) == [
        {"value": 1, "label": "CC"}
    ]
    assert len(seen) == 2 and all(
        r.headers["X-API-Key"].startswith("fixture-original") for r in seen
    )
    calls = []

    def redirect(request):
        calls.append(request)
        return httpx.Response(301, headers={"Location": "https://untrusted.test/types"})

    with pytest.raises(HTTPException):
        client.document_types(transport=httpx.MockTransport(redirect))
    assert len(calls) == 1


def test_requirement_friendly_url_preserves_scope_and_never_sends_key_to_foreign_target(
    settings,
):
    seen = []

    def remote(request):
        seen.append(request)
        assert (
            request.url.params["idOferta"] == "21"
            and request.url.params["idPeriodo"] == "9"
        )
        if request.url.path.endswith(".aspx"):
            return httpx.Response(
                301,
                headers={"Location": "/SIIEWebPlus/Api/CRM/v1/DocumentosRequeridos"},
            )
        return httpx.Response(
            200, json={"status": "ok", "data": {"oferta": {}, "items": []}}
        )

    assert (
        client.request(
            "requirements",
            {"idOferta": 21, "idPeriodo": 9},
            transport=httpx.MockTransport(remote),
        )["state"]
        == "confirmed"
    )
    assert len(seen) == 2
    calls = []

    def foreign(request):
        calls.append(request)
        return httpx.Response(
            301, headers={"Location": "https://untrusted.test/DocumentosRequeridos"}
        )

    with pytest.raises(HTTPException, match="siie_registration_read_redirect"):
        client.request(
            "requirements", {"idOferta": 21}, transport=httpx.MockTransport(foreign)
        )
    assert len(calls) == 1


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "siie_registration_access_rejected"),
        (404, "siie_registration_route_not_found"),
        (500, "siie_registration_source_unavailable"),
    ],
)
def test_requirement_diagnostics_distinguish_source_failures_without_reading_html(
    settings, caplog, status, code
):
    with pytest.raises(HTTPException, match=code):
        client.request(
            "requirements",
            {"idOferta": 21},
            transport=httpx.MockTransport(
                lambda r: httpx.Response(status, text="PRIVATE IIS BODY")
            ),
        )
    assert "PRIVATE" not in caplog.text and "fixture-original" not in caplog.text


def test_eleven_sections_keep_native_misspellings_and_unknown_fields_rejected():
    assert len(forms.SCHEMA) == 11
    names = {f["name"] for s in forms.SCHEMA for f in s["fields"]}
    assert {"FechaNacimento", "CostodiaEstudios", "AñoTerminaion1"} <= names
    forms.validate("registration", {"estudiante": {"Nombres": "ENSAYO"}})
    with pytest.raises(HTTPException):
        forms.validate("registration", {"estudiante": {"Id_Estudiante": 10}})
    with pytest.raises(HTTPException, match="siie_registration_catalogs_required"):
        forms.validate_fields(
            forms.APPLICANT,
            {
                "documento": "X",
                "tipoId": 1,
                "nombres": "A",
                "primerApellido": "B",
                "celular": "3000000000",
                "correo": "a@example.invalid",
            },
            final=True,
        )


def test_intent_is_durable_before_io_unknown_result_is_never_resent(
    settings, memory, monkeypatch
):
    data, active, _ = memory
    identity, operation = str(uuid4()), str(uuid4())
    context = {
        "idOferta": 21,
        "idPeriodo": 9,
        "program_name": "PRE-ICFES",
        "selection": {"program_id": "3", "offer_ref": "21-n1"},
    }
    data[("sd", identity)] = {
        "revision": 1,
        "metadata": {"kind": "applicant", "state": "draft"},
        "private": {"form": {"documento": "TEST123"}, "context": context},
    }
    monkeypatch.setattr(client, "offer_context", lambda *a: copy.deepcopy(context))
    monkeypatch.setattr(registration.native_catalogs, "final_choices", lambda *a: {})
    monkeypatch.setattr(forms, "validate", lambda *a, **k: None)
    calls = []

    def send(*args):
        assert active["write"] == 0
        assert data[("sw", operation)]["metadata"]["state"] == "pending_review"
        assert data[("sd", identity)]["metadata"]["state"] == "pending_review"
        calls.append(True)
        return {"state": "uncertain", "code": "siie_write_outcome_unknown", "data": {}}

    monkeypatch.setattr(client, "request", send)
    command = registration.Command(operation_id=operation, revision=1, reviewed=True)
    service = registration.Registration(settings)
    assert service.submit(identity, command)["state"] == "uncertain"
    assert service.submit(identity, command)["repeated"]
    assert len(calls) == 1
    with pytest.raises(HTTPException, match="operation_conflict"):
        service.submit(identity, command, [(1, "test.pdf", b"%PDF-fixture")])
    assert len(calls) == 1


def test_disabled_writes_do_not_contact_provider(settings, memory, monkeypatch):
    data, _, cfg = memory
    identity = str(uuid4())
    data[("sd", identity)] = {
        "revision": 1,
        "metadata": {"kind": "applicant", "state": "draft"},
        "private": {},
    }
    cfg["writes_enabled"] = False
    monkeypatch.setattr(client, "offer_context", lambda *a: pytest.fail("network"))
    with pytest.raises(HTTPException, match="siie_registration_writes_disabled"):
        registration.Registration(settings).submit(
            identity,
            registration.Command(operation_id=str(uuid4()), revision=1, reviewed=True),
        )


def test_private_record_encryption_and_section_fit_installed_schema(settings):
    db = sqlite3.connect(":memory:")
    db.execute(
        "CREATE TABLE data(InstitutionId TEXT,Section TEXT,Document TEXT,Revision INT,UpdatedAt TEXT)"
    )

    class Cursor:
        def execute(self, statement, *params):
            statement = (
                statement.replace("INSERT crm_access.Setting", "INSERT INTO data")
                .replace("crm_access.Setting", "data")
                .replace("SYSUTCDATETIME()", "CURRENT_TIMESTAMP")
            )
            self.cursor = db.execute(statement, params)
            self.description, self.rowcount = (
                self.cursor.description,
                self.cursor.rowcount,
            )
            return self

        def fetchone(self):
            return self.cursor.fetchone()

    c = Cursor()
    identity = str(uuid4())
    records.put(
        c,
        settings,
        "sd",
        identity,
        {"state": "draft"},
        {"name": "PRIVATE SYNTHETIC NAME", "health": "PRIVATE TEST"},
    )
    stored = db.execute("SELECT Document FROM data").fetchone()[0]
    assert "PRIVATE" not in stored
    assert len(records.section("sd", identity)) <= 40
    assert (
        records.get(c, settings, "sd", identity)["private"]["health"] == "PRIVATE TEST"
    )
    value = json.loads(stored)
    value["ciphertext"] = base64.b64encode(b"bad").decode()
    db.execute("UPDATE data SET Document=?", (json.dumps(value),))
    with pytest.raises(Exception):
        records.get(c, settings, "sd", identity)


def test_registration_routes_have_admissions_crm_and_config_has_recent_admin_boundary():
    assert core_permission(registration.PREFIX + "/records/sd/id", "GET") == (
        "crm.write",
        "admissions",
    )
    assert core_permission(registration.PREFIX + "/records/sw/id", "GET") == (
        "crm.write",
        "admissions",
    )
    assert core_permission(registration.PREFIX + "/records/se/id", "GET") == (
        "crm.write",
        "admissions",
    )
    assert core_permission(registration.PREFIX + "/records/se", "GET") == (
        "crm.read",
        "admissions",
    )
    assert core_permission(registration.PREFIX + "/drafts/id/submit", "POST") == (
        "crm.write",
        "admissions",
    )
    assert core_permission(registration.PREFIX + "/configuration", "PUT") == (
        "settings.webhooks.write",
        "admissions",
    )


@pytest.fixture
def projection_db(settings, monkeypatch):
    import re
    from pglast import parse_sql
    from app.institutional.operations_policy import layout
    from app.institutional.postgres_dialect import postgres_sql
    from app.modules.crm_configuration.application import service as crm

    # The HTTP rehearsal executes the synchronous receiver on its worker thread.
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.executescript("""
      ATTACH ':memory:' AS crm_access; ATTACH ':memory:' AS crm;
      ATTACH ':memory:' AS crm_workspace;
      CREATE TABLE crm_access.Setting(InstitutionId TEXT,Section TEXT,Document TEXT,Revision INT,UpdatedAt TEXT,PRIMARY KEY(InstitutionId,Section));
      CREATE TABLE crm.Contact(ContactId TEXT PRIMARY KEY,Name TEXT,Phone TEXT,City TEXT,ProgramId INT,Program TEXT,Schedule TEXT,Stage TEXT,Tags TEXT,Notes TEXT,Type TEXT,Interests TEXT,CustomValues TEXT);
      CREATE TABLE crm.Conversation(ConversationId TEXT,ContactId TEXT,State TEXT,Priority TEXT,ControlMode TEXT,Unread INT);
      CREATE TABLE crm_workspace.State(StateId INT,Revision INT);
      INSERT INTO crm_workspace.State VALUES(1,0);
      CREATE TABLE crm_workspace.Merge(SourceContactId TEXT,TargetContactId TEXT,Active INT);
    """)
    db.create_function("CONCAT", -1, lambda *parts: "".join(str(v) for v in parts))
    config = SimpleNamespace(
        stages=[SimpleNamespace(key="nuevo", label="Nuevo", active=True)], fields=[]
    )
    monkeypatch.setattr(crm, "read_configuration", lambda *a, **k: (config, 1))
    monkeypatch.setattr(crm, "validate_contact", lambda *a, **k: None)

    class Cursor:
        def execute(self, statement, *params):
            parse_sql(postgres_sql(statement, layout()["tables"]).replace("%s", "NULL"))
            statement = re.sub(r"\bINSERT\s+(?!INTO\b)", "INSERT INTO ", statement)
            statement = statement.replace(
                "SYSUTCDATETIME()", "CURRENT_TIMESTAMP"
            ).replace("JSON_VALUE", "json_extract")
            statement = re.sub(
                r"CONVERT\(varchar\(36\),([a-zA-Z.]+)\)", r"CAST(\1 AS TEXT)", statement
            )
            top = re.search(r"SELECT TOP\s*\((\d+)\)", statement)
            if top:
                statement = (
                    statement[: top.start()]
                    + statement[top.start() :].replace(top[0], "SELECT", 1)
                    + " LIMIT "
                    + top[1]
                )
            self.cursor = db.execute(statement, params)
            self.description, self.rowcount = (
                self.cursor.description,
                self.cursor.rowcount,
            )
            return self

        def fetchone(self):
            return self.cursor.fetchone()

        def fetchall(self):
            return self.cursor.fetchall()

    return db, Cursor()


def test_signed_pre_registration_becomes_registered_same_crm_record_no_promotions(
    settings, projection_db
):
    from app.institutional import siie_classification as classification

    db, cursor = projection_db
    original = hook.Event.model_validate(event())
    result = hook.project(cursor, settings, original, {"stage_key": "nuevo"})
    identity = result["contact_id"]
    assert result["projection"] == "created"
    assert db.execute("SELECT Type FROM crm.Contact").fetchone()[0] == "Preinscrito"
    assert not classification.blocked(cursor, settings, identity, "3000000000")
    registered = hook.Event.model_validate(
        event(
            event_type="registration.created",
            sequence=2,
            idEstudiante=4,
            idInscripcion=5,
        )
    )
    result = hook.project(cursor, settings, registered, {"stage_key": "nuevo"})
    assert result["contact_id"] == identity
    assert db.execute("SELECT COUNT(*) FROM crm.Contact").fetchone()[0] == 1
    assert db.execute("SELECT Type FROM crm.Contact").fetchone()[0] == "Inscrito"
    assert classification.blocked(cursor, settings, identity, "3000000000")
    assert identity in classification.registered_contacts(cursor, settings)
    assert (
        db.execute("SELECT ControlMode FROM crm.Conversation").fetchone()[0] == "human"
    )
    # A later pre-registration cannot reopen promotions or overwrite human edits.
    db.execute("UPDATE crm.Contact SET Name='NOMBRE REVISADO'")
    hook.project(
        cursor,
        settings,
        hook.Event.model_validate(event(sequence=3)),
        {"stage_key": "nuevo"},
    )
    assert classification.blocked(cursor, settings, identity)
    assert db.execute("SELECT Name FROM crm.Contact").fetchone()[0] == "NOMBRE REVISADO"
    assert (
        "PRIVATE"
        not in db.execute(
            "SELECT Document FROM crm_access.Setting WHERE Section LIKE 'sg:%'"
        ).fetchone()[0]
    )


def test_ambiguous_existing_phone_is_not_merged_but_registration_stops_promotions(
    settings, projection_db
):
    from app.institutional import siie_classification as classification

    db, cursor = projection_db
    existing = str(uuid4())
    db.execute(
        "INSERT INTO crm.Contact(ContactId,Name,Phone) VALUES(?, 'IMPORTADO', '+57 300 0000000')",
        (existing,),
    )
    registered = hook.Event.model_validate(
        event(event_type="registration.created", idEstudiante=4, idInscripcion=5)
    )
    result = hook.project(cursor, settings, registered, {"stage_key": "nuevo"})
    assert result == {"projection": "review_required", "contact_id": None}
    assert db.execute("SELECT COUNT(*) FROM crm.Contact").fetchone()[0] == 1
    assert classification.blocked(cursor, settings, existing, "+573000000000")
    # A new social contact with the same destination cannot bypass suppression.
    later_contact = str(uuid4())
    assert classification.blocked(cursor, settings, later_contact, "3000000000")
    assert not classification.blocked(cursor, settings, later_contact, "3000000001")


@pytest.fixture
def identity_review(settings, projection_db, monkeypatch):
    db, cursor = projection_db
    existing = str(uuid4())
    db.execute(
        "INSERT INTO crm.Contact(ContactId,Name,Phone) VALUES(?, 'NOMBRE CRM REVISADO', '+573000000000')",
        (existing,),
    )
    original = hook.Event.model_validate(event())
    projection = hook.project(cursor, settings, original, {"stage_key": "nuevo"})
    records.put(
        cursor,
        settings,
        "se",
        original.event_id,
        {"event_type": original.event_type, "projection": projection["projection"]},
        {"event": original.model_dump(), **projection},
    )

    @contextmanager
    def tx(*args, **kwargs):
        yield cursor

    monkeypatch.setattr(registration, "transaction", tx)
    monkeypatch.setattr(
        registration, "authorize", lambda *a, **k: {"UserId": str(uuid4())}
    )
    monkeypatch.setattr(registration, "audit", lambda *a, **k: None)
    return db, cursor, existing, original, registration.Registration(settings)


def test_old_receipt_review_shows_latest_identity_snapshot_not_just_old_names(
    settings, identity_review
):
    _, cursor, existing, original, service = identity_review
    latest = hook.Event.model_validate(
        event(
            sequence=2,
            persona={**original.persona.model_dump(), "nombres": "NOMBRE ACTUAL SIIE"},
        )
    )
    hook.project(cursor, settings, latest, {"stage_key": "nuevo"})
    detail = service.read("se", original.event_id)
    assert detail["event"]["persona"]["nombres"] == original.persona.nombres
    assert (
        detail["link_review"]["snapshot"]["persona"]["nombres"] == "NOMBRE ACTUAL SIIE"
    )
    assert detail["link_review"]["revision"] == 2
    assert detail["candidates"][0]["id"] == existing
    assert "digest" not in detail and "actor_id" not in detail


def test_reviewed_identity_link_stops_when_new_siie_event_arrived(
    settings, identity_review
):
    db, cursor, existing, original, service = identity_review
    initial = service.read("se", original.event_id)["link_review"]
    hook.project(
        cursor,
        settings,
        hook.Event.model_validate(event(sequence=2)),
        {"stage_key": "nuevo"},
    )
    body = registration.Link(
        contact_id=existing, reviewed=True, link_revision=initial["revision"]
    )
    with pytest.raises(HTTPException, match="siie_contact_link_changed"):
        service.link(original.event_id, body)
    assert (
        records.get(cursor, settings, "sl", hook.person_ref(settings, original))[
            "private"
        ]["contact_id"]
        is None
    )
    assert (
        db.execute("SELECT Name FROM crm.Contact").fetchone()[0]
        == "NOMBRE CRM REVISADO"
    )


def test_current_identity_review_links_once_and_keeps_registered_suppression(
    settings, identity_review
):
    from app.institutional import siie_classification as classification

    db, cursor, existing, original, service = identity_review
    registered = hook.Event.model_validate(
        event(
            event_type="registration.created",
            sequence=2,
            idEstudiante=4,
            idInscripcion=5,
        )
    )
    hook.project(cursor, settings, registered, {"stage_key": "nuevo"})
    detail = service.read("se", original.event_id)
    assert detail["link_review"]["registered"] is True
    body = registration.Link(
        contact_id=existing,
        reviewed=True,
        link_revision=detail["link_review"]["revision"],
    )
    assert service.link(original.event_id, body) == {
        "linked": True,
        "contact_id": existing,
    }
    assert service.link(original.event_id, body)["linked"] is True
    assert db.execute("SELECT COUNT(*) FROM crm.Contact").fetchone()[0] == 1
    assert db.execute("SELECT Name,Type FROM crm.Contact").fetchone() == (
        "NOMBRE CRM REVISADO",
        "Inscrito",
    )
    assert classification.blocked(cursor, settings, existing)
    with pytest.raises(HTTPException, match="siie_contact_link_changed"):
        service.link(
            original.event_id,
            registration.Link(
                contact_id=str(uuid4()),
                reviewed=True,
                link_revision=detail["link_review"]["revision"],
            ),
        )


def test_signed_http_pre_registration_and_enrollment_persist_one_crm_contact(
    settings, projection_db, monkeypatch
):
    from app.institutional import siie_classification as classification

    db, cursor = projection_db

    @contextmanager
    def tx(*args, **kwargs):
        try:
            yield cursor
            db.commit()
        except BaseException:
            db.rollback()
            raise

    monkeypatch.setattr(hook, "transaction", tx)
    monkeypatch.setattr(
        hook, "config", lambda *a: {"webhook_enabled": True, "stage_key": "nuevo"}
    )
    monkeypatch.setattr(hook, "audit", lambda *a, **k: None)
    monkeypatch.setattr(
        client,
        "request",
        lambda *a, **k: pytest.fail(
            "A webhook never calls SIIE registration or payment routes"
        ),
    )
    app = FastAPI()
    hook.install(app, settings)
    browser = TestClient(app)
    first = event()
    raw = json.dumps(first).encode()
    response = browser.post(hook.HOOK_PATH, content=raw, headers=signed(raw))
    assert response.status_code == 200 and response.json()["projection"] == "created"
    duplicate = browser.post(hook.HOOK_PATH, content=raw, headers=signed(raw))
    assert duplicate.json()["duplicate"] is True
    final = event(
        event_type="registration.created", sequence=2, idEstudiante=4, idInscripcion=5
    )
    raw = json.dumps(final).encode()
    response = browser.post(hook.HOOK_PATH, content=raw, headers=signed(raw))
    assert response.status_code == 200 and response.json()["projection"] == "linked"
    assert db.execute("SELECT COUNT(*) FROM crm.Contact").fetchone()[0] == 1
    identity, kind = db.execute("SELECT ContactId,Type FROM crm.Contact").fetchone()
    assert kind == "Inscrito" and classification.blocked(cursor, settings, identity)
    assert db.execute("SELECT ControlMode,Unread FROM crm.Conversation").fetchone() == (
        "human",
        0,
    )
    assert (
        db.execute(
            "SELECT COUNT(*) FROM crm_access.Setting WHERE Section LIKE 'se:%'"
        ).fetchone()[0]
        == 2
    )


def test_delayed_registration_proof_still_suppresses_after_newer_pre_registration(
    settings, projection_db
):
    from app.institutional import siie_classification as classification

    _, cursor = projection_db
    newer = hook.Event.model_validate(event(sequence=20))
    identity = hook.project(cursor, settings, newer, {"stage_key": "nuevo"})[
        "contact_id"
    ]
    older = hook.Event.model_validate(
        event(
            sequence=10,
            event_type="registration.created",
            idEstudiante=4,
            idInscripcion=5,
        )
    )
    assert (
        hook.project(cursor, settings, older, {"stage_key": "nuevo"})["projection"]
        == "stale_ignored"
    )
    assert classification.blocked(cursor, settings, identity)


def test_pre_registration_without_document_uses_native_pre_id_until_completed(
    settings, projection_db
):
    from app.institutional import siie_classification as classification

    db, cursor = projection_db
    preliminary = hook.Event.model_validate(event(documento=None))
    identity = hook.project(cursor, settings, preliminary, {"stage_key": "nuevo"})[
        "contact_id"
    ]
    completed = hook.Event.model_validate(
        event(
            sequence=2,
            event_type="registration.created",
            idEstudiante=4,
            idInscripcion=5,
        )
    )
    assert (
        hook.project(cursor, settings, completed, {"stage_key": "nuevo"})["contact_id"]
        == identity
    )
    assert db.execute("SELECT COUNT(*) FROM crm.Contact").fetchone()[0] == 1
    assert classification.blocked(cursor, settings, identity)
    changed = hook.Event.model_validate(event(sequence=3, documento="OTHER123"))
    with pytest.raises(HTTPException, match="siie_webhook_person_conflict"):
        hook.project(cursor, settings, changed, {"stage_key": "nuevo"})


def test_router_installs_and_query_paths_do_not_require_agent_management(
    settings, memory
):
    app = FastAPI()
    registration.install(app, settings)
    routes = {r.path for r in app.routes}
    assert registration.PREFIX + "/selection/{kind}" in routes
    assert registration.PREFIX + "/drafts/{identity}/documents" in routes
    assert core_permission(registration.PREFIX + "/selection/programs", "GET") == (
        "crm.read",
        "admissions",
    )


def test_registered_guard_cannot_be_bypassed_by_customer_requested_followup(
    settings, monkeypatch
):
    from app.institutional import campaigns, contact_preference, siie_classification

    monkeypatch.setattr(siie_classification, "blocked", lambda *a: True)
    monkeypatch.setattr(campaigns, "filters_for", lambda *a: [])
    monkeypatch.setattr(campaigns, "marketing_allowed", lambda *a: False)
    monkeypatch.setattr(contact_preference, "blocked", lambda *a: False)
    integration = str(uuid4())
    person = {
        "IntegrationId": integration,
        "CanonicalContactId": str(uuid4()),
        "ControlMode": "ai",
        "ConversationState": "open",
        "IncomingCount": 1,
        "LastIncomingAt": campaigns.now(),
    }
    reasons = campaigns.reasons(
        None,
        settings,
        {
            "integration_id": integration,
            "followup_only": True,
            "contact_basis": "customer_request",
        },
        person,
    )
    assert reasons == ["siie_registered_no_promotions"]


def complete_form():
    result, choices = {}, {}
    for section in forms.SCHEMA:
        if section.get("optional"):
            continue
        row = {}
        for f in section["fields"]:
            if not f["required"]:
                continue
            if f["options"]:
                value = f["options"][0]
            elif f["catalog"]:
                value = 1 if f["kind"] == "integer" else "1"
                choices[f["catalog"]] = [{"value": 1, "label": "CATALOGO SINTETICO"}]
            elif f["kind"] == "date":
                value = "2000-01-01"
            elif f["kind"] == "email":
                value = "synthetic@example.invalid"
            elif f["kind"] == "document":
                value = "TEST123"
            else:
                value = "ENSAYO"
            row[f["name"]] = value
            if f["catalog"]:
                choices[f["catalog"]] = [
                    {"value": value, "label": "CATALOGO SINTETICO"}
                ]
        result[section["name"]] = [row] if section.get("max_items") else row
    result["referencia"]["Direccion"] = "DIRECCION DIFERENTE"
    result["aceptaTratamientoDatos"] = True
    return result, choices


def test_complete_native_registration_and_consent_are_validated_before_transport():
    value, choices = complete_form()
    forms.validate(
        "registration", value, final=True, catalogs=choices, program_name="PRE-ICFES"
    )
    value["aceptaTratamientoDatos"] = False
    with pytest.raises(HTTPException, match="siie_consent_required"):
        forms.validate(
            "registration",
            value,
            final=True,
            catalogs=choices,
            program_name="PRE-ICFES",
        )


def test_requirements_without_student_preserve_unknown_file_and_delivery_flags(
    settings,
):
    data = {
        "oferta": {},
        "items": [
            {
                "idDocumento": 1,
                "nombre": "Identidad",
                "obligatorioAlInscribir": True,
                "soportado": True,
                "recibido": None,
                "archivoExistente": None,
                "aplica": None,
            }
        ],
    }
    result = client.request(
        "requirements",
        {"idOferta": 21},
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"status": "ok", "data": data})
        ),
    )
    assert result["data"]["items"][0]["archivoExistente"] is None
    data["items"][0]["obligatorioAlInscribir"] = None
    with pytest.raises(HTTPException, match="siie_registration_invalid_response"):
        client.request(
            "requirements",
            {"idOferta": 21},
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json={"status": "ok", "data": data})
            ),
        )


def test_siie_pre_registration_is_available_in_existing_reviewed_prospect_workflow():
    from app.institutional.broadcast_prospects import reviewed_contact

    contact = {
        "Type": "Preinscrito",
        "Phone": "3000000000",
        "CustomValues": json.dumps(
            {"pre_import_ref": "SIIE-" + "a" * 32, "pre_programas": "PRE ICFES SABADO"}
        ),
    }
    assert reviewed_contact(contact, "all") == "573000000000"
    contact["Type"] = "Inscrito"
    with pytest.raises(HTTPException):
        reviewed_contact(contact, "all")


def test_under_sixteen_requires_review_except_preicfes_and_never_invents_catalog_ids():
    from zoneinfo import ZoneInfo
    from datetime import date

    value, choices = complete_form()
    today = datetime.now(ZoneInfo("America/Bogota")).date()
    value["estudiante"]["FechaNacimento"] = date(
        today.year - 15, today.month, min(today.day, 28)
    ).isoformat()
    forms.validate(
        "registration", value, final=True, catalogs=choices, program_name="PRE-ICFES"
    )
    with pytest.raises(HTTPException, match="siie_minimum_age_review_required"):
        forms.validate(
            "registration", value, final=True, catalogs=choices, program_name="COCINA"
        )
    value["estudiante"]["Id_Genero"] = 99
    with pytest.raises(HTTPException, match="siie_form_catalog_changed"):
        forms.validate(
            "registration",
            value,
            final=True,
            catalogs=choices,
            program_name="PRE-ICFES",
        )


@pytest.mark.parametrize(
    "area,origin,state",
    [
        ("clients", "", ""),
        ("clients", "siie", "pre_registered"),
        ("clients", "siie", "registered"),
        ("clients", "imported", ""),
        ("clients", "social", ""),
        ("inbox", "", ""),
    ],
)
def test_crm_and_inbox_queries_parse_with_origin_filters_and_exact_parameter_order(
    settings, monkeypatch, area, origin, state
):
    from pglast import parse_sql
    from app.institutional import workspace
    from app.institutional.operations_policy import layout
    from app.institutional.postgres_dialect import postgres_sql

    statements = []

    class Cursor:
        description = []

        def execute(self, sql, *params):
            translated = postgres_sql(sql, layout()["tables"])
            parse_sql(translated.replace("%s", "NULL"))
            assert translated.count("%s") == len(params)
            if "LEFT JOIN crm_access.Setting siie" in sql:
                assert params[0] == INSTITUTION
            if "sr.InstitutionId=?" in sql:
                assert params[0] == INSTITUTION
            statements.append((sql, params))
            return self

        def fetchval(self):
            return 0

        def fetchall(self):
            return []

    @contextmanager
    def tx(*args, **kwargs):
        yield Cursor()

    monkeypatch.setattr(workspace, "transaction", tx)
    monkeypatch.setattr(workspace, "authorize", lambda *a: {"UserId": str(uuid4())})
    monkeypatch.setattr(workspace, "revision", lambda *a: "1")
    service = workspace.Workspace(settings)
    result = service.listing(
        area, contactOrigin=origin, academicState=state, q="ENSAYO"
    )
    assert result["items"] == []
    assert len(statements) >= 2
