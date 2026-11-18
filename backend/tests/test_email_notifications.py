from datetime import datetime, timezone
from email.message import EmailMessage
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import re
from fastapi import HTTPException

from app.institutional.email_notifications import (
    smtp_configuration,
    smtp_send,
    validate,
)
from app.institutional.email_policy import address, header, next_run, render, template


@pytest.mark.parametrize(
    "html",
    [
        "<script>alert(1)</script>",
        '<img src="https://tracking.invalid/pixel">',
        '<a href="javascript:alert(1)">Abrir</a>',
        '<form action="https://evil.invalid">a</form>',
        '<div onclick="alert(1)">a</div>',
        '<p style="background-image:url(https://evil.invalid)">a</p>',
        '<p style="color:expression(alert(1))">a</p>',
        '<svg onload="x">x</svg>',
        '<a href="https://user:secret@example.com">x</a>',
        '<iframe src="https://evil.invalid"></iframe>',
    ],
)
def test_rejects_executable_or_tracking_content(html):
    with pytest.raises(HTTPException):
        template(html)


def test_escaping_and_href_validation_survive_template_render():
    output = render(
        '<p>{{nombre}}</p><a href="{{enlace}}">Abrir</a>',
        {"nombre": '<script>"&', "enlace": "https://app.rinovaplus.com/?a=1&b=2"},
    )
    assert "<script>" not in output
    assert "&lt;script&gt;" in output
    assert "a=1&amp;b=2" in output
    with pytest.raises(HTTPException):
        render('<a href="{{enlace}}">Abrir</a>', {"enlace": "javascript:alert(1)"})


def test_missing_and_unknown_variables_block_publish():
    with pytest.raises(HTTPException):
        template("<p>{{password}}</p>")
    with pytest.raises(HTTPException):
        render("<p>{{nombre}}</p>", {})


@pytest.mark.parametrize(
    "value",
    [
        "x@example.com\r\nBcc:evil@example.com",
        "a@localhost",
        "A Name <a@example.com>",
        "a@b.com\n",
    ],
)
def test_recipient_header_injection(value):
    with pytest.raises(HTTPException):
        address(value)


def test_header_and_config_reject_unexpected_types():
    with pytest.raises(HTTPException):
        header("Hello\nBcc: x")
    for body in [
        {"enabled": "false"},
        {"daily_limit": True},
        {"daily_limit": 0},
        {"smtp_password": "no"},
    ]:
        with pytest.raises(HTTPException):
            validate("transport", body)


def test_daily_dst_gap_advances_without_duplicate_occurrence():
    now = datetime(2026, 3, 8, 5, tzinfo=timezone.utc)
    due = next_run(now, "America/New_York", "02:30", "daily")
    assert due == datetime(2026, 3, 8, 7, 30, tzinfo=timezone.utc)
    assert (
        next_run(due, "America/New_York", "02:30", "daily").date().isoformat()
        == "2026-03-09"
    )


def test_fold_chooses_one_occurrence_and_weekly_local_day():
    now = datetime(2026, 11, 1, 4, tzinfo=timezone.utc)
    due = next_run(now, "America/New_York", "01:30", "daily")
    assert due == datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc)
    assert next_run(due, "America/New_York", "01:30", "daily").day == 2
    assert next_run(now, "America/Bogota", "08:00", "weekly", 0).weekday() == 0


