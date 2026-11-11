"""One bounded local worker: SQL evaluation/preparation only, no network sending."""

import threading


class CampaignWorker:
    def __init__(self, service):
        self.service = service
        self.halt = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run, name="campaign-evaluation", daemon=True)
        self.thread.start()

    def stop(self):
        self.halt.set()
        if self.thread:
            self.thread.join(timeout=3)

    def run(self):
        while not self.halt.is_set():
            try:
                worked = self.service.process_one()
            except Exception:
                worked = False
            self.halt.wait(1 if worked else 5)
