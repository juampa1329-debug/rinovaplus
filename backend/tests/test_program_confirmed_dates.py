import hashlib
from unittest.mock import Mock

import pytest

from app.institutional import postgres_dialect
from app.institutional import grounded_replies
from app.modules.agents.skill_policy import for_turn, project_facts


@pytest.mark.parametrize("question", [
    "¿Cuánto cuesta PRE-ICFES y cuándo inician las clases?",
    "Me parece caro. ¿El 13 de febrero de qué año es?",
    "¿Hasta qué fecha aplica el descuento y cuándo empieza?",
])
def test_financial_turn_keeps_reviewed_class_year_and_independent_cash_deadline(question):
    facts = {"presentation": "Inicio confirmado: 13 de febrero de 2027.",
             "price_cop": 800000, "price_concept": "Regular 1600000, descuento 50 %",
             "price_valid_until": "2026-12-16", "financial_plans": [{"valid_until": "2026-12-15"}]}
    projected = project_facts({"commercial": facts}, for_turn(question))["commercial"]
    assert projected == facts
    assert "prevalecen sobre respuestas antiguas" in grounded_replies.RULES
    assert "no vuelve desconocida la fecha de inicio de clases" in grounded_replies.RULES


def test_statement_timing_does_not_record_sql_parameters_or_exception_body(monkeypatch):
    times = iter([0, 1.5])
    monkeypatch.setattr(postgres_dialect, "monotonic", lambda: next(times))
    raw = Mock()
    raw.execute.side_effect = RuntimeError("PRIVATE exception")
    cursor = postgres_dialect.Cursor(raw, {}, {})
    sql = "SELECT secret FROM example WHERE name=%s"
    with pytest.raises(RuntimeError):
        cursor.native(sql, "PRIVATE credential")
    elapsed, fingerprint, source = cursor.slowest
    assert elapsed == 1500 and fingerprint == hashlib.sha256(sql.encode()).hexdigest()[:12]
    assert "test_statement_timing" in source
    assert "PRIVATE" not in str(cursor.slowest) and "secret" not in str(cursor.slowest)
