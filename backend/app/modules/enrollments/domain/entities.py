"""Entidade e invariantes do ciclo de matrícula."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class EnrollmentStatus(StrEnum):
    ACTIVE = "ativa"
    CANCELLED = "cancelada"


@dataclass(slots=True)
class Enrollment:
    id: UUID
    student_id: UUID
    class_id: UUID
    status: EnrollmentStatus
    created_at: datetime
    updated_at: datetime
    _events: list[object] = field(default_factory=list, init=False, repr=False, compare=False)

    @classmethod
    def create(cls, *, student_id: UUID, class_id: UUID) -> "Enrollment":
        now = datetime.now(UTC)
        return cls(uuid4(), student_id, class_id, EnrollmentStatus.ACTIVE, now, now)

    def cancel(self) -> bool:
        if self.status is EnrollmentStatus.CANCELLED:
            return False
        self.status = EnrollmentStatus.CANCELLED
        return True

    def reactivate(self) -> bool:
        if self.status is EnrollmentStatus.ACTIVE:
            return False
        self.status = EnrollmentStatus.ACTIVE
        return True
