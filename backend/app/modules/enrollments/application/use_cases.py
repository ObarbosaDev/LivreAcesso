"""Casos de uso do ciclo de matrícula."""

from dataclasses import dataclass
from uuid import UUID

from backend.app.modules.enrollments.application.dtos import (
    EnrollmentInput,
    EnrollmentOccupancyOutput,
    EnrollmentOutput,
    EnrollmentPageOutput,
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

    async def execute(self, enrollment_id: UUID, dto: EnrollmentStatusInput) -> EnrollmentOutput:
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


@dataclass(slots=True)
class ListEnrollments:
    repository: EnrollmentRepository

    async def execute(
        self,
        *,
        student_id: UUID | None,
        class_id: UUID | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> EnrollmentPageOutput:
        items, total = await self.repository.list(
            student_id=student_id,
            class_id=class_id,
            status=status,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return EnrollmentPageOutput(
            items=[_output(item) for item in items],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size if total else 0,
        )


@dataclass(slots=True)
class GetEnrollmentOccupancy:
    repository: EnrollmentRepository

    async def execute(self, class_id: UUID) -> EnrollmentOccupancyOutput:
        capacity, enrolled, available = await self.repository.occupancy(class_id)
        return EnrollmentOccupancyOutput(
            class_id=class_id,
            capacity=capacity,
            enrolled=enrolled,
            available=available,
        )
