"""Add clearly fictional, non-egress comments only to the new final P4 copy."""

import json
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.db import institution, one, uid
from app.institutional.spanish import load
from app.institutional.store import transaction
from tools.prepare_p4_channels import WORK, read, save
from tools.qualify_p3_workspace import Browser


def main():
    if (WORK / "demo-result.json").exists():
        raise ValueError("P4ES_preview_demo_already_exists")
    settings = load(Path(read(WORK / "final-profile.json")["directory"]))
    access = read(WORK / "final-access.json")
    browser = Browser(create_app(settings))
    browser.login(access["email"], access["password"])
    with transaction(settings, anonymous=True) as c:
        # Any live legacy credentials need an explicit reviewed promotion.
        legacy = c.execute(
            "SELECT COUNT(*) FROM crm_access.Secret WHERE Scope='channel'"
        ).fetchval()
        assert legacy == 0, "P4ES_legacy_credentials_require_review"
        assert (
            c.execute("SELECT COUNT(*) FROM crm_channels2.Application").fetchval() == 0
        )
        before = {
            t: c.execute("SELECT COUNT(*) FROM " + t).fetchval()
            for t in [
                "crm.Contact",
                "crm.Conversation",
                "crm.Message",
                "crm_workspace.Note",
                "crm_workspace.Task",
            ]
        }
        linked = one(
            c,
            "SELECT TOP(1) c.ContactId,v.ConversationId FROM crm.Contact c "
            "JOIN crm.Conversation v ON v.ContactId=c.ContactId "
            "WHERE c.Name LIKE N'Demo · %' ORDER BY c.ContactId",
        )
    created = browser.request(
        "channels",
        "POST",
        {
            "operation_id": str(uuid4()),
            "channel": "facebook",
            "display_name": "Demo · Admisiones CBN (ficticia)",
            "issuer_profile": "facebook_login",
            "client_id": "demo-cbn-no-provider",
            "api_version": "v24.0",
        },
    ).json()
    comments = []
    with transaction(settings, True, anonymous=True) as c:
        c.execute(
            "UPDATE crm_channels2.Application SET "
            "EgressProfile='synthetic_no_provider' "
            "WHERE InstitutionId=? AND ApplicationId=?",
            institution(settings),
            created["application_id"],
        )
        for index, text in enumerate(
            [
                "Ejemplo ficticio: ¿qué documentos necesito "
                "para inscribirme en Enfermería?",
                "Ejemplo ficticio: me interesa conocer los horarios "
                "del programa de Sistemas.",
                "Ejemplo ficticio: gracias por la información "
                "sobre becas y admisiones.",
            ]
        ):
            identity = str(uuid4())
            crm = {"synthetic_demo": True, "state": "archived" if index == 2 else "new"}
            if index == 0:
                crm.update(
                    contact_id=uid(str(linked["ContactId"])),
                    conversation_id=uid(str(linked["ConversationId"])),
                )
            c.execute(
                "INSERT crm_channels2.SocialComment(InstitutionId,CommentId,"
                "IntegrationId,"
                "ExternalId,AuthorExternalId,Body,Payload,ReceivedAt) "
                "VALUES(?,?,?,?,?,?,?,SYSUTCDATETIME())",
                institution(settings),
                identity,
                created["id"],
                "demo-comment-" + str(index),
                "Persona ficticia " + str(index + 1),
                text,
                json.dumps({"_crm": crm, "provider": {}}, ensure_ascii=False),
            )
            comments.append(identity)
        after = {t: c.execute("SELECT COUNT(*) FROM " + t).fetchval() for t in before}
        assert before == after
        assert c.execute("SELECT COUNT(*) FROM crm_channels2.SendJob").fetchval() == 0
    save(
        WORK / "demo-result.json",
        {
            "status": "passed",
            "preserved_P3_records": before,
            "comments": 3,
            "paused_synthetic_accounts": 1,
            "provider_calls": 0,
            "outbound_jobs": 0,
            "academic_writes": False,
        },
    )
    save(
        WORK / "demo-records.json",
        {"integration_id": created["id"], "comment_ids": comments},
    )
    print(
        json.dumps(
            {
                "persisted_comments": 3,
                "previous_demo_records_preserved": True,
                "provider_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
