"""Provedor fake determinístico; nunca alcança a internet."""

from uuid import UUID

from backend.app.modules.communications.domain.entities import OutboundMessage


class FakeCommunicationProvider:
    def __init__(self) -> None:
        self.sent: dict[UUID, str] = {}

    async def send(self, message: OutboundMessage) -> str:
        if message.idempotency_key in self.sent:
            return self.sent[message.idempotency_key]
        external_id = f"fake-{message.idempotency_key}"
        self.sent[message.idempotency_key] = external_id
        return external_id
