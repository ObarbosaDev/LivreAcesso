"""Testes das invariantes da chamada em lote."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from backend.app.modules.attendance.domain.entities import (
    AttendanceMark,
    AttendanceSession,
    AttendanceSessionStatus,
    AttendanceStatus,
)
from backend.app.modules.attendance.domain.exceptions import (
    AttendanceAlreadyClosedError,
    InvalidAttendanceError,
)


def test_session_records_a_complete_batch_and_closes_once() -> None:
    session = AttendanceSession.open(class_id=uuid4(), session_date=date(2026, 10, 27))
    first = AttendanceMark(uuid4(), AttendanceStatus.PRESENT)
    second = AttendanceMark(uuid4(), AttendanceStatus.ABSENT)

    session.record((first, second))
    session.close(closed_at=datetime(2026, 10, 27, 20, tzinfo=UTC))

    assert session.status is AttendanceSessionStatus.CLOSED
    assert session.marks[first.enrollment_id] is first
    assert session.closed_at is not None

    with pytest.raises(AttendanceAlreadyClosedError):
        session.record((first,))


def test_session_rejects_duplicate_marks_and_empty_close() -> None:
    session = AttendanceSession.open(class_id=uuid4(), session_date=date(2026, 10, 27))
    mark = AttendanceMark(uuid4(), AttendanceStatus.PRESENT)

    with pytest.raises(InvalidAttendanceError):
        session.record((mark, mark))
    with pytest.raises(InvalidAttendanceError):
        session.close(closed_at=datetime.now(UTC))


def test_justified_absence_requires_a_note() -> None:
    with pytest.raises(InvalidAttendanceError):
        AttendanceMark(uuid4(), AttendanceStatus.EXCUSED)
