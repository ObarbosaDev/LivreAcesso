"""Casos de uso de comunicação com idempotência na porta do provedor."""

from dataclasses import dataclass

from backend.app.modules.communications.application.ports import CommunicationProvider
from backend.app.modules.communications.domain.entities import OutboundMessage


@dataclass(slots=True)
class SendCommunication:
    provider: CommunicationProvider

    async def execute(self, message: OutboundMessage) -> str:
        return await self.provider.send(message)
