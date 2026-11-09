"""Contratos de entrada e saída da chamada."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.modules.attendance.domain.entities import AttendanceStatus


class AttendanceMarkInput(BaseModel):
    enrollment_id: UUID
    status: AttendanceStatus
    note: str | None = Field(default=None, max_length=500)


class OpenAttendanceInput(BaseModel):
    class_id: UUID
    session_date: date


class AttendanceSessionOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    class_id: UUID
    session_date: date
    status: str
    marks: tuple[AttendanceMarkInput, ...] = ()
    closed_at: datetime | None


class AttendanceSessionSummaryOutput(BaseModel):
    """Linha de uma sessão na listagem histórica, sem as marcas individuais."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    class_id: UUID
    session_date: date
    status: str
    closed_at: datetime | None


class AttendanceSessionPageOutput(BaseModel):
    items: tuple[AttendanceSessionSummaryOutput, ...]
    total: int


class AttendanceMonthlySummaryOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enrollment_id: UUID
    period: date
    total_sessions: int
    present_count: int
    absent_count: int
    justified_count: int


class AttendanceSummaryPageOutput(BaseModel):
    items: tuple[AttendanceMonthlySummaryOutput, ...]
