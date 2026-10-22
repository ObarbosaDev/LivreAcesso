"""Portas de persistência exigidas pelo domínio de alunos."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.app.modules.students.domain.entities import Student
from backend.app.modules.students.domain.value_objects import StatusChangeReason


@dataclass(frozen=True, slots=True)
class PersistedStudentVersion:
    """Timestamps autoritativos produzidos pelo armazenamento."""

    created_at: datetime
    updated_at: datetime


class StudentRepository(Protocol):
    """Porta assíncrona de escrita e reidratação do agregado de aluno."""

    async def add(self, student: Student) -> PersistedStudentVersion: ...

    async def get_by_id(self, student_id: UUID) -> Student | None: ...

    async def update(
        self,
        student: Student,
        *,
        expected_updated_at: datetime,
    ) -> datetime: ...

    async def change_status(
        self,
        student: Student,
        *,
        reason: StatusChangeReason,
        expected_updated_at: datetime,
    ) -> datetime: ...
