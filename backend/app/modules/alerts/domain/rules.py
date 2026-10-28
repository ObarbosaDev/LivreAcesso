"""Regras explícitas para transformar frequência em acompanhamento."""

from backend.app.modules.alerts.domain.entities import AlertType, AttendanceAlert
from backend.app.modules.reporting.domain.attendance import AttendanceSummary


def alert_for_summary(
    summary: AttendanceSummary,
    *,
    consecutive_absence_threshold: int = 3,
    minimum_attendance_percentage: float = 75.0,
) -> AttendanceAlert | None:
    if summary.consecutive_absences >= consecutive_absence_threshold:
        return AttendanceAlert(
            student_id=summary.student_id,
            alert_type=AlertType.CONSECUTIVE_ABSENCES,
            title="Faltas consecutivas precisam de acompanhamento",
            detail=f"{summary.consecutive_absences} faltas consecutivas registradas.",
            threshold=consecutive_absence_threshold,
        )
    if (
        summary.occurred_sessions > 0
        and summary.attendance_percentage < minimum_attendance_percentage
    ):
        return AttendanceAlert(
            student_id=summary.student_id,
            alert_type=AlertType.LOW_ATTENDANCE,
            title="Frequência abaixo do acompanhamento esperado",
            detail=f"Frequência atual de {summary.attendance_percentage:.2f}%.",
            threshold=int(minimum_attendance_percentage),
        )
    return None
