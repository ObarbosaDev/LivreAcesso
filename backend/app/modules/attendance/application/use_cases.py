"""Casos de uso transacionais da chamada."""

from datetime import UTC, datetime
from uuid import UUID

from backend.app.modules.attendance.application.dtos import (
    AttendanceMarkInput,
    AttendanceSessionOutput,
    OpenAttendanceInput,
)
from backend.app.modules.attendance.domain.entities import AttendanceMark, AttendanceSession
from backend.app.modules.attendance.domain.exceptions import AttendanceDomainError
from backend.app.modules.attendance.domain.repositories import AttendanceRepository


def _output(session: AttendanceSession) -> AttendanceSessionOutput:
    return AttendanceSessionOutput(
        id=session.id,
        class_id=session.class_id,
        session_date=session.session_date,
        status=session.status.value,
        marks=tuple(
            AttendanceMarkInput(
                enrollment_id=mark.enrollment_id,
                status=mark.status,
                note=mark.note,
            )
            for mark in session.marks.values()
        ),
        closed_at=session.closed_at,
    )


class OpenAttendance:
    def __init__(self, repository: AttendanceRepository) -> None:
        self.repository = repository

    async def execute(self, payload: OpenAttendanceInput) -> AttendanceSessionOutput:
        session = AttendanceSession.open(
            class_id=payload.class_id,
            session_date=payload.session_date,
        )
        return _output(await self.repository.add(session))


class RecordAttendance:
    def __init__(self, repository: AttendanceRepository) -> None:
        self.repository = repository

    async def execute(
        self, session_id: UUID, marks: tuple[AttendanceMarkInput, ...]
    ) -> AttendanceSessionOutput:
        session = await self.repository.get(session_id)
        if session is None:
            raise AttendanceDomainError("Sessão de chamada não encontrada.")
        session.record(
            tuple(
                AttendanceMark(
                    enrollment_id=mark.enrollment_id,
                    status=mark.status,
                    note=mark.note,
                )
                for mark in marks
            )
        )
        return _output(await self.repository.update(session))


class CloseAttendance:
    def __init__(self, repository: AttendanceRepository) -> None:
        self.repository = repository

    async def execute(self, session_id: UUID) -> AttendanceSessionOutput:
        session = await self.repository.get(session_id)
        if session is None:
            raise AttendanceDomainError("Sessão de chamada não encontrada.")
        session.close(closed_at=datetime.now(UTC))
        return _output(await self.repository.update(session))
