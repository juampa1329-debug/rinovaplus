"""Executable P6 SQL2019/API acceptance. Only an explicitly isolated P6 fixture."""

import base64
import json
import os
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from tools.prepare_p6_knowledge import WORK, admin, read, save
from tools.qualify_p3_workspace import Browser
from tools.qualify_p4_storage import academic


def main():
    label = os.environ.get("P6_FIXTURE_LABEL", "fixture")
    profile = read(WORK / (label + "-profile.json"))
    settings = load(Path(profile["directory"]))
    assert settings.connection["database"].startswith("CBN_P6ES_TRIAL_")
    access = read(WORK / (label + "-access.json"))
    b = Browser(create_app(settings))
    b.login(access["email"], access["password"])
    checks = []

    def check(name, condition=True):
        assert condition, name
        checks.append(name)
        save(WORK / "api-result.json", {"status": "in_progress", "checks": checks})

    def call(path, method="GET", body=None, expected=200, browser=b):
        return browser.request(path, method, body, expected).json()

    def sql(query, *params):
        with admin(settings.connection["database"], readonly=True) as db:
            return (
                Cursor(db.cursor(), settings.ticket["table_map"])
                .execute(query, *params)
                .fetchall()
            )

    with admin(settings.connection["database"], readonly=True) as db:
        before = academic(db.cursor())
    check(
        "own_SQL2019_TLS_profile_153_tables",
        settings.ticket["identity"]["engine"] == 15
        and settings.ticket["identity"]["compatibility"] == 150
        and len(settings.ticket["tables"]) == 153,
    )
    check(
        "knowledge_memory_integrated_runtime",
        all(
            v["operational"]
            for v in call("runtime")["modules"]
            if v["id"] in {"knowledge", "memory"}
        ),
    )
    ids = {}

    def body(kind="document", **extra):
        return dict(
            operation_id=str(uuid4()),
            revision=0,
            reason="Revisión educativa controlada P6",
            kind=kind,
            title="Fuente educativa P6",
            body=(
                "Matrícula: consulta al equipo de admisiones "
                "con documento de identidad."
            ),
            owner="Equipo de admisiones",
            origin="Contenido sintético de cualificación; no oficial",
            valid_until="2027-12-31",
            confidence=0,
            visibility="agent_context",
            program_id=None,
            stage_id=None,
            dna=None,
            source_message_id=None,
            quote="",
            fact_type="followup_note",
            **extra,
        )

    def create(name, kind="document", changes=None, conversation=None):
        key = str(uuid4())
        doc = body(kind)
        doc.update(changes or {})
        prefix = (
            f"conversation-memory/{conversation}"
            if conversation
            else "knowledge/records"
            if kind == "document"
            else "memory/records"
        )
        result = call(prefix + "/" + key, "PUT", doc)
        check(
            name + "_draft_stored",
            result["state"] == "draft" and result["revision"] == 1,
        )
        ids[name] = {"id": key, "prefix": prefix, "body": doc, "revision": 1}
        return ids[name]

    def trans(item, action="publish", expected=200, **extra):
        payload = (
            dict(
                operation_id=str(uuid4()),
                revision=item["revision"],
                reason="Revisión explícita de versión P6",
                confirmed=True,
            )
            | extra
        )
        result = call(
            item["prefix"] + "/" + item["id"] + "/" + action, "POST", payload, expected
        )
        if expected == 200 and action != "reindex":
            item["revision"] = result["revision"]
        return result

    def search(query, program=None, stage=None):
        return call(
            "knowledge/search",
            "POST",
            dict(query=query, program_id=program, stage_id=stage),
        )["items"]

    doc = create(
        "requisitos",
        changes={
            "body": (
                (
    'Requisitos de inscripción: documento de identidad, diploma'
    ' y formulario de admisiones. Palabra exclusiva solazul.'
)
            )
        },
    )
    check("unpublished_body_excluded", not search("solazul"))
    command = {k: v for k, v in doc["body"].items()}
    command["revision"] = 0
    check(
        "replay_draft_is_exact_no_duplicate_version",
        call(doc["prefix"] + "/" + doc["id"], "PUT", command)["revision"] == 1,
    )
    bad = {**command, "body": "Otro contenido"}
    call(doc["prefix"] + "/" + doc["id"], "PUT", bad, 409)
    check("nonce_reuse_payload_conflict")
    trans(doc, confirmed=False, expected=409)
    check("publication_requires_explicit_review")
    trans(doc)
    found = search("solazul")
    check(
        "published_citation_has_page_document_revision",
        len(found) == 1
        and found[0]["page"] == 1
        and found[0]["document_id"] == doc["id"]
        and found[0]["revision"] == 2,
    )
    old_cite = found[0]["id"]
    history = call(doc["prefix"] + "/" + doc["id"] + "/history")["items"]
    check(
        "confidence_zero_and_author_provenance_retained",
        history[0]["document"]["confidence"] == 0
        and len(history) == 2
        and bool(history[0]["actor"]),
    )
    correction = {
        **doc["body"],
        "revision": 2,
        "operation_id": str(uuid4()),
        "body": (
            "Requisitos corregidos: documento y formulario. Palabra exclusiva solverde."
        ),
    }
    call(doc["prefix"] + "/" + doc["id"], "PUT", correction)
    doc["revision"] = 3
    check(
        "correction_withdraws_previous_publication",
        not search("solazul") and not search("solverde"),
    )
    trans(doc)
    check(
        "new_publication_changes_current_citation",
        search("solverde")[0]["id"] != old_cite and not search("solazul"),
    )
    stale = {**correction, "operation_id": str(uuid4())}
    call(doc["prefix"] + "/" + doc["id"], "PUT", stale, 409)
    check("CAS_preserves_current_version")
    trans(doc, "restore", version=2)
    check(
        "restore_appends_approved_version",
        search("solazul")[0]["revision"] == 5
        and len(call(doc["prefix"] + "/" + doc["id"] + "/history")["items"]) == 5,
    )
    citation = search("solazul")[0]
    trans(doc, "reindex")
    check(
        "derived_reindex_preserves_citation_and_revision",
        search("solazul")[0] == citation,
    )
    # Corrupt only derived indexes using the fixture administrator, then rebuild
    # through the restricted application principal from immutable reviewed pages.
    with admin(settings.connection["database"]) as db:
        c = Cursor(db.cursor(), settings.ticket["table_map"])
        c.execute(
            (
                (
    'DELETE t FROM crm_ai.KnowledgeTerm t JOIN crm_ai.Knowledge'
    'Chunk x ON x.ChunkId=t.ChunkId WHERE x.DocumentId=?'
)
            ),
            doc["id"],
        )
    check("missing_derived_terms_are_not_fake_results", not search("solazul"))
    trans(doc, "reindex")
    check(
        "derived_index_recovers_from_reviewed_pages", search("solazul")[0] == citation
    )
    trans(doc, "archive")
    check("archived_source_excluded", not search("solazul"))
    trans(doc, "restore", version=2)
    # Real PDF extraction through the bounded subprocess, not mocked pages.
    import io

    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    out = io.BytesIO()
    pdf = PdfWriter()
    for text in [
        "Becas educativas: consulta condiciones y revision humana.",
        "Jornadas nocturnas: consulta disponibilidad con admisiones.",
    ]:
        page = pdf.add_blank_page(612, 792)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        stream = DecodedStreamObject()
        stream.set_data(("BT /F1 12 Tf 40 740 Td (" + text + ") Tj ET").encode())
        page[NameObject("/Contents")] = pdf._add_object(stream)
    pdf.write(out)
    pdfid = str(uuid4())
    raw = out.getvalue()
    upload = dict(
        operation_id=str(uuid4()),
        revision=0,
        reason="Carga PDF sintética controlada",
        title="Guía educativa PDF",
        filename="guia.pdf",
        content_base64=base64.b64encode(raw).decode(),
        owner="Admisiones",
        confidence=0,
        origin="PDF sintético controlado",
        valid_until="2027-12-31",
        visibility="agent_context",
        program_id=None,
        stage_id=None,
        record_id=pdfid,
    )
    call("knowledge/upload", "POST", upload)
    p = {"id": pdfid, "prefix": "knowledge/records", "revision": 1}
    trans(p)
    check(
        "real_PDF_page_two_citation",
        any(v["page"] == 2 for v in search("jornadas nocturnas")),
    )
    txtid = str(uuid4())
    upload.update(
        operation_id=str(uuid4()),
        record_id=txtid,
        filename="guia.txt",
        title="Inscripción Unicode",
        content_base64=base64.b64encode(
            ("😀" * 1800 + " inscripción matrícula formulario uniacento").encode()
        ).decode(),
    )
    call("knowledge/upload", "POST", upload)
    txt = {"id": txtid, "prefix": "knowledge/records", "revision": 1}
    trans(txt)
    check(
        "TXT_emoji_roundtrip_no_nvarchar_truncation",
        sum(
            len(r[0])
            for r in sql(
                "SELECT Body FROM crm_ai.KnowledgeChunk WHERE DocumentId=?", txtid
            )
        )
        >= 1800
        and max(
            len(r[0].encode("utf-16-le"))
            for r in sql(
                "SELECT Body FROM crm_ai.KnowledgeChunk WHERE DocumentId=?", txtid
            )
        )
        <= 3200,
    )
    upload.update(
        operation_id=str(uuid4()), record_id=str(uuid4()), filename="😀" * 100 + ".txt"
    )
    call("knowledge/upload", "POST", upload, 422)
    check("UTF16_filename_overflow_rejected")
    upload.update(
        operation_id=str(uuid4()),
        record_id=str(uuid4()),
        filename="bad.txt",
        content_base64=base64.b64encode(b"\x00bad").decode(),
    )
    call("knowledge/upload", "POST", upload, 415)
    upload.update(operation_id=str(uuid4()), record_id=str(uuid4()), filename="bad.exe")
    call("knowledge/upload", "POST", upload, 415)
    check("unsupported_and_binary_text_rejected")
    staff = create(
        "staff",
        changes={"visibility": "staff_only", "body": "Secreto editorial platinoculto"},
    )
    trans(staff)
    check("staff_only_body_never_retrieved", not search("platinoculto"))
    expired = create("expired", changes={"valid_until": "2020-01-01"})
    trans(expired, expected=409)
    check("expired_publication_rejected")
    # Distinct reviewed program scope.
    programs = call("/api/v1/agents/programs")["items"]
    program = programs[0]["program_id"]
    scoped = create(
        "program",
        changes={
            "program_id": program,
            "body": "Contenido del programa ámbito uniprogmarcador",
        },
    )
    trans(scoped)
    check(
        "program_scope_filters_before_body",
        not search("uniprogmarcador")
        and bool(search("uniprogmarcador", program))
        and not search("uniprogmarcador", program + 999),
    )
    collective = create(
        "collective",
        "collective",
        {
            "body": (
                "Criterio colectivo marcacolectiva: escuchar y derivar dudas al equipo."
            )
        },
    )
    trans(collective)
    secret = create(
        "collective_staff",
        "collective",
        {"visibility": "staff_only", "body": "Detalle exclusivo editor marcanoagente"},
    )
    trans(secret)
    dna = create(
        "dna",
        "dna",
        {
            "body": "",
            "title": "ADN educativo revisado",
            "dna": {
                "mission": "Acompañar sin inventar hechos marcadna",
                "voice": "Clara y respetuosa",
                "principles": "Citar fuentes vigentes",
                "boundaries": "SIIE conserva la autoridad académica",
                "escalation": "Derivar decisiones al equipo",
            },
        },
    )
    trans(dna)
    guide = next(v for v in call("/api/v1/agents")["agents"] if v["level"] == "guide")
    cfg = {
        **guide["configuration"],
        "document_ids": [doc["id"], pdfid],
        "memories": sorted(set(guide["configuration"]["memories"]) | {"knowledge", "semantic", "collective", "customer_profile", "regulated"}),
        "capabilities": sorted(set(guide["configuration"]["capabilities"]) | {"sources.read", "conversation.reply", "human.handoff"}),
    }
    call(
        "/api/v1/agents/profiles/" + guide["id"],
        "PUT",
        dict(
            operation_id=str(uuid4()),
            revision=guide["revision"],
            name=guide["name"],
            level=guide["level"],
            configuration=cfg,
        ),
    )

    def simulation():
        item = next(
            v for v in call("/api/v1/agents")["agents"] if v["id"] == guide["id"]
        )
        return call(
            "/api/v1/agents/simulate",
            "POST",
            dict(
                agent_id=item["id"],
                config_version=item["version"],
                question="solazul",
                program_id=None,
                stage_id=None,
                request_id=str(uuid4()),
                call_provider=False,
            ),
        )

    simulated = simulation()
    text = json.dumps(simulated, ensure_ascii=False)
    check(
        "agent_context_has_reviewed_collective_DNA_and_sources",
        "marcacolectiva" in text
        and "marcadna" in text
        and "marcanoagente" not in text
        and simulated["sources"],
    )
    first = simulated["effective_context"]["fingerprint"]
    trans(collective, "archive")
    check(
        "archive_changes_effective_context",
        simulation()["effective_context"]["fingerprint"] != first
        and "marcacolectiva" not in json.dumps(simulation()),
    )
    trans(collective, "restore", version=2)
    check(
        "restored_collective_is_new_effective_version",
        "marcacolectiva" in json.dumps(simulation()),
    )
    trans(dna, "archive")
    check(
        "archived_DNA_removed_from_composition",
        "marcadna" not in json.dumps(simulation()),
    )
    trans(dna, "restore", version=2)
    check("approved_DNA_rollback_retains_audit", "marcadna" in json.dumps(simulation()))
    conversations = sql(
        "SELECT TOP(2) ConversationId FROM crm.Conversation ORDER BY ConversationId"
    )
    conv, other = [str(v[0]).lower() for v in conversations]
    message = sql(
        (
            (
    'SELECT TOP(1) MessageId,Body FROM crm.Message WHERE Conver'
    "sationId=? AND Direction='incoming' ORDER BY Sequence"
)
        ),
        conv,
    )[0]
    val = message[1][:100]
    private = create(
        "private",
        "private",
        {
            "body": val,
            "visibility": "conversation_only",
            "source_message_id": str(message[0]).lower(),
            "quote": message[1][:2000],
        },
        conv,
    )
    trans(private)
    check(
        "private_memory_not_in_generic_simulation",
        val not in json.dumps(simulation(), ensure_ascii=False),
    )
    check(
        "private_memory_not_global_list",
        private["id"] not in json.dumps(call("memory"))
        and private["id"] not in json.dumps(call("knowledge")),
    )
    call(
        "conversation-memory/" + other + "/" + private["id"] + "/history", expected=404
    )
    check("foreign_conversation_record_not_disclosed")
    bad = body("private")
    bad.update(
        visibility="conversation_only",
        source_message_id=str(message[0]).lower(),
        quote="No está en el mensaje",
        body="No está",
    )
    call("conversation-memory/" + conv + "/" + str(uuid4()), "PUT", bad, 422)
    check("private_facts_require_literal_incoming_evidence")
    # Role controls and CSRF are exercised at the HTTP boundary.
    password = "P6 isolated qualification passphrase 73!"
    email = "p6-viewer-" + uuid4().hex[:8] + "@cbn.invalid"
    call(
        "users",
        "POST",
        dict(
            operation_id=str(uuid4()),
            email=email,
            full_name="Consulta P6",
            password=password,
            role="viewer",
        ),
    )
    viewer = Browser(create_app(settings))
    viewer.login(email, password)
    call("knowledge", expected=403, browser=viewer)
    call("memory", expected=403, browser=viewer)
    call("conversation-memory/" + conv, browser=viewer)
    call(
        private["prefix"] + "/" + private["id"] + "/archive",
        "POST",
        dict(
            operation_id=str(uuid4()),
            revision=private["revision"],
            reason="No autorizado",
            confirmed=True,
        ),
        403,
        browser=viewer,
    )
    check("viewer_private_read_only_and_no_collective_access")
    b.request("knowledge/search", "POST", {"query": "solazul"}, 403, csrf=False)
    check("POST_search_still_requires_CSRF")
    # Relevance evaluation is reproducible by IDs and ranking, not a confidence claim.
    questions = [
        ("Qué documentos son requisitos para inscripción", doc["id"]),
        ("Cuáles son las jornadas nocturnas", pdfid),
        ("Cómo consultar las becas educativas", pdfid),
    ]
    evaluation = []
    for question, expected in questions:
        result = call(
            "knowledge/evaluate",
            "POST",
            dict(
                query=question,
                expected_document_id=expected,
                program_id=None,
                stage_id=None,
            ),
        )
        evaluation.append(
            {
                "question": question,
                "expected": expected,
                "rank": result["rank"],
                "reciprocal_rank": result["reciprocal_rank"],
            }
        )
    check(
        "educational_questions_relevance_all_top_five",
        all(v["rank"] is not None for v in evaluation),
    )
    with admin(settings.connection["database"], readonly=True) as db:
        check("all_academic_rows_schema_intact", academic(db.cursor()) == before)
    check(
        "manual_previews_no_provider_no_delivery",
        all(
            not simulation()[v] for v in ["network_called", "delivered", "crm_written"]
        ),
    )
    save(
        WORK / "api-records.json",
        {
            "profile": label,
            "records": ids,
            "pdf": pdfid,
            "txt": txtid,
            "conversation": conv,
            "other_conversation": other,
            "guide": guide["id"],
            "program": program,
        },
    )
    save(
        WORK / "api-result.json",
        {
            "status": "passed",
            "checks": checks,
            "engine": 15,
            "compatibility": 150,
            "real_provider_calls": 0,
            "academic_preserved": True,
            "relevance": evaluation,
        },
    )
    print(json.dumps({"P6_API_checks": len(checks), "status": "passed"}))


if __name__ == "__main__":
    main()
