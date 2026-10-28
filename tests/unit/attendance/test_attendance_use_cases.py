"""Testes dos fluxos de aplicação da chamada."""

import asyncio
from datetime import date
from uuid import uuid4

from backend.app.modules.attendance.application.dtos import (
    AttendanceMarkInput,
    OpenAttendanceInput,
)
from backend.app.modules.attendance.application.use_cases import (
    CloseAttendance,
    OpenAttendance,
    RecordAttendance,
)
from backend.app.modules.attendance.domain.entities import AttendanceStatus
from backend.app.modules.attendance.infrastructure.repositories import (
    InMemoryAttendanceRepository,
)


def test_attendance_application_runs_open_record_close_flow() -> None:
    async def scenario() -> None:
        repository = InMemoryAttendanceRepository()
        opened = await OpenAttendance(repository).execute(
            OpenAttendanceInput(class_id=uuid4(), session_date=date(2026, 10, 27))
        )
        enrollment_id = uuid4()
        recorded = await RecordAttendance(repository).execute(
            opened.id,
            (AttendanceMarkInput(enrollment_id=enrollment_id, status=AttendanceStatus.PRESENT),),
        )
        closed = await CloseAttendance(repository).execute(recorded.id)

        assert closed.status == "fechada"
        assert closed.marks[0].enrollment_id == enrollment_id

    asyncio.run(scenario())
