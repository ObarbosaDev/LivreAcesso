"""Processamento seguro de entregas pendentes da outbox."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from backend.app.modules.communications.application.ports import CommunicationProvider
from backend.app.modules.communications.domain.entities import OutboundMessage


@dataclass(frozen=True, slots=True)
class PendingDelivery:
    """Intentção reservada para uma única tentativa de entrega."""

    delivery_id: UUID
    message: OutboundMessage
    attempts: int


class DeliveryRepository(Protocol):
    async def claim_pending(self, *, limit: int, now: datetime) -> tuple[PendingDelivery, ...]: ...

    async def mark_sent(self, delivery_id: UUID, external_id: str, sent_at: datetime) -> None: ...

    async def mark_failed(
        self, delivery_id: UUID, error_code: str, available_at: datetime
    ) -> None: ...


@dataclass(slots=True)
class ProcessPendingDeliveries:
    """Entrega um lote sem duplicar mensagens e agenda falhas para retry."""

    repository: DeliveryRepository
    provider: CommunicationProvider
    retry_delay: timedelta = timedelta(minutes=5)
    max_attempts: int = 5

    async def execute(self, *, limit: int = 20, now: datetime | None = None) -> int:
        if not 1 <= limit <= 100:
            raise ValueError("O lote deve conter entre 1 e 100 entregas.")
        if not 1 <= self.max_attempts <= 20:
            raise ValueError("O limite de tentativas deve estar entre 1 e 20.")

        current_time = now or datetime.now(UTC)
        deliveries = await self.repository.claim_pending(limit=limit, now=current_time)
        processed = 0
        for delivery in deliveries:
            try:
                external_id = await self.provider.send(delivery.message)
            except Exception:
                # O detalhe do provedor não pode chegar ao banco nem ao cliente.
                await self.repository.mark_failed(
                    delivery.delivery_id,
                    (
                        "retry_exhausted"
                        if delivery.attempts >= self.max_attempts
                        else "provider_error"
                    ),
                    current_time
                    if delivery.attempts >= self.max_attempts
                    else current_time + self.retry_delay,
                )
            else:
                await self.repository.mark_sent(delivery.delivery_id, external_id, current_time)
            processed += 1
        return processed
