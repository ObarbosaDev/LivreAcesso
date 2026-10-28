"""Testes do provedor HTTP neutro de comunicação."""

import asyncio
import json
from uuid import UUID

import httpx2
import pytest

from backend.app.modules.communications.domain.entities import CommunicationChannel, OutboundMessage
from backend.app.modules.communications.infrastructure.webhook_provider import (
    WebhookCommunicationProvider,
)


def message() -> OutboundMessage:
    return OutboundMessage(
        idempotency_key=UUID("00000000-0000-4000-8000-000000000001"),
        recipient="familia@example.com",
        channel=CommunicationChannel.EMAIL,
        subject="Aviso",
        body="Mensagem",
    )


def test_webhook_requires_https() -> None:
    with pytest.raises(ValueError):
        WebhookCommunicationProvider("http://example.com")


def test_webhook_returns_external_id() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.headers["Authorization"] == "Bearer token"
        assert json.loads(request.content)["channel"] == "email"
        return httpx2.Response(200, json={"external_id": "provider-1"})

    async def scenario() -> None:
        transport = httpx2.MockTransport(handler)
        client = httpx2.AsyncClient(transport=transport)
        provider = WebhookCommunicationProvider("https://provider.example/send", "token")
        await provider._client.aclose()
        provider._client = client
        assert await provider.send(message()) == "provider-1"
        await provider.close()

    asyncio.run(scenario())
