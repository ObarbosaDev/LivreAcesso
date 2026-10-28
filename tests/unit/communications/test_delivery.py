"""Testes do processamento idempotente da outbox."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from backend.app.modules.communications.application.delivery import (
    PendingDelivery,
    ProcessPendingDeliveries,
)
from backend.app.modules.communications.domain.entities import (
    CommunicationChannel,
    OutboundMessage,
)
from backend.app.modules.communications.infrastructure.fake_provider import (
    FakeCommunicationProvider,
)

_DELIVERY_ID = UUID("00000000-0000-4000-8000-000000000001")
_KEY = UUID("00000000-0000-4000-8000-000000000002")
_NOW = datetime(2026, 10, 28, 12, tzinfo=UTC)


class StubRepository:
    def __init__(self, deliveries: tuple[PendingDelivery, ...]) -> None:
        self.deliveries = deliveries
        self.sent: list[tuple[UUID, str, datetime]] = []
        self.failed: list[tuple[UUID, str, datetime]] = []

    async def claim_pending(self, *, limit: int, now: datetime) -> tuple[PendingDelivery, ...]:
        return self.deliveries[:limit]

    async def mark_sent(self, delivery_id: UUID, external_id: str, sent_at: datetime) -> None:
        self.sent.append((delivery_id, external_id, sent_at))

    async def mark_failed(self, delivery_id: UUID, error_code: str, available_at: datetime) -> None:
        self.failed.append((delivery_id, error_code, available_at))


def pending() -> PendingDelivery:
    return PendingDelivery(
        delivery_id=_DELIVERY_ID,
        message=OutboundMessage(
            idempotency_key=_KEY,
            recipient="familia@example.com",
            channel=CommunicationChannel.EMAIL,
            subject="Atualização do instituto",
            body="Mensagem de teste.",
        ),
        attempts=0,
    )


@pytest.mark.anyio
async def test_processes_batch_and_marks_delivery_sent() -> None:
    repository = StubRepository((pending(),))
    processor = ProcessPendingDeliveries(repository, FakeCommunicationProvider())

    processed = await processor.execute(now=_NOW)

    assert processed == 1
    assert repository.sent == [(_DELIVERY_ID, f"fake-{_KEY}", _NOW)]
    assert repository.failed == []


class FailingProvider:
    async def send(self, message: OutboundMessage) -> str:
        raise RuntimeError("detalhe externo que não deve ser persistido")


@pytest.mark.anyio
async def test_schedules_retry_with_sanitized_error_code() -> None:
    repository = StubRepository((pending(),))
    processor = ProcessPendingDeliveries(repository, FailingProvider())

    await processor.execute(now=_NOW)

    assert repository.sent == []
    assert repository.failed == [(_DELIVERY_ID, "provider_error", _NOW + timedelta(minutes=5))]


@pytest.mark.anyio
async def test_rejects_invalid_batch_size() -> None:
    processor = ProcessPendingDeliveries(StubRepository(()), FakeCommunicationProvider())

    with pytest.raises(ValueError):
        await processor.execute(limit=101)
