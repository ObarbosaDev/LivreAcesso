"""Persistência em memória da fila, útil para testes e desenvolvimento."""

from copy import deepcopy
from uuid import UUID

from backend.app.modules.waiting_list.domain.entities import WaitingListEntry, WaitingListStatus
from backend.app.modules.waiting_list.domain.repositories import WaitingListRepository


class InMemoryWaitingListRepository(WaitingListRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, WaitingListEntry] = {}

    async def add(self, entry: WaitingListEntry) -> WaitingListEntry:
        self._items[entry.id] = deepcopy(entry)
        return deepcopy(entry)

    async def get(self, entry_id: UUID) -> WaitingListEntry | None:
        entry = self._items.get(entry_id)
        return deepcopy(entry) if entry else None

    async def update(self, entry: WaitingListEntry) -> WaitingListEntry:
        self._items[entry.id] = deepcopy(entry)
        return deepcopy(entry)

    def next_position(self, class_id: UUID) -> int:
        positions = [
            entry.position
            for entry in self._items.values()
            if entry.class_id == class_id and entry.status is WaitingListStatus.WAITING
        ]
        return max(positions, default=0) + 1

    def has_active_student(self, student_id: UUID, class_id: UUID) -> bool:
        return any(
            entry.student_id == student_id
            and entry.class_id == class_id
            and entry.status.value in {"aguardando", "vaga_ofertada"}
            for entry in self._items.values()
        )
