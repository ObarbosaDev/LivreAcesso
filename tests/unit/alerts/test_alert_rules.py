"""Testes das regras de acompanhamento por frequência."""

from uuid import uuid4

from backend.app.modules.alerts.domain.entities import AlertType
from backend.app.modules.alerts.domain.rules import alert_for_summary
from backend.app.modules.reporting.domain.attendance import (
    AttendanceValue,
    summarize_attendance,
)


def test_alerts_consecutive_absences_before_percentage() -> None:
    summary = summarize_attendance(
        student_id=uuid4(),
        class_id=uuid4(),
        values=(
            AttendanceValue.ABSENT,
            AttendanceValue.ABSENT,
            AttendanceValue.ABSENT,
            AttendanceValue.PRESENT,
        ),
    )

    alert = alert_for_summary(summary)

    assert alert is not None
    assert alert.alert_type is AlertType.CONSECUTIVE_ABSENCES


def test_no_alert_is_not_a_fake_success_record() -> None:
    summary = summarize_attendance(
        student_id=uuid4(),
        class_id=uuid4(),
        values=(AttendanceValue.PRESENT, AttendanceValue.PRESENT),
    )
    assert alert_for_summary(summary) is None
