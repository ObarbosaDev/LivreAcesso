"""Repositório em memória para testes e desenvolvimento."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from threading import RLock
from uuid import UUID

from backend.app.modules.enrollments.domain.entities import Enrollment, EnrollmentStatus
from backend.app.modules.enrollments.domain.exceptions import (
    ClassCapacityReachedError,
    DuplicateEnrollmentError,
    EnrollmentNotFoundError,
    EnrollmentVersionConflictError,
)


class InMemoryEnrollmentRepository:
    def __init__(self, *, class_capacities: dict[UUID, int] | None = None) -> None:
        self._items: dict[UUID, Enrollment] = {}
        self._capacities = class_capacities or {}
        self._lock = RLock()

    def _snapshot(self, item: Enrollment) -> Enrollment:
        return deepcopy(item)

    async def add(self, enrollment: Enrollment) -> Enrollment:
        with self._lock:
            if any(
                item.student_id == enrollment.student_id
                and item.class_id == enrollment.class_id
                and item.status is EnrollmentStatus.ACTIVE
                for item in self._items.values()
            ):
                raise DuplicateEnrollmentError
            capacity = self._capacities.get(enrollment.class_id)
            occupied = sum(
                item.class_id == enrollment.class_id and item.status is EnrollmentStatus.ACTIVE
                for item in self._items.values()
            )
            if capacity is not None and occupied >= capacity:
                raise ClassCapacityReachedError
            self._items[enrollment.id] = self._snapshot(enrollment)
            return self._snapshot(enrollment)

    async def get(self, enrollment_id: UUID) -> Enrollment | None:
        with self._lock:
            item = self._items.get(enrollment_id)
            return self._snapshot(item) if item else None

    async def find_active(self, student_id: UUID, class_id: UUID) -> Enrollment | None:
        with self._lock:
            return next(
                (
                    self._snapshot(item)
                    for item in self._items.values()
                    if item.student_id == student_id
                    and item.class_id == class_id
                    and item.status is EnrollmentStatus.ACTIVE
                ),
                None,
            )

    async def update(self, enrollment: Enrollment, *, expected_updated_at: datetime) -> Enrollment:
        with self._lock:
            current = self._items.get(enrollment.id)
            if current is None:
                raise EnrollmentNotFoundError
            if current.updated_at != expected_updated_at:
                raise EnrollmentVersionConflictError
            now = datetime.now(UTC)
            if now <= current.updated_at:
                now = current.updated_at + timedelta(microseconds=1)
            enrollment.updated_at = now
            self._items[enrollment.id] = self._snapshot(enrollment)
            return self._snapshot(enrollment)

    async def list(
        self,
        *,
        student_id: UUID | None,
        class_id: UUID | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Enrollment], int]:
        with self._lock:
            items = [
                self._snapshot(item)
                for item in self._items.values()
                if (student_id is None or item.student_id == student_id)
                and (class_id is None or item.class_id == class_id)
                and (status is None or item.status.value == status)
            ]
            items.sort(key=lambda item: item.created_at, reverse=True)
            return items[offset : offset + limit], len(items)

    async def occupancy(self, class_id: UUID) -> tuple[int, int, int]:
        with self._lock:
            capacity = self._capacities.get(class_id)
            if capacity is None:
                raise EnrollmentNotFoundError
            enrolled = sum(
                item.class_id == class_id and item.status is EnrollmentStatus.ACTIVE
                for item in self._items.values()
            )
            return capacity, enrolled, max(capacity - enrolled, 0)
