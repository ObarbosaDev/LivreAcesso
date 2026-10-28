"""Testes do ciclo de vida do runner de comunicação."""

import asyncio

import pytest

from backend.app.modules.communications.application.status import CommunicationQueueStatus
from backend.app.modules.communications.application.worker import CommunicationWorker


class StubProcessor:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, *, limit: int) -> int:
        self.calls += 1
        return limit


class StubMonitor:
    async def get_status(self) -> CommunicationQueueStatus:
        return CommunicationQueueStatus(2, 0, 1, 8, None)


@pytest.mark.anyio
async def test_worker_runs_once_and_returns_count() -> None:
    processor = StubProcessor()
    worker = CommunicationWorker(processor, batch_size=7)

    assert await worker.run_once() == 7
    assert processor.calls == 1


@pytest.mark.anyio
async def test_worker_reads_aggregated_queue_status() -> None:
    processor = StubProcessor()
    worker = CommunicationWorker(processor, monitor=StubMonitor())

    assert await worker.run_once() == 20


@pytest.mark.anyio
async def test_worker_stops_when_event_is_set() -> None:
    processor = StubProcessor()
    worker = CommunicationWorker(processor, batch_size=1, interval_seconds=60)
    stop_event = asyncio.Event()

    task = asyncio.create_task(worker.run_forever(stop_event))
    await asyncio.sleep(0)
    stop_event.set()
    await asyncio.wait_for(task, timeout=1)

    assert processor.calls == 1


@pytest.mark.anyio
async def test_worker_rejects_invalid_runtime_configuration() -> None:
    worker = CommunicationWorker(StubProcessor(), batch_size=101)

    with pytest.raises(ValueError):
        await worker.run_forever(asyncio.Event())
