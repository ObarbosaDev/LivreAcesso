"""Entidades de alerta sem dados pessoais desnecessários."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class AlertType(StrEnum):
    CONSECUTIVE_ABSENCES = "faltas_consecutivas"
    LOW_ATTENDANCE = "frequencia_baixa"


@dataclass(slots=True)
class AttendanceAlert:
    student_id: UUID
    alert_type: AlertType
    title: str
    detail: str
    threshold: int
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None

    @property
    def resolved(self) -> bool:
        return self.resolved_at is not None

    def resolve(self, *, resolved_at: datetime | None = None) -> None:
        self.resolved_at = resolved_at or datetime.now(UTC)
