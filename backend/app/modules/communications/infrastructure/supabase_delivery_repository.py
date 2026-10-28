"""Persistência interna das tentativas de entrega da outbox."""

from datetime import datetime
from uuid import UUID

from backend.app.modules.communications.application.delivery import PendingDelivery
from backend.app.modules.communications.domain.entities import CommunicationChannel, OutboundMessage
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway


class SupabaseDeliveryRepository:
    """Chama somente RPCs internas autenticadas pela service_role."""

    def __init__(self, gateway: SupabaseRPCGateway) -> None:
        self._gateway = gateway

    async def claim_pending(self, *, limit: int, now: datetime) -> tuple[PendingDelivery, ...]:
        result = await self._gateway.call_service(
            "claim_pending_communications",
            {"p_limit": limit},
        )
        if not isinstance(result, list):
            raise ValueError("A reserva da outbox retornou um contrato inválido.")
        return tuple(self._to_pending(row) for row in result)

    async def mark_sent(self, delivery_id: UUID, external_id: str, sent_at: datetime) -> None:
        await self._gateway.call_service(
            "mark_communication_sent",
            {
                "p_delivery_id": str(delivery_id),
                "p_external_id": external_id,
                "p_processed_at": sent_at.isoformat(),
            },
        )

    async def mark_failed(self, delivery_id: UUID, error_code: str, available_at: datetime) -> None:
        await self._gateway.call_service(
            "mark_communication_failed",
            {
                "p_delivery_id": str(delivery_id),
                "p_error_code": error_code,
                "p_available_at": available_at.isoformat(),
            },
        )

    @staticmethod
    def _to_pending(row: object) -> PendingDelivery:
        if not isinstance(row, dict):
            raise ValueError("A outbox retornou uma linha inválida.")
        try:
            return PendingDelivery(
                delivery_id=UUID(str(row["id"])),
                attempts=int(row["attempts"]),
                message=OutboundMessage(
                    idempotency_key=UUID(str(row["idempotency_key"])),
                    recipient=str(row["recipient"]),
                    channel=CommunicationChannel(str(row["channel"])),
                    subject=str(row["subject"]),
                    body=str(row["body"]),
                    requested_by=(
                        UUID(str(row["requested_by"])) if row.get("requested_by") else None
                    ),
                    request_id=UUID(str(row["request_id"])) if row.get("request_id") else None,
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("A outbox retornou uma linha inválida.") from error
