"""Endpoints protegidos da chamada e frequência."""

import hmac
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from backend.app.core.config import Settings
from backend.app.core.container import ApplicationContainer
from backend.app.modules.attendance.application.dtos import (
    AttendanceMarkInput,
    AttendanceSessionOutput,
    AttendanceSessionPageOutput,
    AttendanceSummaryPageOutput,
    OpenAttendanceInput,
)
from backend.app.modules.identity.presentation.dependencies import require_request_context
from backend.app.shared.application.request_context import RequestContext


def build_attendance_router(container: ApplicationContainer, settings: Settings) -> APIRouter:
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

    @router.get("/sessions", response_model=AttendanceSessionPageOutput)
    async def list_sessions(
        class_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
        limit: int = Query(default=60, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> AttendanceSessionPageOutput:
        return await container.attendance_for(context).list_sessions(
            class_id, limit=limit, offset=offset
        )

    @router.get("/sessions/{session_id}/marks", response_model=tuple[AttendanceMarkInput, ...])
    async def session_marks(
        session_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> tuple[AttendanceMarkInput, ...]:
        return await container.attendance_for(context).session_marks(session_id)

    @router.get("/summary", response_model=AttendanceSummaryPageOutput)
    async def summary(
        class_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> AttendanceSummaryPageOutput:
        return await container.attendance_for(context).summary(class_id)

    @router.get("/archive", include_in_schema=False)
    async def archive_old_sessions(
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, int]:
        """Disparado pelo cron do Vercel; nunca pelo app do usuário.

        Compara em tempo constante contra CRON_SECRET para evitar oráculo de timing.
        """
        expected = settings.cron_secret
        provided = authorization.removeprefix("Bearer ").strip() if authorization else ""
        if not expected or not hmac.compare_digest(provided, expected):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        archived = await container.attendance_archiver().archive_old_sessions()
        return {"archived_periods": archived}

    return router
