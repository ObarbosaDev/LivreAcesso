"""Testes do adaptador interno de processamento da outbox."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from backend.app.modules.communications.infrastructure.supabase_delivery_repository import (
    SupabaseDeliveryRepository,
)

_DELIVERY_ID = UUID("00000000-0000-4000-8000-000000000001")
_KEY = UUID("00000000-0000-4000-8000-000000000002")
_ACTOR = UUID("00000000-0000-4000-8000-000000000003")
_REQUEST = UUID("00000000-0000-4000-8000-000000000004")


class StubGateway:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def call_service(self, function_name: str, payload: dict[str, object]) -> object:
        self.calls.append((function_name, payload))
        return self.response


def delivery_row() -> dict[str, object]:
    return {
        "id": str(_DELIVERY_ID),
        "idempotency_key": str(_KEY),
        "channel": "email",
        "recipient": "familia@example.com",
        "subject": "Aviso",
        "body": "Conteúdo",
        "attempts": 1,
        "requested_by": str(_ACTOR),
        "request_id": str(_REQUEST),
    }


@pytest.mark.anyio
async def test_claim_converts_private_row_without_exposing_extra_data() -> None:
    gateway = StubGateway([delivery_row()])
    repository = SupabaseDeliveryRepository(gateway)  # type: ignore[arg-type]

    deliveries = await repository.claim_pending(limit=10, now=datetime.now(UTC))

    assert len(deliveries) == 1
    assert deliveries[0].delivery_id == _DELIVERY_ID
    assert deliveries[0].message.requested_by == _ACTOR
    assert gateway.calls == [("claim_pending_communications", {"p_limit": 10})]


@pytest.mark.anyio
async def test_mark_methods_send_only_sanitized_worker_payloads() -> None:
    gateway = StubGateway(None)
    repository = SupabaseDeliveryRepository(gateway)  # type: ignore[arg-type]
    now = datetime(2026, 10, 28, 12, tzinfo=UTC)

    await repository.mark_sent(_DELIVERY_ID, "provider-1", now)
    await repository.mark_failed(_DELIVERY_ID, "provider_error", now)

    assert gateway.calls == [
        (
            "mark_communication_sent",
            {
                "p_delivery_id": str(_DELIVERY_ID),
                "p_external_id": "provider-1",
                "p_processed_at": now.isoformat(),
            },
        ),
        (
            "mark_communication_failed",
            {
                "p_delivery_id": str(_DELIVERY_ID),
                "p_error_code": "provider_error",
                "p_available_at": now.isoformat(),
            },
        ),
    ]


@pytest.mark.anyio
async def test_claim_rejects_invalid_remote_row() -> None:
    gateway = StubGateway([{"id": "not-a-uuid"}])
    repository = SupabaseDeliveryRepository(gateway)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="linha inválida"):
        await repository.claim_pending(limit=1, now=datetime.now(UTC))


@pytest.mark.anyio
async def test_queue_status_is_aggregated_without_message_content() -> None:
    gateway = StubGateway(
        {
            "pending": 2,
            "processing": 1,
            "failed": 3,
            "sent": 10,
            "oldest_pending_at": "2026-10-28T12:00:00Z",
        }
    )
    repository = SupabaseDeliveryRepository(gateway)  # type: ignore[arg-type]

    status = await repository.get_status()

    assert status.pending == 2
    assert status.processing == 1
    assert status.failed == 3
    assert status.sent == 10
    assert status.oldest_pending_at is not None
    assert gateway.calls == [("get_communication_queue_status", {})]
