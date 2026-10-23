"""Contratos HTTP independentes das entidades do catálogo."""

from datetime import datetime, time
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from backend.app.modules.classes.domain.entities import Weekday


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ScheduleInput(DTO):
    weekday: Weekday
    starts_at: time
    ends_at: time


class CreateModalityInput(DTO):
    name: str = Field(min_length=3, max_length=80)
    description: str | None = Field(default=None, max_length=500)


class UpdateModalityInput(CreateModalityInput):
    expected_updated_at: AwareDatetime


class ChangeCatalogActivationInput(DTO):
    expected_updated_at: AwareDatetime
    reason: str = Field(min_length=10, max_length=500)


class CreateClassInput(DTO):
    modality_id: UUID
    name: str = Field(min_length=3, max_length=120)
    capacity: int = Field(ge=1, le=500)
    location: str = Field(min_length=2, max_length=120)
    minimum_age: int | None = Field(default=None, ge=0, le=120)
    maximum_age: int | None = Field(default=None, ge=0, le=120)
    schedules: list[ScheduleInput] = Field(min_length=1, max_length=14)
    instructor_ids: list[UUID] = Field(min_length=1, max_length=20)


class UpdateClassInput(CreateClassInput):
    expected_updated_at: AwareDatetime


class ModalityOutput(DTO):
    id: UUID
    name: str
    description: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class ModalityPageOutput(DTO):
    items: list[ModalityOutput]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_previous: bool
    has_next: bool


class ScheduleOutput(DTO):
    weekday: Weekday
    starts_at: time
    ends_at: time


class InstructorOutput(DTO):
    id: UUID
    full_name: str


class ClassOutput(DTO):
    id: UUID
    modality_id: UUID
    name: str
    capacity: int
    location: str
    minimum_age: int | None
    maximum_age: int | None
    schedules: list[ScheduleOutput]
    instructors: list[InstructorOutput]
    active: bool
    created_at: datetime
    updated_at: datetime


class ClassPageOutput(DTO):
    items: list[ClassOutput]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_previous: bool
    has_next: bool
