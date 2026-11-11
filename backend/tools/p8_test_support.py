"""Controlled P8 native-copy support; never imported by application startup."""

from pathlib import Path
from uuid import uuid4
from app.institutional.api import create_app
from app.institutional.spanish import load
from tools.p7_test_support import Harness as P7, Gateway
from tools.prepare_p8_campaign import WORK, read
from tools.qualify_p3_workspace import Browser


class Harness(P7):
    def __init__(self, label="fixture"):
        self.label = label
        self.settings = load(Path(read(WORK / (label + "-profile.json"))["directory"]))
        assert self.settings.connection["database"].startswith("CBN_P8ES_TRIAL_")
        self.gateway = Gateway()
        self.app = create_app(self.settings, broadcast_gateway=self.gateway)
        self.b = Browser(self.app)
        self.access = read(WORK / (label + "-access.json"))
        self.b.login(self.access["email"], self.access["password"])

    def save8(self, kind, doc, name=None, id=None, revision=0):
        id = id or str(uuid4())
        return self.call(
            "campaigns/" + id,
            "PUT",
            self.cmd(revision, kind=kind, name=name or "Prueba " + kind, document=doc),
        )

    def act8(self, id, action, expected=200, **changes):
        current = self.call("campaigns/" + id)
        if action == "activate" and "preflight_id" not in changes:
            pre = self.call(
                "campaigns/" + id + "/preflight", "POST", self.cmd(current["revision"])
            )
            if expected == 200:
                assert pre["valid"], pre
            changes["preflight_id"] = pre["id"]
        return self.call(
            "campaigns/" + id + "/" + action,
            "POST",
            self.cmd(current["revision"], confirmed=True, **changes),
            expected,
        )

    def template8(self, channel="whatsapp", **extra):
        v = self.save8(
            "template",
            (
                dict(
                    channel=channel,
                    body="Hola {{nombre}}, consulta admisiones.",
                    variables={"nombre": {"source": "customer_first_name"}},
                )
                | extra
            ),
        )
        self.act8(v["id"], "activate")
        return self.call("campaigns/" + v["id"])

    def flow8(self, integration, template=None, *, kind="flow", **extra):
        if template is None:
            template = self.template8()
        doc = (
            dict(
                integration_id=integration,
                steps=[
                    dict(
                        kind="send",
                        crm_template_id=template["id"],
                        crm_template_version=template["version"],
                    )
                ],
            )
            | extra
        )
        v = self.save8(kind, doc)
        self.act8(v["id"], "activate")
        return self.call("campaigns/" + v["id"])

    def enroll8(self, flow, person):
        result = self.act8(flow["id"], "enroll", identity_ids=[person["id"]])["items"][
            0
        ]
        assert result["enrolled"], result
        return result["id"]

    def cadence8(self, integration):
        current = self.call("broadcasts/accounts/" + integration + "/cadence")
        self.call(
            "broadcasts/accounts/" + integration + "/cadence",
            "PUT",
            self.cmd(
                current["revision"], enabled=True, daily_limit=1000, interval_seconds=1
            ),
        )

    def release8(self, integration):
        self.sql(
            "UPDATE crm_broadcast7.Cadence SET NextAt=DATEADD(second,-1,SYSUTCDATETIME()) WHERE IntegrationId=?",
            integration,
            write=True,
        )

    def run8(self, id):
        row = self.sql(
            "SELECT State,StepIndex,DueAt,LastReason FROM crm_campaign8.Enrollment WHERE EnrollmentId=?",
            id,
        )[0]
        return dict(state=row[0], step=row[1], due=row[2], reason=row[3])
