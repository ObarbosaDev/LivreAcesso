"""Portas de persistência exigidas pelo domínio de alunos."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.app.modules.students.domain.entities import (
    Guardian,
    GuardianRelationship,
    Student,
    StudentGuardian,
)
from backend.app.modules.students.domain.value_objects import (
    GuardianUnlinkReason,
    StatusChangeReason,
)


@dataclass(frozen=True, slots=True)
class PersistedStudentVersion:
    """Timestamps autoritativos produzidos pelo armazenamento."""

    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StudentGuardianSnapshot:
    """Vínculo integral acompanhado da versão atual do aluno."""

    student_updated_at: datetime
    link: StudentGuardian


@dataclass(frozen=True, slots=True)
class StudentGuardianMutation:
    """Resultado de escrita que informa se houve mudança efetiva."""

    snapshot: StudentGuardianSnapshot
    changed: bool


@dataclass(frozen=True, slots=True)
class StudentGuardianUnlinkResult:
    """Nova versão do aluno após a desvinculação lógica."""

    student_id: UUID
    guardian_id: UUID
    student_updated_at: datetime
    changed: bool


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


class StudentGuardianRepository(Protocol):
    """Porta transacional para contatos vinculados ao cadastro do aluno."""

    async def get_guardian(
        self,
        student_id: UUID,
        guardian_id: UUID,
    ) -> StudentGuardianSnapshot: ...

    async def add_guardian(
        self,
        student_id: UUID,
        *,
        guardian: Guardian | None,
        existing_guardian_id: UUID | None,
        relationship: GuardianRelationship,
        make_primary: bool,
        receives_communications: bool,
        expected_student_updated_at: datetime,
    ) -> StudentGuardianMutation: ...

    async def update_guardian(
        self,
        student_id: UUID,
        guardian: Guardian,
        *,
        relationship: GuardianRelationship,
        receives_communications: bool,
        expected_student_updated_at: datetime,
        expected_guardian_updated_at: datetime,
    ) -> StudentGuardianMutation: ...

    async def set_primary_guardian(
        self,
        student_id: UUID,
        guardian_id: UUID,
        *,
        expected_student_updated_at: datetime,
    ) -> StudentGuardianMutation: ...

    async def unlink_guardian(
        self,
        student_id: UUID,
        guardian_id: UUID,
        *,
        reason: GuardianUnlinkReason,
        expected_student_updated_at: datetime,
    ) -> StudentGuardianUnlinkResult: ...
