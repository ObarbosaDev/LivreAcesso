"""Casos de uso da fila com decisão humana explícita."""

from uuid import UUID

from backend.app.modules.waiting_list.application.dtos import (
    WaitingListInput,
    WaitingListOutput,
)
from backend.app.modules.waiting_list.domain.entities import WaitingListEntry
from backend.app.modules.waiting_list.domain.repositories import WaitingListRepository
from backend.app.modules.waiting_list.infrastructure.repositories import (
    InMemoryWaitingListRepository,
)


def _output(entry: WaitingListEntry) -> WaitingListOutput:
    return WaitingListOutput(
        id=entry.id,
        student_id=entry.student_id,
        class_id=entry.class_id,
        position=entry.position,
        status=entry.status,
    )


class JoinWaitingList:
    def __init__(self, repository: InMemoryWaitingListRepository) -> None:
        self.repository = repository

    async def execute(self, payload: WaitingListInput) -> WaitingListOutput:
        if self.repository.has_active_student(payload.student_id, payload.class_id):
            raise ValueError("O estudante já está na fila desta turma.")
        entry = WaitingListEntry(
            student_id=payload.student_id,
            class_id=payload.class_id,
            position=self.repository.next_position(payload.class_id),
        )
        return _output(await self.repository.add(entry))


class OfferWaitingListEntry:
    def __init__(self, repository: WaitingListRepository) -> None:
        self.repository = repository

    async def execute(self, entry_id: UUID) -> WaitingListOutput:
        entry = await self.repository.get(entry_id)
        if entry is None:
            raise ValueError("Entrada da fila não encontrada.")
        entry.offer()
        return _output(await self.repository.update(entry))


class AcceptWaitingListEntry:
    def __init__(self, repository: WaitingListRepository) -> None:
        self.repository = repository

    async def execute(self, entry_id: UUID) -> WaitingListOutput:
        entry = await self.repository.get(entry_id)
        if entry is None:
            raise ValueError("Entrada da fila não encontrada.")
        entry.accept()
        return _output(await self.repository.update(entry))
