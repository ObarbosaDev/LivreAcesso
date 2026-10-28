"""Porta de persistência das sessões de frequência."""

from abc import ABC, abstractmethod
from uuid import UUID

from backend.app.modules.attendance.domain.entities import AttendanceSession


class AttendanceRepository(ABC):
    @abstractmethod
    async def add(self, session: AttendanceSession) -> AttendanceSession: ...

    @abstractmethod
    async def get(self, session_id: UUID) -> AttendanceSession | None: ...

    @abstractmethod
    async def update(self, session: AttendanceSession) -> AttendanceSession: ...
