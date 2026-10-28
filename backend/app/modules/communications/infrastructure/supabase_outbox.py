"""Adaptador da outbox privada para intenções de comunicação."""

from backend.app.modules.communications.domain.entities import OutboundMessage
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway


class SupabaseCommunicationOutbox:
    def __init__(self, gateway: SupabaseRPCGateway, context: RequestContext) -> None:
        self.gateway = gateway
        self.context = context

    async def enqueue(self, message: OutboundMessage) -> str:
        result = await self.gateway.call(
            "enqueue_communication",
            {
                "p_idempotency_key": str(message.idempotency_key),
                "p_channel": message.channel.value,
                "p_recipient": message.recipient,
                "p_subject": message.subject,
                "p_body": message.body,
            },
            self.context,
        )
        if not isinstance(result, dict) or not isinstance(result.get("id"), str):
            raise ValueError("A outbox não retornou um identificador válido.")
        delivery_id = result["id"]
        if not isinstance(delivery_id, str):
            raise ValueError("A outbox não retornou um identificador válido.")
        return delivery_id
