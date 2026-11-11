"""Controlled P11 fixture; never the populated main preview or an older copy."""

from pathlib import Path

from app.institutional.api import create_app
from app.institutional.operations_policy import VERSION
from app.institutional.spanish import load
from tools.p7_test_support import Gateway
from tools.p7_test_support import Harness as Parent
from tools.prepare_p11_operations import WORK, read
from tools.qualify_p3_workspace import Browser


class Harness(Parent):
    def __init__(self, label="fixture"):
        self.label = label
        self.settings = load(Path(read(WORK / (label + "-profile.json"))["directory"]))
        assert self.settings.ticket["version"] == VERSION and label != "final"
        self.gateway = Gateway()
        self.app = create_app(self.settings, broadcast_gateway=self.gateway)
        self.b = Browser(self.app)
        self.access = read(WORK / (label + "-access.json"))
        self.b.login(self.access["email"], self.access["password"])
