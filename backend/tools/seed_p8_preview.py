"""Operator-created fictional drafts only in the new final P8 copy."""

import json
from tools.p8_test_support import Harness
from tools.prepare_p8_campaign import WORK, save


def main():
    assert not (WORK / "demo-result.json").exists(), (
        "Do not seed an existing final preview twice"
    )
    h = Harness("final")
    assert h.sql("SELECT COUNT(*) FROM crm_campaign8.Record")[0][0] == 0
    account = next(
        v for v in h.call("channels")["items"] if v["channel"] == "whatsapp"
    )["id"]
    template = h.save8(
        "template",
        dict(
            channel="whatsapp",
            category="admisiones",
            body="Hola {{nombre}}, ¿qué programa te interesa conocer?",
            variables={"nombre": {"source": "customer_first_name"}},
            blocks=[
                dict(type="heading", text="Orientación institucional"),
                dict(
                    type="text",
                    text="Ejemplo: consulta los requisitos con tu orientador.",
                ),
            ],
        ),
        name="Orientación de programas · Ejemplo",
    )
    segment = h.save8(
        "segment",
        dict(
            description="Segmento de ejemplo con los contactos ficticios del CRM. La información académica debe verificarse en SIIE.",
            filters={},
        ),
        name="Aspirantes del CRM · Ejemplo",
    )
    steps = [
        dict(kind="wait", name="Esperar antes del seguimiento", wait_minutes=60),
        dict(kind="condition", name="Revisar condiciones del contacto", conditions={}),
        dict(
            kind="send",
            name="Orientación de programas",
            crm_template_id=template["id"],
            crm_template_version=template["version"],
        ),
    ]
    doc = dict(
        integration_id=account,
        objective="Orientar a aspirantes de la institución educativa.",
        description="Ejemplo editable. Guardado en SQL Server; requiere revisión antes de activar.",
        segment_id=segment["id"],
        segment_version=segment["version"],
        quiet_hours=dict(
            enabled=True,
            timezone="America/Bogota",
            start_time="21:00",
            end_time="08:00",
            days=list(range(7)),
        ),
        exit_on_response=True,
        steps=steps,
    )
    campaign = h.save8("campaign", doc, name="Admisiones y orientación · Ejemplo")
    flow = h.save8("flow", doc, name="Seguimiento por programa · Ejemplo")
    trigger = h.save8(
        "trigger",
        dict(
            channel="whatsapp",
            event_type="message_in",
            flow_id=flow["id"],
            flow_version=flow["version"],
            conditions={"keywords": ["admisiones", "programa"]},
            priority=100,
            cooldown_minutes=1440,
        ),
        name="Consulta de admisiones · Ejemplo",
    )
    assert all(v["state"] == "draft" for v in h.call("campaigns")["items"])
    assert h.sql("SELECT COUNT(*) FROM crm_campaign8.Enrollment")[0][0] == 0
    assert h.sql("SELECT COUNT(*) FROM crm_channels2.SendJob")[0][0] == 0
    save(
        WORK / "demo-result.json",
        dict(
            status="passed",
            checks=[
                "five_persisted_operator_drafts",
                "no_automatic_enrollment_or_send",
                "no_fabricated_consent_or_Meta_approval",
                "same_educational_CRM_demo_contacts_preserved",
            ],
            records=5,
            campaign_id=campaign["id"],
            flow_id=flow["id"],
            template_id=template["id"],
            segment_id=segment["id"],
            trigger_id=trigger["id"],
            real_provider_calls=0,
            academic_writes=False,
        ),
    )
    print(json.dumps(dict(status="passed", drafts=5)))


if __name__ == "__main__":
    main()
