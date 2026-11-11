"""Controlled P7 fixture only. Never used by application startup or main preview."""

import hashlib
import hmac
import json
import time
from pathlib import Path
from uuid import uuid4

from app.institutional.api import create_app
from app.institutional.channel_events import EventWorker
from app.institutional.spanish import load
from app.institutional.spanish_bindings import Cursor
from app.modules.channels import providers
from tools.prepare_p7_broadcast import WORK, admin, read
from tools.qualify_p3_workspace import Browser


class Gateway:
    def __init__(self):
        self.gets = []
        self.posts = []
        self.fail = None
        self.before_get = None
        self.before_post = None
        self.next_external = None
        self.components = [
            {"type": "HEADER", "format": "TEXT", "text": "Institución {{1}}"},
            {"type": "BODY", "text": "Hola {{1}}, información de {{2}}."},
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL",
                        "text": "Ver información",
                        "url": "https://cbn.example/info/{{1}}",
                    }
                ],
            },
        ]
        self.status = "APPROVED"

    def __call__(self, adapter, method, path, body=None, params=None, **_):
        if method == "GET":
            self.gets.append(path)
            if self.before_get:
                action = self.before_get
                self.before_get = None
                action()
            if self.fail == "get":
                raise providers.ProviderFailure("invalid_access_token")
            return {
                "data": [
                    {
                        "id": "777001",
                        "name": "admisiones_controladas",
                        "language": "es",
                        "category": "MARKETING",
                        "status": self.status,
                        "components": self.components,
                        "quality_score": "GREEN",
                    }
                ]
            }
        self.posts.append({"path": path, "body": body})
        if self.before_post:
            action = self.before_post
            self.before_post = None
            action()
        if self.fail == "timeout":
            raise providers.ProviderFailure("provider_timeout", uncertain=True)
        if self.fail == "definitive":
            raise providers.ProviderFailure("provider_rejected")
        if path.endswith("/message_templates"):
            return {"id": "888001", "status": "PENDING"}
        external = self.next_external or "wamid.controlled." + uuid4().hex
        self.next_external = None
        return {"messages": [{"id": external}]}


