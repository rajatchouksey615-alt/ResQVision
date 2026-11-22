"""Outbox delivery worker; a failed request leaves its event available for recovery."""

import logging

from .client import BackendEventClient
from .errors import BackendSubmissionError
from .outbox import SQLiteEventOutbox

logger = logging.getLogger(__name__)


class EventPublisher:
    def __init__(self, outbox: SQLiteEventOutbox, client: BackendEventClient) -> None:
        self.outbox = outbox
        self.client = client

    def publish_pending(self, *, limit: int = 100) -> tuple[int, int]:
        delivered = 0
        failed = 0
        for payload in self.outbox.pending(limit=limit):
            try:
                self.client.submit(payload)
            except BackendSubmissionError as exc:
                self.outbox.record_failure(payload, type(exc).__name__)
                failed += 1
                logger.error(
                    "AI event remains in the local outbox",
                    extra={"event_id": payload.external_event_id, "error_code": type(exc).__name__},
                )
                continue
            self.outbox.mark_delivered(payload)
            delivered += 1
        return delivered, failed
