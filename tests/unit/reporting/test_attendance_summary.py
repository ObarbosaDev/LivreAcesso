"""Testes dos cálculos de frequência."""

from uuid import uuid4

from backend.app.modules.reporting.domain.attendance import (
    AttendanceValue,
    summarize_attendance,
)


def test_summary_counts_justified_absence_as_valid_occurrence() -> None:
    summary = summarize_attendance(
        student_id=uuid4(),
        class_id=uuid4(),
        values=(
            AttendanceValue.PRESENT,
            AttendanceValue.ABSENT,
            AttendanceValue.ABSENT,
            AttendanceValue.EXCUSED,
        ),
    )

    assert summary.present_sessions == 1
    assert summary.absent_sessions == 2
    assert summary.excused_sessions == 1
    assert summary.consecutive_absences == 2
    assert summary.attendance_percentage == 50.0