class Harness:
    def __init__(self, label="fixture"):
        self.label = label
        self.settings = load(Path(read(WORK / (label + "-profile.json"))["directory"]))
        assert self.settings.connection["database"].startswith("CBN_P7ES_TRIAL_")
        self.gateway = Gateway()
        self.app = create_app(self.settings, broadcast_gateway=self.gateway)
        self.b = Browser(self.app)
        self.access = read(WORK / (label + "-access.json"))
        self.b.login(self.access["email"], self.access["password"])

    def call(self, path, method="GET", body=None, expected=200):
        return self.b.request(path, method, body, expected).json()

    def cmd(self, revision=0, **extra):
        return dict(
            operation_id=str(uuid4()),
            revision=revision,
            reason="Prueba controlada P7",
            **extra,
        )

    def sql(self, text, *params, write=False):
        with admin(self.settings.connection["database"], readonly=not write) as db:
            c = Cursor(db.cursor(), self.settings.ticket["table_map"])
            c.execute(text, *params)
            return c.fetchall() if c.description else c.rowcount

    def account(self, suffix="1"):
        created = self.call(
            "channels",
            "POST",
            {
                "operation_id": str(uuid4()),
                "channel": "whatsapp",
                "display_name": "Cuenta controlada P7 " + suffix,
                "issuer_profile": "meta_whatsapp",
                "client_id": "270700" + suffix,
                "api_version": "v24.0",
            },
        )
        key = created["id"]
        item = next(v for v in self.call("channels")["items"] if v["id"] == key)
        for owner, kind, value in [
            (
                "application:" + item["application_id"],
                "app_secret",
                "controlled-app-" + uuid4().hex,
            ),
            ("integration:" + key, "access_token", "controlled-access-" + uuid4().hex),
        ]:
            self.call(
                "credentials",
                "PUT",
                {
                    "operation_id": str(uuid4()),
                    "scope": "channel",
                    "owner": owner,
                    "kind": kind,
                    "value": value,
                },
            )
        from app.modules.crm_configuration.application.service import read_configuration

        with admin(self.settings.connection["database"]) as db:
            c = Cursor(db.cursor(), self.settings.ticket["table_map"])
            config, _ = read_configuration(c, foundation=True)
            stage = next(v.key for v in config.stages if v.active)
            c.execute(
                (
                    "UPDATE crm_channels2.Integration SET E"
                    "xternalAccountId=?,ParentExternalId=?,"
                    "RequestedStatus='connected',VerifiedSt"
                    "atus='verified',InitialStageKey=?,Init"
                    "ialStageConfigHash=? WHERE Integration"
                    "Id=?"
                ),
                "15557000" + suffix,
                "1777000" + suffix,
                stage,
                hashlib.sha256(config.model_dump_json().encode()).digest(),
                key,
            )
        runtime = self.call("channels/runtime")
        self.call(
            "channels/runtime",
            "PUT",
            {**runtime, "operation_id": str(uuid4()), "outbound_enabled": True},
        )
        budget = self.call("settings/budgets")
        self.call(
            "settings/budgets",
            "PUT",
            {
                "operation_id": str(uuid4()),
                "revision": budget["revision"],
                "document": dict(budget["document"], daily_messages=1000),
            },
        )
        item = next(v for v in self.call("channels")["items"] if v["id"] == key)
        self.call(
            "channels/" + key + "/webhook",
            "POST",
            {
                "operation_id": str(uuid4()),
                "row_version": item["webhook"]["row_version"],
                "active": True,
            },
        )
        return key

    def incoming(
        self,
        integration,
        phone,
        name="Aspirante controlado",
        body="Solicito información de admisiones",
        reply_to=None,
    ):
        item = next(v for v in self.call("channels")["items"] if v["id"] == integration)
        from app.institutional.channel_operations import account, app_secret_kind
        from app.institutional.channel_secrets import get
        from app.institutional.store import transaction

        with transaction(self.settings, anonymous=True) as c:
            account_item = account(c, self.settings, integration)
            secret, _ = get(
                c,
                self.settings,
                "application",
                item["application_id"],
                app_secret_kind(account_item),
            )
        raw = json.dumps(
            {
                "object": "whatsapp_business_account",
                "entry": [
                    {
                        "id": account_item["ParentExternalId"],
                        "changes": [
                            {
                                "field": "messages",
                                "value": {
                                    "messaging_product": "whatsapp",
                                    "metadata": {
                                        "phone_number_id": account_item[
                                            "ExternalAccountId"
                                        ]
                                    },
                                    "contacts": [
                                        {"wa_id": phone, "profile": {"name": name}}
                                    ],
                                    "messages": [
                                        {
                                            "id": "incoming.controlled." + uuid4().hex,
                                            "from": phone,
                                            "type": "text",
                                            "text": {"body": body},
                                            "timestamp": str(int(time.time())),
                                            **(
                                                {"context": {"id": reply_to}}
                                                if reply_to
                                                else {}
                                            ),
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                ],
            }
        ).encode()
        response = self.b.client.post(
            item["webhook"]["path"],
            content=raw,
            headers={
                "X-Hub-Signature-256": "sha256="
                + hmac.digest(secret.encode(), raw, "sha256").hex(),
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 200, response.status_code
        worker = EventWorker(self.settings)
        assert worker.once()
        assert worker.project_once()
        row = self.sql(
            (
                "SELECT IdentityId,ContactId,Conversati"
                "onId FROM crm_channels2.ExternalIdenti"
                "ty WHERE IntegrationId=? AND ExternalI"
                "d=?"
            ),
            integration,
            phone,
        )[0]
        self.sql(
            ("UPDATE crm.Conversation SET ControlMode='ai' WHERE ConversationId=?"),
            row[2],
            write=True,
        )
        self.sql(
            "UPDATE crm.Contact SET Name=? WHERE ContactId=?", name, row[1], write=True
        )
        return {
            "id": str(row[0]).lower(),
            "contact": str(row[1]).lower(),
            "conversation": str(row[2]).lower(),
            "phone": phone,
        }

    def sync(self, integration):
        return self.call(
            "broadcasts/accounts/" + integration + "/templates/sync", "POST", self.cmd()
        )

    def receipt(self, integration, external, status, phone):
        item = next(v for v in self.call("channels")["items"] if v["id"] == integration)
        from app.institutional.channel_operations import account, app_secret_kind
        from app.institutional.channel_secrets import get
        from app.institutional.store import transaction

        with transaction(self.settings, anonymous=True) as c:
            owned = account(c, self.settings, integration)
            secret, _ = get(
                c,
                self.settings,
                "application",
                item["application_id"],
                app_secret_kind(owned),
            )
        raw = json.dumps(
            {
                "object": "whatsapp_business_account",
                "entry": [
                    {
                        "id": owned["ParentExternalId"],
                        "changes": [
                            {
                                "field": "messages",
                                "value": {
                                    "messaging_product": "whatsapp",
                                    "metadata": {
                                        "phone_number_id": owned["ExternalAccountId"]
                                    },
                                    "statuses": [
                                        {
                                            "id": external,
                                            "status": status,
                                            "recipient_id": phone,
                                            "timestamp": str(int(time.time())),
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                ],
            }
        ).encode()
        response = self.b.client.post(
            item["webhook"]["path"],
            content=raw,
            headers={
                "X-Hub-Signature-256": "sha256="
                + hmac.digest(secret.encode(), raw, "sha256").hex(),
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 200
        worker = EventWorker(self.settings)
        worker.once()
        worker.project_once()

    def grant(self, integration, person, state="granted"):
        listing = self.call("broadcasts/accounts/" + integration + "/identities")[
            "items"
        ]
        row = next(v for v in listing if v["id"] == person["id"])
        version = row["consent"]["version"] if row["consent"] else 0
        return self.call(
            "broadcasts/accounts/" + integration + "/consent/" + person["id"],
            "PUT",
            self.cmd(
                version,
                state=state,
                evidence="Formulario sintético de consentimiento explícito",
                origin="Fixture local controlada",
                expires_at="2027-12-31T23:59:00Z" if state == "granted" else None,
                confirmed=True,
            ),
        )

    def campaign(self, integration, **changes):
        template = next(
            v
            for v in self.call("broadcasts/options")["templates"]
            if v["integration_id"] == integration
            and v["name"] == "admisiones_controladas"
        )
        key = str(uuid4())
        body = self.cmd(
            name="Admisiones controladas P7",
            integration_id=integration,
            template_id=template["id"],
            template_version=template["version"],
            filters={},
            variables={
                "body.1": {"source": "customer_first_name"},
                "body.2": {"source": "literal", "value": "admisiones"},
                "header.1": {"source": "literal", "value": "CBN"},
                "button.0.1": {"source": "literal", "value": "programas"},
            },
        )
        body.update(changes)
        self.call("broadcasts/" + key, "PUT", body)
        return key

    def action(self, key, action, expected=200, **extra):
        current = self.call("broadcasts/" + key)
        return self.call(
            "broadcasts/" + key + "/" + action,
            "POST",
            self.cmd(current["revision"], confirmed=True, **extra),
            expected,
        )
