"""Contratos de entrada e saída dos perfis operacionais."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from backend.app.modules.identity.domain.entities import Capability, UserRole


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AssignableRole(StrEnum):
    COORDINATOR = "coordenador"
    RECEPTIONIST = "recepcao"
    INSTRUCTOR = "instrutor"
    READ_ONLY = "consulta"


class UpdateMyProfileInput(DTO):
    expected_updated_at: AwareDatetime
    full_name: str = Field(min_length=3, max_length=120)


class ChangeProfileRoleInput(DTO):
    expected_updated_at: AwareDatetime
    role: AssignableRole
    reason: str = Field(min_length=10, max_length=500)


class ChangeProfileActivationInput(DTO):
    expected_updated_at: AwareDatetime
    reason: str = Field(min_length=10, max_length=500)


class InviteProfileInput(DTO):
    email: str = Field(min_length=5, max_length=320)
    full_name: str = Field(min_length=3, max_length=120)


class InviteProfileOutput(DTO):
    message: str


class ProfileOutput(DTO):
    id: UUID
    full_name: str
    role: UserRole
    active: bool
    capabilities: list[Capability]
    created_at: datetime
    updated_at: datetime


class ProfilePageOutput(DTO):
    items: list[ProfileOutput]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_previous: bool
    has_next: bool
