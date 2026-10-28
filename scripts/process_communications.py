"""Processa um lote da outbox usando o webhook configurado no ambiente."""

import asyncio
import os

from backend.app.core.config import get_settings
from backend.app.modules.communications.application.delivery import ProcessPendingDeliveries
from backend.app.modules.communications.infrastructure.supabase_delivery_repository import (
    SupabaseDeliveryRepository,
)
from backend.app.modules.communications.infrastructure.webhook_provider import (
    WebhookCommunicationProvider,
)
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway


async def run() -> int:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise RuntimeError("Supabase não está configurado para o worker.")
    if not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY é obrigatório para o worker.")
    webhook_url = os.getenv("COMMUNICATION_WEBHOOK_URL", "").strip()
    if not webhook_url:
        raise RuntimeError("COMMUNICATION_WEBHOOK_URL é obrigatório para o worker.")

    gateway = SupabaseRPCGateway(
        settings.supabase_url,
        settings.supabase_publishable_key,
        service_role_key=settings.supabase_service_role_key,
    )
    provider = WebhookCommunicationProvider(
        webhook_url,
        os.getenv("COMMUNICATION_WEBHOOK_TOKEN"),
    )
    try:
        processor = ProcessPendingDeliveries(
            SupabaseDeliveryRepository(gateway),
            provider,
        )
        return await processor.execute(limit=int(os.getenv("COMMUNICATION_BATCH_SIZE", "20")))
    finally:
        await provider.close()
        await gateway.close()


def main() -> None:
    processed = asyncio.run(run())
    print(f"Entregas processadas: {processed}")


if __name__ == "__main__":
    main()
