"""Owned P9 fixture support; never imported at product startup."""

from pathlib import Path

from app.institutional.api import create_app
from app.institutional.spanish import load
from tools.p7_test_support import Gateway
from tools.p7_test_support import Harness as Parent
from tools.prepare_p9_ads import WORK, read
from tools.qualify_p3_workspace import Browser


class Harness(Parent):
    def __init__(self, label="fixture-v2"):
        self.label = label
        self.settings = load(Path(read(WORK / (label + "-profile.json"))["directory"]))
        assert self.settings.connection["database"].startswith("CBN_P9ES_TRIAL_")
        self.gateway = Gateway()
        self.app = create_app(self.settings, broadcast_gateway=self.gateway)
        self.b = Browser(self.app)
        self.access = read(WORK / (label + "-access.json"))
        self.b.login(self.access["email"], self.access["password"])
