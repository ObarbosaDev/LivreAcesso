"""Porta estável para envio, independente do provedor escolhido."""

from typing import Protocol

from backend.app.modules.communications.domain.entities import OutboundMessage


class CommunicationProvider(Protocol):
    async def send(self, message: OutboundMessage) -> str: ...
