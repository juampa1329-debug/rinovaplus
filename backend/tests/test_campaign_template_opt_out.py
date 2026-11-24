from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.institutional import campaign_runtime as runtime


@pytest.mark.parametrize("text,declined", [
    ("No recibir mensajes", True), ("NO RECIBIR MENSAJES!", True),
    ("stop", True), ("Prefiero dejar el seguimiento en pausa", True), ("Pausa", True),
    ("No quiero pausar el seguimiento", False), ("Ver plan de pagos", False), ("Conocer el programa", False),
])
def test_authenticated_template_reply_records_scoped_opt_out(
    monkeypatch, text, declined,
):
    identity, incoming, contact = [str(uuid4()) for _ in range(3)]
    p = {
        "Stage": "Seguimiento", "ProgramId": None, "IncomingCount": 1,
        "CanonicalContactId": contact, "LastIncomingId": incoming,
        "IncomingText": text,
    }
    old = {**p, "Revision": 1, "IncomingCount": 0}
    captured = []
    monkeypatch.setattr(runtime, "person", lambda *args: p)
    monkeypatch.setattr(runtime, "snapshot", lambda *args: {})
    monkeypatch.setattr(runtime, "one", lambda *args: old)
    monkeypatch.setattr(runtime, "institution", lambda *args: "institution")
    monkeypatch.setattr(runtime, "event", lambda c, s, kind, doc, **kw:
                        captured.append((kind, doc)))
    c = SimpleNamespace(execute=lambda *args: None)
    runtime.observe_identity(
        c, None, identity, incoming=True, incoming_text=text, incoming_id=incoming,
    )
    events = [doc for kind, doc in captured if kind == "opt_out"]
    assert bool(events) == declined
    if declined:
        assert events[0]["identity_id"] == identity
        assert events[0]["message_id"] == incoming
        assert events[0]["source"] == "authenticated_incoming"
