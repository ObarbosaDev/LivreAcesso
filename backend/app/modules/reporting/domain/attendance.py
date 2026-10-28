"""Cálculos puros para relatórios de frequência."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class AttendanceValue(StrEnum):
    PRESENT = "presente"
    ABSENT = "ausente"
    EXCUSED = "justificada"


@dataclass(frozen=True, slots=True)
class AttendanceSummary:
    student_id: UUID
    class_id: UUID
    occurred_sessions: int
    present_sessions: int
    absent_sessions: int
    excused_sessions: int
    consecutive_absences: int

    @property
    def attendance_percentage(self) -> float:
        if self.occurred_sessions == 0:
            return 0.0
        return round(
            (self.present_sessions + self.excused_sessions) / self.occurred_sessions * 100,
            2,
        )


def summarize_attendance(
    *,
    student_id: UUID,
    class_id: UUID,
    values: tuple[AttendanceValue, ...],
) -> AttendanceSummary:
    consecutive = 0
    longest = 0
    for value in values:
        if value is AttendanceValue.ABSENT:
            consecutive += 1
            longest = max(longest, consecutive)
        else:
            consecutive = 0
    return AttendanceSummary(
        student_id=student_id,
        class_id=class_id,
        occurred_sessions=len(values),
        present_sessions=values.count(AttendanceValue.PRESENT),
        absent_sessions=values.count(AttendanceValue.ABSENT),
        excused_sessions=values.count(AttendanceValue.EXCUSED),
        consecutive_absences=longest,
    )
