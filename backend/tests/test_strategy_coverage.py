"""A matching fingerprint is insufficient when receipts omit a SQL message."""

import json
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.modules.conversation_analysis.domain.models import PROMPT_VERSION
from app.modules.conversation_analysis.api.router import STATE_SELECT
from app.modules.conversation_strategy.api.router import PLAN_SELECT, ConversationStrategy


@pytest.mark.parametrize(
    "covered,total,pending,eligible",
    [(1, 2, 0, False), (1, 1, 1, False), (1, 1, 0, True)],
)
def test_even_current_matching_plan_requires_complete_sql_coverage(
    monkeypatch, covered, total, pending, eligible
):
    class Cursor:
        def execute(self, sql, *args):
            if sql == PLAN_SELECT:
                self.data = [
                    {
                        "id": str(uuid4()),
                        "generation": 1,
                        "binding": "binding",
                        "semanticFingerprint": "semantic",
                        "promptVersion": PROMPT_VERSION,
                        "documentJson": json.dumps({"followupSupported": True}),
                    }
                ]
            elif sql == STATE_SELECT:
                self.data = [
                    {
                        "generation": 1,
                        "contextGeneration": 1,
                        "status": "current",
                        "fingerprint": "fingerprint",
                    }
                ]
            else:
                self.data = []
            return self

        def fetchone(self):
            return self.row

        def fetchval(self):
            return None

    cursor = Cursor()
    execute = cursor.execute

    def dispatch(sql, *args):
        cursor.row = (
            ("ai", "open")
            if "SELECT ControlMode" in sql
            else (None, 1, 1)
            if "SELECT a.HumanEmployeeId" in sql
            else (str(uuid4()),)
        )
        return execute(sql, *args)

    cursor.execute = dispatch
    monkeypatch.setattr("app.modules.conversation_strategy.api.router.rows", lambda c: c.data)
    monkeypatch.setattr(
        "app.modules.conversation_strategy.api.router.ConversationAnalysis.policy",
        lambda c: {"enabled": True},
    )
    monkeypatch.setattr(
        "app.modules.conversation_strategy.api.router.ConversationAnalysis.coverage",
        lambda *args: {
            "coveredMessages": covered,
            "totalMessages": total,
            "pendingReferences": pending,
        },
    )
    monkeypatch.setattr(
        "app.modules.conversation_strategy.api.router.ConversationAnalysis.fingerprint",
        lambda *args: "fingerprint",
    )
    monkeypatch.setattr(
        "app.modules.conversation_strategy.api.router.semantic_fingerprint", lambda *args: "semantic"
    )
    monkeypatch.setattr("app.modules.conversation_strategy.api.router.no_contact", lambda *args: False)
    monkeypatch.setattr("app.modules.contacts.application.merge.historical_ids", lambda c, key: {key})
    monkeypatch.setattr("app.modules.contacts.application.merge.analysis_guard", lambda *args: None)
    service = ConversationStrategy(Mock())
    service.policy = lambda c, key: key != "global"
    _, _, _, _, status = service.inspect(cursor, str(uuid4()), "binding")
    assert status["planCurrent"] is eligible
    assert status["effective"] is eligible
