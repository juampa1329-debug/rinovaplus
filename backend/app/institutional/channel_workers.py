"""Only the P4 C10 event/outbound consumers run in this application."""

import logging
import threading
from contextlib import asynccontextmanager

from app.institutional.channel_events import EventWorker
from app.institutional.channel_outbox import Dispatcher

logger = logging.getLogger(__name__)


class Workers:
    def __init__(self, settings):
        self.settings = settings
        self.stop_event = threading.Event()
        self.thread = None
        from app.institutional.operations import Pulse

        self.pulse = Pulse()

    def start(self):
        if self.thread is not None:
            raise RuntimeError("channel_workers_already_started")
        self.thread = threading.Thread(
            target=self.run, name="cbn-c10-channels", daemon=True
        )
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=45)

    def run(self):
        from app.institutional.channel_media import MediaWorker
        from app.institutional.channel_recovery import maintenance

        events, dispatcher = EventWorker(self.settings), Dispatcher(self.settings)
        media = MediaWorker(self.settings)
        failures = 0
        while not self.stop_event.is_set():
            try:
                self.pulse.observe("events", events.once)
                self.pulse.observe("projection", events.project_once)
                self.pulse.observe("media", media.once)
                if (
                    self.settings.ticket.get("version") in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-campaign-p8-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}
                ):
                    from app.institutional.campaign_runtime import Worker as FlowWorker

                    try:
                        def run_flow():
                            flow = FlowWorker(self.settings)
                            flow.refresh()
                            flow.once()

                        self.pulse.observe("campaigns", run_flow)
                    except Exception:
                        logger.warning("campaign_worker_retry_required")
                if self.settings.ticket.get("version") in {
                    "cbn-institutional-broadcast-p7-v1",
                    "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
                    from app.institutional.broadcast_dispatch import (
                        Worker,
                        reconcile_receipts,
                    )
                    from app.institutional.store import transaction

                    def run_broadcast():
                        with transaction(self.settings, True, anonymous=True) as c:
                            reconcile_receipts(c, self.settings)
                        Worker(self.settings).once()

                    self.pulse.observe("broadcasts", run_broadcast)
                self.pulse.observe("dispatch", dispatcher.once)
                self.pulse.observe("maintenance", lambda: maintenance(self.settings))
                if self.settings.ticket.get("version") in {
                    "cbn-institutional-agents-p5-v1",
                    "cbn-institutional-knowledge-p6-v1",
                    "cbn-institutional-broadcast-p7-v1",
                    "cbn-institutional-campaign-p8-v1", 'cbn-institutional-ads-p9-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'}:
                    from app.institutional.agents import expire_requests
                    from app.institutional.store import transaction

                    def expire():
                        with transaction(self.settings, True, anonymous=True) as c:
                            expire_requests(c)

                    self.pulse.observe("agents", expire)
                failures = 0
            except Exception:
                failures += 1
                if failures in {1, 5, 20}:
                    # Provider bodies, URLs, query strings and SQL credentials stay out
                    # of logs.
                    logger.warning("channel_worker_retry_required")
            self.stop_event.wait(min(30, 3 + failures * 2))


def lifespan(settings):
    @asynccontextmanager
    async def running(app):
        workers = Workers(settings)
        app.state.channel_workers = workers
        workers.start()
        try:
            yield
        finally:
            workers.stop()

    return running
