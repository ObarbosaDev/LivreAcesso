"""Runner do processamento da outbox, independente do provedor externo."""

import asyncio
import logging
from dataclasses import dataclass

from backend.app.modules.communications.application.delivery import ProcessPendingDeliveries

logger = logging.getLogger("livre_acesso.communications")


@dataclass(slots=True)
class CommunicationWorker:
    """Executa lotes pequenos e encerra sem deixar tarefa órfã."""

    processor: ProcessPendingDeliveries
    batch_size: int = 20
    interval_seconds: float = 30.0

    async def run_once(self) -> int:
        processed = await self.processor.execute(limit=self.batch_size)
        logger.info("communication_batch_completed processed=%s", processed)
        return processed

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        if self.batch_size < 1 or self.batch_size > 100:
            raise ValueError("O lote do worker deve estar entre 1 e 100.")
        if self.interval_seconds <= 0:
            raise ValueError("O intervalo do worker deve ser positivo.")

        while not stop_event.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self.interval_seconds)
            except TimeoutError:
                continue
