"""Endpoints protegidos da chamada e frequência."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from backend.app.core.container import ApplicationContainer
from backend.app.modules.attendance.application.dtos import (
    AttendanceMarkInput,
    AttendanceSessionOutput,
    OpenAttendanceInput,
)
from backend.app.modules.identity.presentation.dependencies import require_request_context
from backend.app.shared.application.request_context import RequestContext


def build_attendance_router(container: ApplicationContainer) -> APIRouter:
    router = APIRouter(prefix="/attendance", tags=["Frequência"])

    @router.post(
        "/sessions",
        response_model=AttendanceSessionOutput,
        status_code=status.HTTP_201_CREATED,
    )
    async def open_session(
        payload: OpenAttendanceInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> AttendanceSessionOutput:
        return await container.attendance_for(context).open(payload)

    @router.put("/sessions/{session_id}/marks", response_model=AttendanceSessionOutput)
    async def record_marks(
        session_id: UUID,
        payload: tuple[AttendanceMarkInput, ...],
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> AttendanceSessionOutput:
        return await container.attendance_for(context).record(session_id, payload)

    @router.post("/sessions/{session_id}/close", response_model=AttendanceSessionOutput)
    async def close_session(
        session_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> AttendanceSessionOutput:
        return await container.attendance_for(context).close(session_id)

    return router
