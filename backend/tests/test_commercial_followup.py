from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.institutional import campaigns
from app.institutional import commercial_followup as f
from app.institutional.cbn_profile import PREICFES_REGISTRATION_URL, REGISTRATION_URL


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Quiero aprovecharlo", "interest_confirmed"),
        ("Quiero inscribirme", "interest_confirmed"),
        ("Me interesa el programa de cocina", "interest_confirmed"),
        ("Compárteme el formulario", "interest_confirmed"),
        ("Ya diligencié el formulario", "form_reported_complete"),
        ("He completado la inscripción", "form_reported_complete"),
        ("No quiero inscribirme", None),
        ("No he llenado el formulario", None),
        ("¿Ya envié el formulario?", None),
        ("¿Cuánto cuesta?", None),
        ("Ver horarios", None),
        ("Sí", "review_positive"),
        ("No recibir mensajes", None),
    ],
)
def test_only_customer_statements_support_progress(text, expected):
    assert f.classification(text, "incoming") == expected


@pytest.mark.parametrize(
    "prior,expected",
    [
        (
            "¿Te gustaría que te comparta el formulario de inscripción?",
            "interest_confirmed",
        ),
        ("¿Te gustaría avanzar con la inscripción?", "interest_confirmed"),
        ("¿Tienes dudas?", "review_positive"),
        ("¿Quieres el formulario o más información?", "review_positive"),
        ("¿No quieres inscribirte?", "review_positive"),
        ("¿Ya pagaste la inscripción?", "review_positive"),
    ],
)
def test_yes_requires_the_actual_preceding_question(prior, expected):
    assert f.classification("Sí", "incoming", previous=prior) == expected


@pytest.mark.parametrize("url", [REGISTRATION_URL, PREICFES_REGISTRATION_URL])
def test_form_requires_exact_official_link_and_real_provider_acknowledgement(url):
    assert (
        f.classification("Diligencia aquí: " + url + ".", "outgoing", accepted=True)
        == "form_sent"
    )
    assert f.classification(url, "outgoing", accepted=False) is None
    assert f.classification(url, "incoming") is None
    assert f.classification(url + "/fake", "outgoing", accepted=True) is None
    assert (
        f.classification(
            url.replace("siieplus.online", "siieplus.online.evil"),
            "outgoing",
            accepted=True,
        )
        is None
    )
    assert (
        f.classification("¿Quieres el formulario?", "outgoing", accepted=True) is None
    )


@pytest.mark.parametrize("state", [*f.CASES, "review_positive"])
def test_generic_marketing_is_blocked_without_revoking_response_permission(state):
    assert (
        f.exclusion({"state": state}, "Seguimiento", {})
        == "commercial_progress_requires_case_followup"
    )
    assert f.exclusion({"state": state}, "Seguimiento", {"followup_only": True})
    target = {"followup_only": True, "entry_conditions": {"followup_states": [state]}}
    assert f.exclusion({"state": state}, "Seguimiento", target) is None
    assert f.exclusion(
        {"state": state},
        "Seguimiento",
        {"followup_only": False, "entry_conditions": {"followup_states": [state]}},
    )


@pytest.mark.parametrize(
    "stage",
    ["Inscripción", "Matriculado", "Propuesta y financiación", "Dudas y objeciones"],
)
def test_advanced_stage_is_never_a_generic_reactivation_target(stage):
    assert f.exclusion({}, stage, {}) == "advanced_stage_no_reactivation"


def test_conditions_are_revalidated_when_case_advances():
    p = {"CommercialProgress": {"state": "form_sent"}}
    assert campaigns.matches(p, {"followup_states": ["form_sent"]})
    assert not campaigns.matches(p, {"followup_states": ["interest_confirmed"]})
    assert not campaigns.matches({}, {"followup_states": ["form_sent"]})


def test_case_flows_keep_their_scope_in_the_native_meta_dispatch_document():
    doc = {
        "integration_id": "account",
        "channel": "whatsapp",
        "followup_only": True,
        "entry_conditions": {"followup_states": ["form_sent"]},
        "ab_test": {"enabled": False},
        "timezone": "America/Bogota",
    }
    step = {
        "meta_template_id": "template",
        "meta_template_version": 1,
        "variables": {},
        "header_media_url": "",
    }
    selected = campaigns.send_document(doc, step, "A")
    assert selected["followup_only"]
    assert f.exclusion({"state": "form_sent"}, "Seguimiento", selected) is None
    assert f.exclusion({"state": "interest_confirmed"}, "Seguimiento", selected)


