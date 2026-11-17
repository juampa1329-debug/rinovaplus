"""Only the P4 C10 event/outbound consumers run in this application."""

import logging
import threading
from contextlib import asynccontextmanager

from app.institutional.channel_events import EventWorker
from app.institutional.channel_outbox import Dispatcher

logger = logging.getLogger(__name__)


class Workers:
    def __init__(self, settings, *, transport=None, media_downloader=None):
        self.settings = settings
        self.stop_event = threading.Event()
        self.ingress_wake = threading.Event()
        self.dispatch_wake = threading.Event()
        self.fast_queues = bool(
            getattr(settings, "postgres_deployment", False)
            or getattr(settings, "public_origin", None)
        )
        self.queue_threads = ()
        self.thread = None
        self.gemini_thread = None
        from app.institutional.operations import Pulse

        if getattr(settings, "postgres_profile", False) and not getattr(settings, "postgres_deployment", False):
            from app.institutional.postgres_rehearsal import WORKER_STAGES, network_disabled

            self.transport = transport or network_disabled
            self.media_downloader = media_downloader or network_disabled
            self.pulse = Pulse(stages=WORKER_STAGES)
        else:
            self.transport = transport
            self.media_downloader = media_downloader
            self.pulse = Pulse()

    def start(self):
        if self.thread is not None:
            raise RuntimeError("channel_workers_already_started")
        self.thread = threading.Thread(
            target=self.run, name="cbn-c10-channels", daemon=True
        )
        self.thread.start()
        if self.fast_queues:
            self.queue_threads = (
                threading.Thread(target=self.run_ingress, name="rinova-c10-ingress", daemon=True),
                threading.Thread(target=self.run_dispatch, name="rinova-c10-dispatch", daemon=True),
            )
            for thread in self.queue_threads:
                thread.start()
        from app.institutional.comment_automation import available
        from app.institutional.whatsapp_gemini import configured_account

        if configured_account(self.settings) or available(self.settings):
            self.gemini_thread = threading.Thread(
                target=self.run_gemini, name="rinova-whatsapp-gemini", daemon=True
            )
            self.gemini_thread.start()

    def stop(self):
        self.stop_event.set()
        self.ingress_wake.set()
        self.dispatch_wake.set()
        if self.thread:
            self.thread.join(timeout=45)
        if self.gemini_thread:
            self.gemini_thread.join(timeout=45)
        for thread in self.queue_threads:
            thread.join(timeout=45)

    def run_queue(self, wake, consume):
        while not self.stop_event.is_set():
            wake.clear()
            try:
                if consume():
                    continue
                delay = 3
            except Exception:
                logger.warning("channel_queue_worker_retry_required")
                delay = 5
            wake.wait(delay)

    def run_ingress(self):
        events = EventWorker(self.settings)

        def consume():
            accepted = self.pulse.observe("events", events.once)
            projected = self.pulse.observe("projection", events.project_once)
            return accepted or projected

        self.run_queue(self.ingress_wake, consume)

    def run_dispatch(self):
        dispatcher = Dispatcher(self.settings, self.transport)
        self.run_queue(self.dispatch_wake, lambda: self.pulse.observe("dispatch", dispatcher.once))

    def run_gemini(self):
        from app.institutional.comment_automation import Worker as CommentWorker
        from app.institutional.whatsapp_gemini import Worker

        workers = (Worker(self.settings), CommentWorker(self.settings))
        while not self.stop_event.is_set():
            delay = 3
            for worker in workers:
                try:
                    if worker.once():
                        self.dispatch_wake.set()
                except Exception:
                    logger.warning("channel_gemini_worker_retry_required")
                    delay = 10
            self.stop_event.wait(delay)

    def run(self):
        from app.institutional.channel_media import MediaWorker
        from app.institutional.channel_recovery import maintenance

        events = EventWorker(self.settings)
        dispatcher = Dispatcher(self.settings, self.transport)
        media = MediaWorker(self.settings, self.media_downloader)
        failures = 0
        while not self.stop_event.is_set():
            try:
                if not self.fast_queues:
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
                if not self.fast_queues:
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


def lifespan(settings, *, transport=None, media_downloader=None):
    @asynccontextmanager
    async def running(app):
        workers = Workers(settings, transport=transport, media_downloader=media_downloader)
        app.state.channel_workers = workers
        workers.start()
        try:
            yield
        finally:
            workers.stop()

    return running