def test_only_oracle_tls_endpoint_is_accepted(monkeypatch):
    monkeypatch.setenv("CRM_SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("CRM_SMTP_USERNAME", "test")
    monkeypatch.setenv("CRM_SMTP_PASSWORD", "test")
    with pytest.raises(HTTPException):
        smtp_configuration()


class SMTP:
    recipient_code = 250
    data_failure = False
    quit_failure = False

    def __init__(self, host, port, timeout):
        assert port == 587 and timeout == 20
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        if self.quit_failure:
            raise OSError("connection ended after acceptance")

    def ehlo(self):
        self.calls.append("ehlo")

    def starttls(self, context):
        assert context.check_hostname
        self.calls.append("tls")

    def login(self, *_):
        assert "tls" in self.calls

    def mail(self, *_):
        return 250, b"ok"

    def rcpt(self, *_):
        return self.recipient_code, b"not logged"

    def data(self, raw):
        assert re.search(rb"(?<!\r)\n", raw) is None, "SMTP DATA must use CRLF"
        if self.data_failure:
            raise OSError("lost after DATA: possible acceptance")
        return 250, b"accepted"


@pytest.fixture
def mail(monkeypatch):
    for key, value in {
        "CRM_SMTP_HOST": "smtp.email.us-ashburn-1.oci.oraclecloud.com",
        "CRM_SMTP_USERNAME": "test",
        "CRM_SMTP_PASSWORD": "test",
    }.items():
        monkeypatch.setenv(key, value)
    message = EmailMessage()
    message["From"] = "RinovaPlus <notificaciones@rinovaplus.com>"
    message["To"] = "authorized@example.com"
    message.set_content("Prueba sin datos reales")
    return message


def test_smtp_acceptance_is_distinct_from_delivery(mail):
    with patch("smtplib.SMTP", SMTP):
        assert smtp_send(mail, "authorized@example.com") == ("accepted", None)


@pytest.mark.parametrize("code,state", [(450, "retry"), (550, "failed")])
def test_definitive_recipient_failure_is_safe_to_classify(mail, code, state):
    with patch("smtplib.SMTP", type("Failure", (SMTP,), {"recipient_code": code})):
        assert smtp_send(mail, "authorized@example.com")[0] == state


def test_unknown_data_result_never_automatically_retries(mail):
    with patch("smtplib.SMTP", type("Failure", (SMTP,), {"data_failure": True})):
        assert smtp_send(mail, "authorized@example.com")[0] == "uncertain"


def test_disconnect_after_250_does_not_duplicate_accepted_message(mail):
    with patch("smtplib.SMTP", type("Failure", (SMTP,), {"quit_failure": True})):
        assert smtp_send(mail, "authorized@example.com")[0] == "accepted"


def test_worker_disabled_does_not_open_storage(monkeypatch):
    from app.institutional.email_notifications import Worker

    monkeypatch.delenv("CRM_EMAIL_SCHEMA_ENABLED", raising=False)
    with patch(
        "app.institutional.email_notifications.transaction",
        side_effect=AssertionError("no IO"),
    ):
        assert Worker(SimpleNamespace(postgres_deployment=True)).once() is False


def test_access_link_is_available_in_plain_text_and_date_is_present(monkeypatch):
    import json
    from app.institutional import email_notifications as mail

    monkeypatch.setattr(mail, "key", lambda _: bytes(32))
    monkeypatch.setattr(mail, "institution", lambda _: "institution")
    monkeypatch.setattr(
        mail,
        "unseal",
        lambda *_: json.dumps(
            {
                "name": "RinovaPlus",
                "sender": "sender@example.invalid",
                "reply_to": "",
                "subject": "Activación de prueba",
                "html": '<p>Abre <a style="color:#12343B" href="https://example.invalid/#/access/redeem?token=fake-for-test">tu cuenta</a>.</p>',
            }
        ),
    )
    result = mail.build_message(
        None,
        SimpleNamespace(connection={"database": "test"}),
        {
            "id": "test-mail",
            "nonce": b"n",
            "ciphertext": b"c",
            "recipient": "authorized@example.invalid",
            "message_id": "<stable@example.invalid>",
        },
    )
    assert result["Date"]
    assert result["Message-ID"] == "<stable@example.invalid>"
    assert (
        "https://example.invalid/#/access/redeem?token=fake-for-test"
        in result.get_body(preferencelist=("plain",)).get_content()
    )


def test_recipients_respect_permission_inactive_role_and_preferences(monkeypatch):
    from app.institutional import email_notifications as mail

    people = [
        {
            "UserId": "allowed",
            "RoleKey": "admin",
            "Active": 1,
            "Actions": '["users.manage"]',
        },
        {"UserId": "denied", "RoleKey": "admin", "Active": 1, "Actions": "[]"},
        {
            "UserId": "inactive",
            "RoleKey": "admin",
            "Active": 0,
            "Actions": '["users.manage"]',
        },
        {
            "UserId": "optout",
            "RoleKey": "admin",
            "Active": 1,
            "Actions": '["users.manage"]',
        },
    ]
    monkeypatch.setattr(mail, "users", lambda *_: people)
    monkeypatch.setattr(
        mail,
        "documents",
        lambda _c, _s, kind: (
            [{"id": "optout", "body": {"disabled_events": ["users.create"]}}]
            if kind == "preference"
            else []
        ),
    )
    result = mail.selected_users(
        None, None, {"roles": ["admin"]}, "users.manage", "users.create"
    )
    assert [p["UserId"] for p in result] == ["allowed"]


def test_group_membership_does_not_grant_new_access(monkeypatch):
    from app.institutional import email_notifications as mail

    monkeypatch.setattr(
        mail,
        "users",
        lambda *_: [
            {"UserId": "member", "RoleKey": "viewer", "Active": 1, "Actions": "[]"}
        ],
    )
    monkeypatch.setattr(
        mail,
        "documents",
        lambda _c, _s, kind: (
            [{"id": "supervisors", "body": {"users": ["member"]}}]
            if kind == "group"
            else []
        ),
    )
    assert (
        mail.selected_users(
            None, None, {"groups": ["supervisors"]}, "users.manage", "users.create"
        )
        == []
    )


def test_active_rules_require_a_published_template_and_selected_recipients(monkeypatch):
    from app.institutional import email_notifications as mail

    monkeypatch.setattr(mail, "document", lambda *_: {"body": {"published": False}})
    with pytest.raises(HTTPException) as error:
        mail.validate_activation(
            None,
            None,
            "rule",
            {"enabled": True, "template": "draft", "roles": ["owner"]},
        )
    assert error.value.detail == "email_template_not_published"
    monkeypatch.setattr(mail, "document", lambda *_: {"body": {"published": True}})
    with pytest.raises(HTTPException) as error:
        mail.validate_activation(
            None, None, "rule", {"enabled": True, "template": "valid"}
        )
    assert error.value.detail == "email_recipient_selection_required"
    mail.validate_activation(
        None, None, "rule", {"enabled": True, "template": "valid", "roles": ["owner"]}
    )


def test_disabled_rule_can_be_saved_as_an_incomplete_draft(monkeypatch):
    from app.institutional import email_notifications as mail

    monkeypatch.setattr(
        mail, "document", lambda *_: pytest.fail("draft must not require template IO")
    )
    mail.validate_activation(None, None, "rule", {"enabled": False})


@pytest.mark.parametrize(
    "endpoint,method,body",
    [
        ("/api/institution/notifications", "get", None),
        (
            "/api/institution/notifications/preview",
            "post",
            {"html": "<p>Hola</p>", "values": {}},
        ),
        (
            "/api/institution/notifications/documents/transport/main",
            "put",
            {"revision": 0, "body": {}},
        ),
    ],
)
def test_mail_admin_routes_check_authority_before_reading_or_writing(
    monkeypatch, endpoint, method, body
):
    from contextlib import contextmanager
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.institutional import email_notifications as mail

    @contextmanager
    def tx(*_args, **_kwargs):
        yield SimpleNamespace(
            native=lambda *_: pytest.fail("unauthorized storage access")
        )

    def denied(*_args, **_kwargs):
        raise HTTPException(403, "permission_denied")

    monkeypatch.setenv("CRM_EMAIL_SCHEMA_ENABLED", "1")
    monkeypatch.setattr(mail, "transaction", tx)
    monkeypatch.setattr(mail, "authorize", denied)
    app = FastAPI()

    @app.middleware("http")
    async def authority(request, call_next):
        request.state.authority = {}
        return await call_next(request)

    mail.install(app, SimpleNamespace(postgres_deployment=True))
    response = getattr(TestClient(app), method)(
        endpoint, **({"json": body} if body is not None else {})
    )
    assert response.status_code == 403


def test_recovery_does_not_enumerate_accounts_when_mail_is_disabled(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.institutional import email_notifications as mail

    monkeypatch.delenv("CRM_EMAIL_SCHEMA_ENABLED", raising=False)
    app = FastAPI()
    mail.install(app, SimpleNamespace(postgres_deployment=True))
    client = TestClient(app)
    first = client.post(
        "/api/institution/auth/recover-email", json={"email": "known@example.invalid"}
    )
    second = client.post(
        "/api/institution/auth/recover-email", json={"email": "unknown@example.invalid"}
    )
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert "token" not in first.text


def test_report_period_query_uses_the_declared_audit_schema(monkeypatch):
    import re
    from pathlib import Path
    from datetime import datetime, timedelta, timezone
    from unittest.mock import MagicMock
    from app.institutional import email_notifications as mail

    ddl = (
        Path(__file__).parents[1]
        / "migrations/cbn_institutional_spanish_v1/P2ES_002_access.sql"
    ).read_text(encoding="utf-8")
    audit_ddl = ddl.split("CREATE TABLE [dbo].[CRMAccesoAuditoria](", 1)[1].split(
        "CREATE INDEX", 1
    )[0]
    schema_columns = set(re.findall(r"\b([A-Za-z]+At)\s+datetime2", audit_ddl))
    cursor = MagicMock()
    cursor.native.return_value.fetchval.return_value = {
        "next": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    }

    def execute(sql, *_):
        assert set(re.findall(r"\b([A-Za-z]+At)\b", sql)) <= schema_columns
        return MagicMock()

    cursor.execute.side_effect = execute
    monkeypatch.setattr(mail, "institution", lambda _: "institution")
    monkeypatch.setattr(
        mail,
        "documents",
        lambda *_: [
            {
                "id": "daily",
                "revision": 1,
                "body": {
                    "enabled": True,
                    "frequency": "daily",
                    "zone": "America/Bogota",
                    "time": "08:00",
                    "template": "source",
                },
            }
        ],
    )
    monkeypatch.setattr(mail, "document", lambda *_: {"body": {"published": True}})
    monkeypatch.setattr(mail, "selected_users", lambda *_: [])
    mail.due_reports(cursor, None)
    assert cursor.execute.call_count == 1
