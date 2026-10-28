"""Endpoints protegidos da lista de espera."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from backend.app.core.container import ApplicationContainer
from backend.app.modules.identity.presentation.dependencies import require_request_context
from backend.app.modules.waiting_list.application.dtos import (
    WaitingListInput,
    WaitingListOutput,
)
from backend.app.shared.application.request_context import RequestContext


def build_waiting_list_router(container: ApplicationContainer) -> APIRouter:
    router = APIRouter(prefix="/waiting-list", tags=["Lista de espera"])

    @router.post("", response_model=WaitingListOutput, status_code=status.HTTP_201_CREATED)
    async def join_waiting_list(
        payload: WaitingListInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> WaitingListOutput:
        return await container.waiting_list_for(context).join(payload)

    @router.post("/{entry_id}/offer", response_model=WaitingListOutput)
    async def offer_waiting_list(
        entry_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> WaitingListOutput:
        return await container.waiting_list_for(context).offer(entry_id)

    @router.post("/{entry_id}/accept", response_model=WaitingListOutput)
    async def accept_waiting_list(
        entry_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> WaitingListOutput:
        return await container.waiting_list_for(context).accept(entry_id)

    @router.get("", response_model=tuple[WaitingListOutput, ...])
    async def list_waiting_list(
        class_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> tuple[WaitingListOutput, ...]:
        return await container.waiting_list_for(context).list(class_id)

    @router.post("/{entry_id}/withdraw", response_model=WaitingListOutput)
    async def withdraw_waiting_list(
        entry_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> WaitingListOutput:
        return await container.waiting_list_for(context).withdraw(entry_id)

    return router