def test_signal_queries_are_scoped_and_exclude_unsent_drafts(monkeypatch):
    queries = []
    monkeypatch.setattr(f.db, "institution", lambda s: "institution")
    monkeypatch.setattr(
        f.db, "rows", lambda c, sql, *args: queries.append((sql, args)) or []
    )
    f.signals(None, None, "contact")
    sql, args = queries[0]
    assert args == ("institution", "contact")
    assert "r.InstitutionId=?" in sql and "r.ActorKind='external'" in sql
    assert (
        "q.ExternalId IS NOT NULL" in sql
        and "'accepted','sent','delivered','read'" in sql
    )
    assert "TOP(5001)" in sql


def item(stage="Nuevo", state="form_sent", held=False):
    return {
        "contact_id": str(uuid4()),
        "state": state,
        "message_id": str(uuid4()),
        "conversation_id": str(uuid4()),
        "stage": stage,
        "observed_at": "2026-11-25T12:00:00Z",
        "previous_revision": 0,
        "held": held,
        "no_contact": False,
        "receipt_state": "delivered",
        "quote": "evidence",
        "label": "Avance",
        "next_action": "Ayudar con formulario",
    }


@pytest.mark.parametrize(
    "stage,manual,held,expected",
    [
        ("Nuevo", False, False, True),
        ("Calificación", False, False, True),
        ("Inscripción", False, False, False),
        ("Matriculado", False, False, False),
        ("Nuevo", True, False, False),
        ("Nuevo", False, True, False),
    ],
)
def test_followup_task_is_distinct_and_stage_updates_respect_manual_or_advanced_choices(
    monkeypatch, stage, manual, held, expected
):
    from app.modules.crm_configuration.application import service

    statements = []

    class C:
        rowcount = 1

        def execute(self, sql, *args):
            statements.append((sql, args))
            self.sql = sql
            return self

        def fetchone(self):
            return (
                (1,)
                if self.sql.startswith("SELECT 1 FROM crm_access.Audit") and manual
                else None
            )

    monkeypatch.setattr(f.db, "institution", lambda s: "institution")
    monkeypatch.setattr(f, "save", lambda *a: None)
    monkeypatch.setattr(f.db, "audit", lambda *a, **k: None)
    monkeypatch.setattr(
        service,
        "read_configuration",
        lambda *a, **kw: (
            SimpleNamespace(stages=[SimpleNamespace(active=True, label="Seguimiento")]),
            1,
        ),
    )
    selected = item(stage, "review_positive" if held else "form_sent", held)
    assert f.commit(C(), None, selected)
    assert (
        any(sql.startswith("UPDATE crm.Contact") for sql, args in statements)
        == expected
    )
    inserts = [
        args for sql, args in statements if sql.startswith("INSERT crm_workspace.Task")
    ]
    assert len(inserts) == 1
    assert not any(
        "crm.Message" in sql or "SendJob" in sql or "Consent" in sql
        for sql, args in statements
    )
    assert any(
        sql.startswith("UPDATE crm_workspace.Task") for sql, args in statements
    ) == (not held)


def test_opt_out_produces_no_task_or_stage_change():
    chosen = item()
    chosen["no_contact"] = True
    assert f.commit(None, None, chosen) is False


def test_scope_limit_fails_closed():
    with pytest.raises(HTTPException, match="commercial_followup_scope_limit"):
        f.evidence(None, None, [{}] * 5001)


def test_incoming_opt_out_cancels_only_own_pending_tasks_without_new_messages(
    monkeypatch,
):
    from app.institutional import contact_preference

    contact = str(uuid4())
    queries = []

    class C:
        def execute(self, sql, *args):
            queries.append((sql, args))
            return self

    monkeypatch.setattr(contact_preference, "blocked", lambda *a: True)
    monkeypatch.setattr(f.db, "institution", lambda s: "institution")
    f.observe(C(), SimpleNamespace(postgres_deployment=True), contact)
    assert len(queries) == 4
    assert all(
        "Status='pending'" in sql and sql.startswith("UPDATE crm_workspace.Task")
        for sql, args in queries
    )
    assert len({args[1] for sql, args in queries}) == 4
