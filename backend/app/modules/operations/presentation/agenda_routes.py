"""Endpoints da agenda institucional."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from backend.app.core.container import ApplicationContainer
from backend.app.modules.identity.presentation.dependencies import require_request_context
from backend.app.modules.operations.application.agenda import (
    AgendaEventInput,
    AgendaEventListOutput,
    AgendaEventOutput,
)
from backend.app.shared.application.request_context import RequestContext


def build_agenda_router(container: ApplicationContainer) -> APIRouter:
    router = APIRouter(prefix="/agenda", tags=["Agenda"])

    @router.get("", response_model=AgendaEventListOutput)
    async def list_agenda(
        context: Annotated[RequestContext, Depends(require_request_context)],
        start: datetime,
        end: datetime,
        event_type: str | None = None,
        assigned_to: UUID | None = None,
    ) -> AgendaEventListOutput:
        items = await container.agenda_for(context).list(
            start, end, event_type, assigned_to, context
        )
        return AgendaEventListOutput(items=items)

    @router.post("", response_model=AgendaEventOutput, status_code=status.HTTP_201_CREATED)
    async def create_agenda(
        payload: AgendaEventInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> AgendaEventOutput:
        return await container.agenda_for(context).create(payload, context)

    return router
