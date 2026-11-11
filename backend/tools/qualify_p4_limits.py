"""Long Unicode conversion against the immutable P3 NVARCHAR note contract."""

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
    settings = load(Path(read(WORK / "fixture-profile.json")["directory"]))
    access = read(WORK / "fixture-access.json")
    browser = Browser(create_app(settings))
    browser.login(access["email"], access["password"])
    identity, body = str(uuid4()), "😀" * 4002 + " Comentario original íntegro"
    with transaction(settings, True, anonymous=True) as c:
        integration = c.execute(
            "SELECT TOP(1) IntegrationId FROM crm_channels2.Integration "
            "WHERE Channel='facebook' AND RequestedStatus='connected' "
            "AND VerifiedStatus='verified'"
        ).fetchval()
        c.execute(
            "INSERT crm_channels2.SocialComment(InstitutionId,CommentId,IntegrationId,"
            "ExternalId,AuthorExternalId,Body,Payload,ReceivedAt) "
            "VALUES(?,?,?,?,?,?,'{}',SYSUTCDATETIME())",
            institution(settings),
            identity,
            integration,
            "owned-limit-" + uuid4().hex,
            "owned-author-" + uuid4().hex,
            body,
        )
        revision = c.execute(
            "SELECT RowVersion FROM crm_channels2.SocialComment WHERE CommentId=?",
            identity,
        ).fetchval()
    command = {
        "operation_id": str(uuid4()),
        "row_version": bytes(revision).hex(),
        "action": "convert",
        "display_name": "Conversión Unicode controlada",
    }
    result = browser.request("comments/" + identity, "POST", command).json()
    replay = browser.request("comments/" + identity, "POST", command).json()
    assert result == replay
    with transaction(settings, anonymous=True) as c:
        note = one(
            c,
            "SELECT Body FROM crm_workspace.Note WHERE ContactId=?",
            uid(result["contact_id"]),
        )
        assert 0 < len(note["Body"].encode("utf-16-le")) <= 4000
        assert (
            c.execute(
                "SELECT Body FROM crm_channels2.SocialComment WHERE CommentId=?",
                identity,
            ).fetchval()
            == body
        )
        assert (
            c.execute(
                "SELECT COUNT(*) FROM crm_workspace.Note WHERE ContactId=?",
                uid(result["contact_id"]),
            ).fetchval()
            == 1
        )
    save(
        WORK / "limits-result.json",
        {
            "status": "passed",
            "checks": [
                "long_unicode_comment_converts_without_SQL_truncation",
                "original_comment_preserved",
                "conversion_replay_preserves_one_note",
            ],
            "real_provider_calls": 0,
        },
    )
    print(json.dumps({"passed": 3, "real_provider_calls": 0}))


if __name__ == "__main__":
    main()
