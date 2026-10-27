"""Porta de persistência das matrículas."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.app.modules.enrollments.domain.entities import Enrollment


class EnrollmentRepository(Protocol):
    async def add(self, enrollment: Enrollment) -> Enrollment: ...
    async def get(self, enrollment_id: UUID) -> Enrollment | None: ...
    async def find_active(self, student_id: UUID, class_id: UUID) -> Enrollment | None: ...
    async def update(
        self, enrollment: Enrollment, *, expected_updated_at: datetime
    ) -> Enrollment: ...

    async def list(
        self,
        *,
        student_id: UUID | None,
        class_id: UUID | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Enrollment], int]: ...
