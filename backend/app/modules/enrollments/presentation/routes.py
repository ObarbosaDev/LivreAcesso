"""Endpoints do ciclo de matrícula."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from backend.app.core.container import ApplicationContainer
from backend.app.modules.enrollments.application.dtos import (
    EnrollmentInput,
    EnrollmentOccupancyOutput,
    EnrollmentOutput,
    EnrollmentPageOutput,
    EnrollmentStatusInput,
)
from backend.app.modules.identity.presentation.dependencies import require_request_context
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.presentation.problem_details import ProblemDetail


def build_enrollments_router(container: ApplicationContainer) -> APIRouter:
    router = APIRouter(prefix="/enrollments", tags=["Matrículas"])
    responses: dict[int | str, dict[str, Any]] = {409: {"model": ProblemDetail}}

    @router.get("", response_model=EnrollmentPageOutput)
    async def list_enrollments(
        context: Annotated[RequestContext, Depends(require_request_context)],
        student_id: UUID | None = None,
        class_id: UUID | None = None,
        status_filter: str | None = None,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=25, ge=1, le=100),
    ) -> EnrollmentPageOutput:
        return await container.enrollments_for(context).list.execute(
            student_id=student_id,
            class_id=class_id,
            status=status_filter,
            page=page,
            page_size=page_size,
        )

    @router.post(
        "",
        response_model=EnrollmentOutput,
        status_code=status.HTTP_201_CREATED,
        responses=responses,
    )
    async def create_enrollment(
        payload: EnrollmentInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> EnrollmentOutput:
        return await container.enrollments_for(context).create.execute(payload)

    @router.get("/occupancy/{class_id}", response_model=EnrollmentOccupancyOutput)
    async def enrollment_occupancy(
        class_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> EnrollmentOccupancyOutput:
        return await container.enrollments_for(context).occupancy.execute(class_id)

    @router.get(
        "/{enrollment_id}",
        response_model=EnrollmentOutput,
        responses={404: {"model": ProblemDetail}},
    )
    async def get_enrollment(
        enrollment_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> EnrollmentOutput:
        return await container.enrollments_for(context).get.execute(enrollment_id)

    @router.post("/{enrollment_id}/cancel", response_model=EnrollmentOutput, responses=responses)
    async def cancel_enrollment(
        enrollment_id: UUID,
        payload: EnrollmentStatusInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> EnrollmentOutput:
        return await container.enrollments_for(context).cancel.execute(enrollment_id, payload)

    @router.post(
        "/{enrollment_id}/reactivate", response_model=EnrollmentOutput, responses=responses
    )
    async def reactivate_enrollment(
        enrollment_id: UUID,
        payload: EnrollmentStatusInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> EnrollmentOutput:
        return await container.enrollments_for(context).reactivate.execute(enrollment_id, payload)

    return router
