"""Entidades da chamada em lote.

Uma sessão representa uma aula concreta de uma turma. Os registros ficam
associados a matrículas, e não diretamente ao cadastro do estudante; assim a
frequência continua correta quando o mesmo estudante participa de modalidades
ou turmas diferentes.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from backend.app.modules.attendance.domain.exceptions import (
    AttendanceAlreadyClosedError,
    InvalidAttendanceError,
)


class AttendanceStatus(StrEnum):
    PRESENT = "presente"
    ABSENT = "ausente"
    EXCUSED = "justificada"


class AttendanceSessionStatus(StrEnum):
    OPEN = "aberta"
    CLOSED = "fechada"


@dataclass(frozen=True, slots=True)
class AttendanceMark:
    """Marca de uma matrícula em uma sessão específica."""

    enrollment_id: UUID
    status: AttendanceStatus
    note: str | None = None

    def __post_init__(self) -> None:
        if self.status is AttendanceStatus.EXCUSED and not self.note:
            raise InvalidAttendanceError("Uma falta justificada precisa de observação.")
        if self.note and len(self.note.strip()) > 500:
            raise InvalidAttendanceError("A observação da frequência é muito longa.")


@dataclass(slots=True)
class AttendanceSession:
    """Chamada de uma turma em uma data de aula."""

    id: UUID
    class_id: UUID
    session_date: date
    status: AttendanceSessionStatus
    marks: dict[UUID, AttendanceMark] = field(default_factory=dict)
    closed_at: datetime | None = None

    @classmethod
    def open(cls, *, class_id: UUID, session_date: date) -> "AttendanceSession":
        return cls(uuid4(), class_id, session_date, AttendanceSessionStatus.OPEN)

    def record(self, marks: tuple[AttendanceMark, ...]) -> None:
        """Substitui a chamada em uma operação única enquanto a sessão está aberta."""
        if self.status is AttendanceSessionStatus.CLOSED:
            raise AttendanceAlreadyClosedError("A chamada já foi fechada.")
        enrollment_ids = [mark.enrollment_id for mark in marks]
        if len(enrollment_ids) != len(set(enrollment_ids)):
            raise InvalidAttendanceError("A mesma matrícula não pode aparecer duas vezes.")
        self.marks = {mark.enrollment_id: mark for mark in marks}

    def close(self, *, closed_at: datetime) -> None:
        if self.status is AttendanceSessionStatus.CLOSED:
            raise AttendanceAlreadyClosedError("A chamada já foi fechada.")
        if not self.marks:
            raise InvalidAttendanceError("A chamada precisa de pelo menos um registro.")
        self.status = AttendanceSessionStatus.CLOSED
        self.closed_at = closed_at
