"""Contrato mínimo de saúde da fila de comunicação."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CommunicationQueueStatus:
    pending: int
    processing: int
    failed: int
    sent: int
    oldest_pending_at: datetime | None


class CommunicationQueueMonitor(Protocol):
    async def get_status(self) -> CommunicationQueueStatus: ...
