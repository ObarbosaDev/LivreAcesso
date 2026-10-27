"""Testes do domínio de matrículas."""

import asyncio
from uuid import uuid4

import pytest

from backend.app.modules.enrollments.application.dtos import (
    EnrollmentInput,
    EnrollmentStatusInput,
)
from backend.app.modules.enrollments.application.use_cases import (
    ChangeEnrollmentStatus,
    CreateEnrollment,
    GetEnrollment,
    GetEnrollmentOccupancy,
    ListEnrollments,
)
from backend.app.modules.enrollments.domain.entities import Enrollment, EnrollmentStatus
from backend.app.modules.enrollments.domain.exceptions import (
    ClassCapacityReachedError,
    DuplicateEnrollmentError,
    EnrollmentNotFoundError,
    EnrollmentVersionConflictError,
)
from backend.app.modules.enrollments.infrastructure.repositories import (
    InMemoryEnrollmentRepository,
)


def test_enrollment_cycle_and_duplicate_guard() -> None:
    async def scenario() -> None:
        student_id, class_id = uuid4(), uuid4()
        repository = InMemoryEnrollmentRepository(class_capacities={class_id: 1})
        create = CreateEnrollment(repository)
        first = await create.execute(EnrollmentInput(student_id=student_id, class_id=class_id))
        assert first.status is EnrollmentStatus.ACTIVE
        with pytest.raises(DuplicateEnrollmentError):
            await create.execute(EnrollmentInput(student_id=student_id, class_id=class_id))
        with pytest.raises(ClassCapacityReachedError):
            await create.execute(EnrollmentInput(student_id=uuid4(), class_id=class_id))

    asyncio.run(scenario())


def test_enrollment_queries_and_status_changes_cover_success_and_conflicts() -> None:
    async def scenario() -> None:
        student_id, class_id = uuid4(), uuid4()
        repository = InMemoryEnrollmentRepository(class_capacities={class_id: 2})
        created = await CreateEnrollment(repository).execute(
            EnrollmentInput(student_id=student_id, class_id=class_id)
        )
        page = await ListEnrollments(repository).execute(
            student_id=student_id,
            class_id=class_id,
            status=None,
            page=1,
            page_size=10,
        )
        assert page.total == 1
        assert (await GetEnrollment(repository).execute(created.id)).id == created.id
        occupancy = await GetEnrollmentOccupancy(repository).execute(class_id)
        assert occupancy.enrolled == 1
        assert occupancy.available == 1

        reason = EnrollmentStatusInput(
            expected_updated_at=created.updated_at,
            reason="Cancelamento confirmado pela coordenação",
        )
        cancelled = await ChangeEnrollmentStatus(repository, active=False).execute(
            created.id, reason
        )
        assert cancelled.status is EnrollmentStatus.CANCELLED
        reactivated = await ChangeEnrollmentStatus(repository, active=True).execute(
            created.id,
            EnrollmentStatusInput(
                expected_updated_at=cancelled.updated_at,
                reason="Retorno confirmado pela coordenação",
            ),
        )
        assert reactivated.status is EnrollmentStatus.ACTIVE
        with pytest.raises(EnrollmentVersionConflictError):
            await ChangeEnrollmentStatus(repository, active=False).execute(created.id, reason)
        with pytest.raises(EnrollmentNotFoundError):
            await GetEnrollment(repository).execute(uuid4())

    asyncio.run(scenario())


def test_enrollment_entity_rejects_invalid_status_transitions() -> None:
    item = Enrollment.create(student_id=uuid4(), class_id=uuid4())
    with pytest.raises(ValueError):
        item.reactivate()
    item.cancel()
    with pytest.raises(ValueError):
        item.cancel()
