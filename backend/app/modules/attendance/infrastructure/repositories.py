"""Persistência em memória para desenvolvimento e testes determinísticos."""

from copy import deepcopy
from uuid import UUID

from backend.app.modules.attendance.domain.entities import AttendanceSession
from backend.app.modules.attendance.domain.repositories import AttendanceRepository


class InMemoryAttendanceRepository(AttendanceRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, AttendanceSession] = {}

    async def add(self, session: AttendanceSession) -> AttendanceSession:
        self._items[session.id] = deepcopy(session)
        return deepcopy(session)

    async def get(self, session_id: UUID) -> AttendanceSession | None:
        session = self._items.get(session_id)
        return deepcopy(session) if session else None

    async def update(self, session: AttendanceSession) -> AttendanceSession:
        self._items[session.id] = deepcopy(session)
        return deepcopy(session)

    async def list_by_class(self, class_id: UUID) -> list[AttendanceSession]:
        items = [session for session in self._items.values() if session.class_id == class_id]
        items.sort(key=lambda session: session.session_date, reverse=True)
        return deepcopy(items)
