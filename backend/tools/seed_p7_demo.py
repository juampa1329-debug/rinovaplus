"""Explicit local draft example in the new final copy; no provider effects."""

import json
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.spanish import load
from app.institutional.store import transaction
from tools.prepare_p7_broadcast import WORK, admin, read, save
from tools.qualify_p3_workspace import Browser
from tools.qualify_p4_deployment import fingerprint
from tools.qualify_p4_storage import academic


def main():
    assert not (WORK / "demo-result.json").exists(), "P7 demo is explicit and one-shot"
    profile = load(Path(read(WORK / "final-profile.json")["directory"]))
    assert profile.ticket["version"] == "cbn-institutional-broadcast-p7-v1"
    source = read(WORK / "final-source-snapshot.json")
    with admin(profile.connection["database"], readonly=True) as db:
        assert fingerprint(db.cursor(), set(source["names"])) == source["business"]
        assert academic(db.cursor()) == source["academic"]
    b = Browser(create_app(profile))
    access = read(WORK / "final-access.json")
    b.login(access["email"], access["password"])
    b.request("broadcasts/options")
    from app.institutional.broadcast_policy import layout

    additions = [
        layout()["tables"]["crm_channels2." + n]
        for n in [
            "Application",
            "Integration",
            "WebhookEndpoint",
            "EndpointIntegration",
            "SecretVersion",
        ]
    ]
    import hashlib
    from collections import Counter

    from tools.foundation_snapshot import encode, quote_name

    def catalog_rows(db):
        result = {}
        for table in additions:
            c = db.cursor()
            cols = [
                v[0]
                for v in c.execute(
                    (
                        "SELECT name FROM sys.columns WHERE obj"
                        "ect_id=OBJECT_ID(?) ORDER BY column_id"
                    ),
                    table,
                ).fetchall()
            ]
            projection = ",".join(
                "CONVERT(varbinary(max)," + quote_name(n) + ")" for n in cols
            )
            result[table] = Counter(
                hashlib.sha256(encode(list(row))).hexdigest()
                for row in c.execute(
                    "SELECT " + projection + " FROM " + table
                ).fetchall()
            )
        return result

    with admin(profile.connection["database"], readonly=True) as db:
        catalog_before = catalog_rows(db)
    stable = set(source["names"]) - set(additions)
    with admin(profile.connection["database"], readonly=True) as db:
        before_stable = fingerprint(db.cursor(), stable)
    account = b.request(
        "channels",
        "POST",
        dict(
            operation_id=str(uuid4()),
            channel="whatsapp",
            display_name="Admisiones WhatsApp · Ejemplo pendiente",
            issuer_profile="meta_whatsapp",
            client_id="270700000000000",
            api_version="v24.0",
        ),
    ).json()["id"]
    key = str(uuid4())
    campaign = str(uuid4())

    def command(**extra):
        return dict(
            operation_id=str(uuid4()),
            revision=0,
            reason="Ejemplo ficticio editable de admisiones",
            **extra,
        )

    template = b.request(
        "broadcasts/accounts/" + account + "/templates/" + key,
        "PUT",
        command(
            name="orientacion_admisiones_ejemplo",
            language="es",
            body_text=("Hola {{1}}, conoce la orientación de admisiones de CBN."),
            header_type="TEXT",
            header_text="Admisiones CBN",
            footer_text="Ejemplo ficticio: requiere aprobación de Meta",
            buttons=[{"type": "QUICK_REPLY", "text": "Solicitar información"}],
        ),
    ).json()
    b.request(
        "broadcasts/" + campaign,
        "PUT",
        command(
            name="Orientación de admisiones · Ejemplo",
            integration_id=account,
            template_id=key,
            template_version=template["version"],
            variables={"body.1": {"source": "customer_first_name"}},
            filters={},
            timezone="America/Bogota",
        ),
    )
    with admin(profile.connection["database"], readonly=True) as db:
        preserved = fingerprint(db.cursor(), stable) == before_stable
        academic_same = academic(db.cursor()) == source["academic"]
        catalog_after = catalog_rows(db)
        assert all(not (catalog_before[t] - catalog_after[t]) for t in additions), (
            "existing C10 account rows must be byte-identical"
        )
    with transaction(profile, anonymous=True) as c:
        counts = {
            n: c.execute("SELECT COUNT(*) FROM " + table).fetchval()
            for n, table in [
                ("contacts", "crm.Contact"),
                ("conversations", "crm.Conversation"),
                ("messages", "crm.Message"),
                ("knowledge", "crm_knowledge6.Record"),
            ]
        }
        assert c.execute("SELECT COUNT(*) FROM crm_broadcast7.Attempt").fetchval() == 0
        assert c.execute("SELECT COUNT(*) FROM crm_broadcast7.Consent").fetchval() == 0
    assert preserved and academic_same
    save(
        WORK / "demo-result.json",
        {
            "status": "passed",
            "checks": [
                (
                    "inherited_P6_business_rows_unchanged_p"
                    "lus_explicit_C10_account_draft_additio"
                    "ns"
                ),
                "academic_tables_unchanged",
                "one_operator_template_draft_and_campaign_persisted",
                ("no_recipient_queue_consent_or_provider_approval_fabricated"),
            ],
            "counts": counts,
            "preserved_business_tables": len(stable),
            "account_draft_additions_to_tables": additions,
            "P7_drafts": 1,
            "real_provider_calls": 0,
            "approved_templates": 0,
            "campaign_id": campaign,
            "template_id": key,
        },
    )
    print(
        json.dumps(
            {
                "status": "passed",
                "P7_demo_drafts": 1,
                "counts": counts,
                "real_provider_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
