"""Casos de uso do ciclo de matrícula."""

from dataclasses import dataclass
from uuid import UUID

from backend.app.modules.enrollments.application.dtos import (
    EnrollmentInput,
    EnrollmentOutput,
    EnrollmentStatusInput,
)
from backend.app.modules.enrollments.domain.entities import Enrollment
from backend.app.modules.enrollments.domain.exceptions import EnrollmentNotFoundError
from backend.app.modules.enrollments.domain.repositories import EnrollmentRepository


def _output(item: Enrollment) -> EnrollmentOutput:
    return EnrollmentOutput.model_validate(item, from_attributes=True)


@dataclass(slots=True)
class CreateEnrollment:
    repository: EnrollmentRepository

    async def execute(self, dto: EnrollmentInput) -> EnrollmentOutput:
        return _output(
            await self.repository.add(
                Enrollment.create(student_id=dto.student_id, class_id=dto.class_id)
            )
        )


@dataclass(slots=True)
class GetEnrollment:
    repository: EnrollmentRepository

    async def execute(self, enrollment_id: UUID) -> EnrollmentOutput:
        item = await self.repository.get(enrollment_id)
        if item is None:
            raise EnrollmentNotFoundError
        return _output(item)


@dataclass(slots=True)
class ChangeEnrollmentStatus:
    repository: EnrollmentRepository
    active: bool

    async def execute(
        self, enrollment_id: UUID, dto: EnrollmentStatusInput
    ) -> EnrollmentOutput:
        item = await self.repository.get(enrollment_id)
        if item is None:
            raise EnrollmentNotFoundError
        if self.active:
            item.reactivate()
        else:
            item.cancel()
        return _output(
            await self.repository.update(item, expected_updated_at=dto.expected_updated_at)
        )
