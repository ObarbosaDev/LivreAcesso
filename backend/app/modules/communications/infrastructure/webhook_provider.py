"""Provedor HTTP neutro para integrar e-mail, WhatsApp ou gateway institucional."""

import httpx2

from backend.app.modules.communications.domain.entities import OutboundMessage
from backend.app.shared.application.exceptions import PersistenceUnavailableError


class WebhookCommunicationProvider:
    """Envia uma mensagem para um adaptador externo sem conhecer o fornecedor."""

    def __init__(self, url: str, token: str | None = None) -> None:
        if not url.startswith("https://"):
            raise ValueError("COMMUNICATION_WEBHOOK_URL deve usar HTTPS.")
        self._url = url
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._client = httpx2.AsyncClient(timeout=15.0, follow_redirects=False)

    async def send(self, message: OutboundMessage) -> str:
        try:
            response = await self._client.post(
                self._url,
                headers=self._headers,
                json={
                    "idempotency_key": str(message.idempotency_key),
                    "channel": message.channel.value,
                    "recipient": message.recipient,
                    "subject": message.subject,
                    "body": message.body,
                },
            )
        except httpx2.HTTPError as error:
            raise PersistenceUnavailableError from error
        if response.status_code >= 400 or len(response.content) > 64 * 1024:
            raise PersistenceUnavailableError
        try:
            payload = response.json()
        except ValueError as error:
            raise PersistenceUnavailableError from error
        external_id = payload.get("external_id") if isinstance(payload, dict) else None
        if not isinstance(external_id, str) or not external_id:
            raise PersistenceUnavailableError
        return external_id

    async def close(self) -> None:
        await self._client.aclose()
