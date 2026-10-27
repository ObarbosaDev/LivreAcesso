"""DTOs de matrícula."""

from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict

from backend.app.modules.enrollments.domain.entities import EnrollmentStatus


class EnrollmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: UUID
    class_id: UUID


class EnrollmentStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_updated_at: AwareDatetime
    reason: str


class EnrollmentOutput(BaseModel):
    id: UUID
    student_id: UUID
    class_id: UUID
    status: EnrollmentStatus
    created_at: datetime
    updated_at: datetime


class EnrollmentPageOutput(BaseModel):
    """Página paginada para não carregar a turma inteira na API."""

    items: list[EnrollmentOutput]
    page: int
    page_size: int
    total: int
    total_pages: int


class EnrollmentOccupancyOutput(BaseModel):
    """Resumo leve para acompanhar vagas sem carregar a lista inteira."""

    class_id: UUID
    capacity: int
    enrolled: int
    available: int
