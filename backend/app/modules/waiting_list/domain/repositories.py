"""Porta de persistência da fila de espera."""

from abc import ABC, abstractmethod
from uuid import UUID

from backend.app.modules.waiting_list.domain.entities import WaitingListEntry


class WaitingListRepository(ABC):
    @abstractmethod
    async def add(self, entry: WaitingListEntry) -> WaitingListEntry: ...

    @abstractmethod
    async def get(self, entry_id: UUID) -> WaitingListEntry | None: ...
