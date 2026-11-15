"""Run real HTTP and worker flows in a disposable, network-isolated PostgreSQL fixture."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import tempfile
import time
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import httpx2 as httpx
import psycopg2
from fastapi.testclient import TestClient
from PIL import Image
from psycopg2 import sql

from app.institutional import operations_policy
from app.institutional.api import create_app
from app.institutional.channel_secrets import put
from app.institutional.crypto import password_hash
from app.institutional.policy import ACTIONS, MODULES
from app.institutional.postgres_dialect import Cursor
from app.institutional.postgres_rehearsal import DATABASE, load, transaction
from app.modules.channels.providers import ProviderFailure
from app.modules.crm_configuration.application.service import Configuration
from tools.postgres_crm_schema import TABLE, build
from tools.postgres_runtime_role import grants

DIGEST = "a" * 64
ROOT = Path(__file__).resolve().parents[1]
PREFIX = "/api/institution"
AUTH = PREFIX + "/auth"
WORKSPACE = PREFIX + "/workspace"
LOCAL = {"X-CRM-Local": "1"}
FIXTURE_ROLE = "rinova_pg_fixture"
PHONE = "15551231234"


def seed_catalog(dsn, runtime_password, source_sha256=None):
    with closing(psycopg2.connect(dsn)) as conn:
        conn.autocommit = True
        with conn.cursor() as c:
            c.execute("SELECT current_database(),to_regnamespace('rinovaplus_crm')")
            database, schema = c.fetchone()
            if database != DATABASE or bool(schema) != bool(source_sha256):
                raise RuntimeError("Disposable database required")
            if schema:
                c.execute("SELECT tablename FROM pg_tables WHERE schemaname='rinovaplus_crm'")
                for (table,) in c.fetchall():
                    c.execute(sql.SQL("SELECT 1 FROM rinovaplus_crm.{} LIMIT 1").format(sql.Identifier(table)))
                    if c.fetchone():
                        raise RuntimeError("An empty schema-only copy is required")
            c.execute(
                """CREATE SCHEMA rinova_migration;
                   CREATE TABLE rinova_migration.source_snapshot(archive_sha256 text PRIMARY KEY);
                   CREATE TABLE rinova_migration.source_row(source_table text,source_values json);
                """
            )
            c.execute("INSERT INTO rinova_migration.source_snapshot VALUES(%s)", (source_sha256 or DIGEST,))
            if not schema:
                source = json.loads(
                    (operations_policy.parent.PACKAGE / "expected-model.json").read_text(encoding="utf-8")
                )
                model = {
                    section: [
                        row for row in values
                        if TABLE.fullmatch(row["schema"] + "." + row["name" if section == "tables" else "table"])
                    ]
                    for section, values in source.items()
                }
                c.execute(build(model, DIGEST))
                c.execute((ROOT / "migrations/postgresql/001_copy_queries_and_queues.sql").read_text())
            c.execute("CREATE ROLE rinova_pg_fixture LOGIN PASSWORD %s", (runtime_password,))
            c.execute("REVOKE CREATE ON DATABASE rinovaplus_rehearsal FROM PUBLIC")
            c.execute("\n".join(grants(FIXTURE_ROLE, DATABASE)))
            c.execute("SELECT has_table_privilege(%s, 'rinova_migration.source_row', 'SELECT')", (FIXTURE_ROLE,))
            assert c.fetchone() == (False,)


def seed_institution(dsn, institution, password):
    mapping = operations_policy.layout()["tables"]
    now = "SYSUTCDATETIME()"
    config = Configuration(stages=[{"key": "new", "label": "Nuevo"}], tags=[], fields=[])
    stage = next(item for item in config.stages if item.active)
    owner, limited = str(uuid4()), str(uuid4())
    with closing(psycopg2.connect(dsn)) as conn, conn, conn.cursor() as raw:
        c = Cursor(raw, mapping, {})
        c.execute(
            f"INSERT crm_channels2.Context(ContextId,InstitutionId,ContractVersion,CreatedAt) "
            f"VALUES(1,?,'CBN-channels-parity-v1',{now})", institution,
        )
        c.execute(f"INSERT crm_access.Institution(InstitutionId,InitializedAt) VALUES(?,{now})", institution)
        for role, name, actions in (
            ("owner", "Owner", list(ACTIONS)),
            ("agent", "Agent", ["inbox.read"]),
        ):
            c.execute(
                "INSERT crm_access.Role(InstitutionId,RoleKey,Name,Actions,Protected,Active,Revision)"
                " VALUES(?,?,?,?,1,1,1)",
                institution, role, name, json.dumps(actions),
            )
        for identity, email, role in (
            (owner, "owner@example.invalid", "owner"),
            (limited, "agent@example.invalid", "agent"),
        ):
            c.execute(
                "INSERT crm_access.AccessUser(InstitutionId,UserId,Login,NormalizedLogin,DisplayName,"
                "Profile,PasswordHash,RoleKey,Active,AuthVersion,Revision) VALUES(?,?,?,?,?,'{}',?,?,1,1,1)",
                institution, identity, email, email, role, password_hash(password), role,
            )
        for section, document in (
            ("modules", {"enabled": dict.fromkeys(MODULES, True)}),
            ("budgets", {"requests_per_minute": 120, "daily_messages": 20}),
        ):
            c.execute(
                "INSERT crm_access.Setting(InstitutionId,Section,Document,Revision,UpdatedAt)"
                f" VALUES(?,?,?,1,{now})",
                institution, section, json.dumps(document),
            )
        c.execute(
            "INSERT crm_config.Configuration(ConfigurationId,Document,Revision) VALUES(1,?,1)",
            config.model_dump_json(),
        )
        c.execute("INSERT crm_workspace.State(StateId,Revision) VALUES(1,1)")
        c.execute("INSERT crm_channels4.Configuration(InstitutionId,OutboundEnabled) VALUES(?,1)", institution)
    return stage, hashlib.sha256(config.model_dump_json().encode()).digest()


def seed_channel(settings, stage, config_digest):
    institution = settings.ticket["context"][0][1]
    app, integration, endpoint = (str(uuid4()) for _ in range(3))
    verify, signature_secret, access_secret = (secrets.token_urlsafe(32) for _ in range(3))
    key = "ep_" + secrets.token_urlsafe(32)
    with transaction(settings, True, anonymous=True) as c:
        c.execute(
            "INSERT crm_channels2.Application(InstitutionId,ApplicationId,ClientId,Provider,ApiVersion,"
            "IssuerProfile,RedirectUri,EgressProfile,State,CreatedAt,UpdatedAt)"
            " VALUES(?,?,'3357','meta','v20.0','meta_whatsapp','https://example.invalid',"
            "'pinned','enabled',SYSUTCDATETIME(),SYSUTCDATETIME())",
            institution, app,
        )
        c.execute(
            "INSERT crm_channels2.Integration(InstitutionId,IntegrationId,ApplicationId,Channel,Provider,"
            "ApiVersion,DispatchMode,DisplayName,ExternalNamespace,ExternalAccountId,RequestedStatus,"
            "VerifiedStatus,InitialStageKey,InitialStageConfigHash,CreatedAt,UpdatedAt)"
            " VALUES(?,?,?,'whatsapp','meta','v20.0','live','Fixture',?,'7733','connected','verified',"
            "?,?,SYSUTCDATETIME(),SYSUTCDATETIME())",
            institution, integration, app, bytes.fromhex("8a" * 32), stage.key, config_digest,
        )
        c.execute(
            "INSERT crm_channels2.WebhookEndpoint(InstitutionId,EndpointId,ApplicationId,Provider,"
            "ChannelSelector,EndpointKey,SignatureProfile,SignatureRequired,IsActive,CreatedAt,UpdatedAt)"
            " VALUES(?,?,?,'meta','whatsapp',?,'meta_sha256',1,1,SYSUTCDATETIME(),SYSUTCDATETIME())",
            institution, endpoint, app, key,
        )
        c.execute(
            "INSERT crm_channels2.EndpointIntegration(InstitutionId,EndpointId,IntegrationId,ApplicationId,"
            "RouteKind,ExternalId,IsActive,CreatedAt) VALUES(?,?,?,?,'configured_whatsapp','7733',1,SYSUTCDATETIME())",
            institution, endpoint, integration, app,
        )
        put(c, settings, "endpoint", endpoint, "webhook_verify", verify)
        put(c, settings, "application", app, "meta_app_secret", signature_secret)
        put(c, settings, "integration", integration, "meta_permanent_access", access_secret)
    return key, verify, signature_secret


def checked(response, expected=200):
    assert response.status_code == expected, (response.request.method, response.request.url.path, response.status_code)
    return response.json()


def seed_worker_recovery(settings, thread):
    institution = settings.ticket["context"][0][1]
    agent, request, enrollment, flow = (str(uuid4()) for _ in range(4))
    with transaction(settings, True, anonymous=True) as c:
        actor, session = c.execute(
            "SELECT s.UserId,s.SessionId FROM crm_access.Session s JOIN crm_access.AccessUser u"
            " ON u.InstitutionId=s.InstitutionId AND u.UserId=s.UserId WHERE u.Login=? AND s.RevokedAt IS NULL",
            "owner@example.invalid",
        ).fetchone()
        identity, contact = c.execute(
            "SELECT IdentityId,ContactId FROM crm_channels2.ExternalIdentity WHERE InstitutionId=? AND ConversationId=?",
            institution, thread,
        ).fetchone()
        c.execute(
            "INSERT crm_inbox.Agent(AgentId,Name,Description,Enabled) VALUES(?,'Agente sintético','',0)",
            agent,
        )
        c.execute(
            "INSERT crm_agents.Profile(AgentId,Level,Version,Document) VALUES(?,'guide',1,'{}')",
            agent,
        )
        c.execute(
            "INSERT crm_agents5.Request(InstitutionId,RequestId,AgentId,ActorId,SessionId,Kind,State,PayloadHash,LeaseId,LeaseUntil)"
            " VALUES(?,?,?,?,?,'simulation','running',?,?,DATEADD(second,-1,SYSUTCDATETIME()))",
            institution, request, agent, actor, session, bytes(32), str(uuid4()),
        )
        c.execute(
            "INSERT crm_campaign8.Record(InstitutionId,RecordId,Kind,State,Name,Document,CurrentVersion,Epoch,Revision)"
            " VALUES(?,?,'flow','paused','Flujo sintético','{}',1,1,1)", institution, flow,
        )
        c.execute(
            "INSERT crm_campaign8.Version(InstitutionId,RecordId,VersionNo,Kind,Name,Document,Reason,ActorId,OperationId)"
            " VALUES(?,?,1,'flow','Flujo sintético','{}','fixture',?,?)", institution, flow, actor, str(uuid4()),
        )
        c.execute(
            "INSERT crm_campaign8.Enrollment(InstitutionId,EnrollmentId,FlowId,VersionNo,FlowEpoch,"
            "IdentityId,ContactId,CanonicalContactId,ConversationId,EntryKey,Variant,State,Context,StepIndex,DueAt)"
            " VALUES(?,?,?,1,1,?,?,?,?,?,'A','waiting','{}',0,SYSUTCDATETIME())",
            institution, enrollment, flow, identity, contact, contact, thread, "e" * 64,
        )
    return request, enrollment


def recovery_states(settings, request, enrollment):
    with transaction(settings, anonymous=True) as c:
        agent = c.execute("SELECT State,ErrorCode FROM crm_agents5.Request WHERE RequestId=?", request).fetchone()
        campaign = c.execute("SELECT State,LastReason FROM crm_campaign8.Enrollment WHERE EnrollmentId=?", enrollment).fetchone()
        return agent, campaign


def wait_for(call, predicate):
    deadline = time.monotonic() + 24
    while time.monotonic() < deadline:
        result = call()
        if predicate(result):
            return result
        time.sleep(0.25)
    raise AssertionError("worker_wait_timeout")


def verify_coolify_start(config, password):
    entrypoint = subprocess.Popen(
        ["/bin/bash", "/app/coolify-start.sh"],
        env={**os.environ, **config},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(base_url="http://127.0.0.1:4178", trust_env=False, headers=LOCAL, timeout=4) as api:
            def readiness():
                if entrypoint.poll() is not None:
                    raise AssertionError("coolify_entrypoint_exited")
                try:
                    return api.get("/health/ready").status_code
                except httpx.ConnectError:
                    return 0

            wait_for(readiness, lambda code: code == 200)
            login = checked(api.post(AUTH + "/login", json={"email": "owner@example.invalid", "password": password}))
            assert checked(api.get(AUTH + "/me"))["user"]["role"] == "owner"
            assert checked(api.get(WORKSPACE + "/clients"))["total"] == 1
            checked(api.post(AUTH + "/logout", headers={"X-CSRF-Token": login["csrf_token"]}))
    finally:
        entrypoint.terminate()
        entrypoint.wait(timeout=20)


def run():
    admin = os.environ["PG_FIXTURE_ADMIN_DSN"]
    target = urlsplit(admin)
    if target.hostname != "pg-fixture" or target.path != "/" + DATABASE or target.username != "postgres":
        raise RuntimeError("Use the dedicated PostgreSQL fixture container")
    source_sha256 = os.environ.get("PG_FIXTURE_SOURCE_SHA256")
    runtime_password = secrets.token_urlsafe(30)
    seed_catalog(admin, runtime_password, source_sha256)
    institution = str(uuid4())
    password = secrets.token_urlsafe(30)
    stage, config_digest = seed_institution(admin, institution, password)
    dsn = urlunsplit(("postgresql", "pg-fixture:5432", target.path, "", ""))
    config = {
        "CRM_POSTGRES_URL": dsn, "CRM_POSTGRES_SNAPSHOT_SHA256": source_sha256 or DIGEST,
        "CRM_POSTGRES_USER": FIXTURE_ROLE, "CRM_POSTGRES_PASSWORD": runtime_password,
        "CRM_SECURITY_KEY": base64.b64encode(secrets.token_bytes(32)).decode(),
    }
    settings = load(config)
    endpoint, verify, signature = seed_channel(settings, stage, config_digest)
    sent = []

    def transport(adapter, payload, *, media=None, before_send=None):
        assert adapter["channel"] == "whatsapp" and payload["target"] == PHONE
        assert media is None
        if before_send is not None:
            before_send()
        sent.append(payload["body"])
        if payload["body"] == "incierto":
            raise ProviderFailure("fixture_uncertain", uncertain=True)
        return "fixture_sent_1"

    def downloader(adapter, reference, target):
        assert adapter["channel"] == "whatsapp" and reference["id"] == "fixture_image_1"
        Image.new("RGB", (2, 2), "white").save(target, "PNG")

    with tempfile.TemporaryDirectory(prefix="rinova-pg-media-") as media:
        os.environ["CRM_AI_STATE_DIR"] = media
        app = create_app(settings, channel_transport=transport, media_downloader=downloader)
        with TestClient(
            app, base_url="http://127.0.0.1:4178", client=("127.0.0.1", 40000),
            headers=LOCAL, raise_server_exceptions=False,
        ) as api:
            def post(path, **kwargs):
                return api.post(path, **kwargs)

            checked(api.get(WORKSPACE + "/clients"), 401)
            checked(post(AUTH + "/login", json={"email": "owner@example.invalid", "password": "incorrecta"}), 401)
            login = checked(post(AUTH + "/login", json={"email": "owner@example.invalid", "password": password}))
            csrf = {"X-CSRF-Token": login["csrf_token"]}
            assert checked(api.get(AUTH + "/me"))["user"]["role"] == "owner"
            sections = (
                "runtime", "settings/modules", "users", "roles", "sessions", "campaigns", "broadcasts",
                "knowledge", "memory", "ads/accounts", "learning/packs",
            )
            observed = {section: api.get(PREFIX + "/" + section).status_code for section in sections}
            assert all(status == 200 for status in observed.values()), observed
            checked(api.get("/api/v1/agents/selection"))
            checked(api.put(PREFIX + "/campaigns/" + str(uuid4()), headers=csrf, json={}), 404)
            wait_for(lambda: api.get("/health/ready").status_code, lambda code: code == 200)

            hooks = "/hooks/channels/" + endpoint
            handshake = api.get(hooks, params={"hub.mode": "subscribe", "hub.verify_token": verify, "hub.challenge": "fixture"})
            assert handshake.status_code == 200 and handshake.text == "fixture"

            def deliver(value):
                payload = {"entry": [{"changes": [{"field": "messages", "value": {
                    "messaging_product": "whatsapp", "metadata": {"phone_number_id": "7733"}, **value,
                }}]}]}
                raw = json.dumps(payload).encode()
                digest = "sha256=" + hmac.digest(signature.encode(), raw, "sha256").hex()
                checked(post(hooks, content=raw, headers={"x-hub-signature-256": "sha256=wrong"}), 403)
                headers = {"x-hub-signature-256": digest}
                assert checked(post(hooks, content=raw, headers=headers))["duplicate"] is False
                assert checked(post(hooks, content=raw, headers=headers))["duplicate"] is True

            deliver({"messages": [{"id": "fixture_received_1", "from": PHONE, "timestamp": str(int(time.time())),
                                   "type": "text", "text": {"body": "Hola ensayo"}}]})
            inbox = wait_for(
                lambda: checked(api.get(WORKSPACE + "/inbox")),
                lambda data: data["total"] == 1,
            )
            thread = inbox["items"][0]["conversationId"]
            assert checked(api.get(WORKSPACE + "/clients", params={"q": PHONE}))["total"] == 1
            empty_page = checked(api.get(WORKSPACE + "/inbox", params={"offset": 30, "anchor": inbox["revision"]}))
            assert empty_page["items"] == [] and empty_page["total"] == 1
            path = WORKSPACE + "/conversations/" + thread + "/messages"
            assert [item["body"] for item in checked(api.get(path))["items"]] == ["Hola ensayo"]

            def reply(text):
                current = checked(api.get(path))
                body = {"operationId": str(uuid4()), "revision": current["revision"], "body": text}
                checked(post(path, json=body), 403)
                result = checked(post(path, json=body, headers=csrf))
                assert checked(post(path, json=body, headers=csrf)) == result

            def queue(state):
                return checked(api.get(PREFIX + "/operations"))["queues"]["outbound"].get(state, 0)

            reply("respuesta")
            wait_for(lambda: queue("accepted"), lambda count: count == 1)
            deliver({"statuses": [{"id": "fixture_delayed_binding", "status": "delivered"}]})
            wait_for(
                lambda: checked(api.get(PREFIX + "/operations"))["queues"]["webhook_events"].get("quarantined"),
                lambda count: count == 1,
            )
            with transaction(settings, True, anonymous=True) as c:
                c.execute(
                    "UPDATE crm_channels2.SendJob SET ExternalId=? WHERE ExternalId=? AND State='accepted'",
                    "fixture_delayed_binding", "fixture_sent_1",
                )
                assert c.rowcount == 1
            wait_for(lambda: queue("delivered"), lambda count: count == 1)
            reply("incierto")
            wait_for(lambda: queue("uncertain"), lambda count: count == 1)
            assert sent == ["respuesta", "incierto"]
            assert [item["body"] for item in checked(api.get(path))["items"]] == [
                "Hola ensayo", "respuesta", "incierto",
            ]
            deliver({"messages": [{"id": "fixture_received_media", "from": PHONE, "timestamp": str(int(time.time())),
                                   "type": "image", "image": {"id": "fixture_image_1", "mime_type": "image/png"}}]})
            operations = wait_for(
                lambda: checked(api.get(PREFIX + "/operations")),
                lambda state: state["queues"]["media"].get("ready") == 1,
            )
            assert operations["sql"]["tables"] == 155 and operations["workers"]["ready"]
            assert {entry["stage"] for entry in operations["workers"]["stages"]} == {
                "events", "projection", "media", "campaigns", "broadcasts", "dispatch", "maintenance", "agents",
            }
            [attachment] = (Path(media) / "inbox-media").glob("*.bin")
            with Image.open(attachment) as image:
                assert image.size == (2, 2)
            response = api.get(PREFIX + "/media/" + attachment.stem)
            assert response.status_code == 200 and response.content == attachment.read_bytes()
            request, enrollment = seed_worker_recovery(settings, thread)
            wait_for(
                lambda: recovery_states(settings, request, enrollment),
                lambda result: result == (
                    ("uncertain", "agents_request_lease_expired"),
                    ("cancelled", "campaign_version_or_pause_changed"),
                ),
            )
            checked(post(AUTH + "/logout", headers=csrf))
            checked(api.get(WORKSPACE + "/clients"), 401)
            checked(post(AUTH + "/login", json={"email": "agent@example.invalid", "password": password}))
            checked(api.get(WORKSPACE + "/clients"), 403)
            checked(api.get(PREFIX + "/operations"), 403)
        if source_sha256:
            verify_coolify_start(config, password)
    print(json.dumps({"postgres_backend_flows": "verified", "queue_states": ["accepted", "delivered", "uncertain"],
                      "incoming_media": "verified", "worker_stages": 8,
                      "recovery": ["broadcast_delayed_receipt", "campaign_paused", "agent_lease_expired"],
                      "coolify_entrypoint": "verified" if source_sha256 else "skipped"}))


if __name__ == "__main__":
    run()
