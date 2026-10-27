"""Testes do domínio de matrículas."""

import asyncio
from uuid import uuid4

import pytest

from backend.app.modules.enrollments.application.dtos import EnrollmentInput
from backend.app.modules.enrollments.application.use_cases import CreateEnrollment
from backend.app.modules.enrollments.domain.entities import EnrollmentStatus
from backend.app.modules.enrollments.domain.exceptions import (
    ClassCapacityReachedError,
    DuplicateEnrollmentError,
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
