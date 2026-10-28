"""Contratos e casos de uso da agenda institucional."""

from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from backend.app.shared.application.request_context import RequestContext


class AgendaEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    event_type: str
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    all_day: bool = False
    location: str | None = Field(default=None, min_length=2, max_length=200)
    class_id: UUID | None = None
    assigned_to: UUID | None = None


class AgendaEventOutput(AgendaEventInput):
    id: UUID
    status: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class AgendaEventListOutput(BaseModel):
    items: list[AgendaEventOutput]


class AgendaRepository:
    async def list(
        self,
        starts_at: datetime,
        ends_at: datetime,
        event_type: str | None,
        assigned_to: UUID | None,
        context: RequestContext,
    ) -> list[AgendaEventOutput]:
        raise NotImplementedError

    async def create(self, payload: AgendaEventInput, context: RequestContext) -> AgendaEventOutput:
        raise NotImplementedError

    async def update(
        self,
        event_id: UUID,
        expected_updated_at: datetime,
        payload: AgendaEventInput,
        context: RequestContext,
    ) -> AgendaEventOutput:
        raise NotImplementedError

    async def cancel(
        self, event_id: UUID, expected_updated_at: datetime, reason: str, context: RequestContext
    ) -> AgendaEventOutput:
        raise NotImplementedError
