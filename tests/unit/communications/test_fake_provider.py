"""O fake prova idempotência sem usar dados reais ou rede."""

import asyncio
from uuid import uuid4

from backend.app.modules.communications.application.use_cases import SendCommunication
from backend.app.modules.communications.domain.entities import (
    CommunicationChannel,
    OutboundMessage,
)
from backend.app.modules.communications.infrastructure.fake_provider import (
    FakeCommunicationProvider,
)


def test_fake_provider_does_not_send_same_message_twice() -> None:
    async def scenario() -> None:
        provider = FakeCommunicationProvider()
        message = OutboundMessage(
            idempotency_key=uuid4(),
            recipient="responsavel@example.test",
            channel=CommunicationChannel.EMAIL,
            subject="Vaga disponível",
            body="Mensagem sintética de teste.",
        )

        sender = SendCommunication(provider)
        first = await sender.execute(message)
        second = await sender.execute(message)

        assert first == second
        assert len(provider.sent) == 1

    asyncio.run(scenario())
