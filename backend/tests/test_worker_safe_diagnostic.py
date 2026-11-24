import logging
from types import SimpleNamespace

from app.institutional.channel_workers import Workers


def test_queue_failure_logs_only_class_and_sqlstate_without_exception_body(caplog):
    worker = Workers.__new__(Workers)
    stopped = [False]
    worker.stop_event = SimpleNamespace(is_set=lambda: stopped[0])
    wake = SimpleNamespace(clear=lambda: None, wait=lambda _: None)
    class DatabaseFault(Exception):
        pgcode = "42703"
    def consume():
        stopped[0] = True
        raise DatabaseFault("private contact and secret must not be logged")
    with caplog.at_level(logging.WARNING):
        worker.run_queue(wake, consume)
    assert "type=DatabaseFault sqlstate=42703" in caplog.text
    assert "private contact" not in caplog.text and "secret" not in caplog.text
