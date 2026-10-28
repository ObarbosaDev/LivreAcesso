"""Endpoints de acompanhamento de frequência."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from backend.app.core.container import ApplicationContainer
from backend.app.modules.alerts.application.dtos import AlertInput, AlertOutput
from backend.app.modules.identity.presentation.dependencies import require_request_context
from backend.app.shared.application.request_context import RequestContext


def build_alerts_router(container: ApplicationContainer) -> APIRouter:
    router = APIRouter(prefix="/alerts", tags=["Alertas"])

    @router.get("", response_model=tuple[AlertOutput, ...])
    async def list_alerts(
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> tuple[AlertOutput, ...]:
        return await container.alerts_for(context).list_open()

    @router.post("", response_model=AlertOutput)
    async def create_alert(
        payload: AlertInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> AlertOutput:
        return await container.alerts_for(context).upsert(payload)

    @router.post("/{alert_id}/resolve", response_model=AlertOutput)
    async def resolve_alert(
        alert_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> AlertOutput:
        return await container.alerts_for(context).resolve(alert_id)

    return router
