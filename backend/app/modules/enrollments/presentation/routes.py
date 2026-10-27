"""Endpoints do ciclo de matrícula."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from backend.app.core.container import ApplicationContainer
from backend.app.modules.enrollments.application.dtos import (
    EnrollmentInput,
    EnrollmentOutput,
    EnrollmentStatusInput,
)
from backend.app.modules.identity.presentation.dependencies import require_request_context
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.presentation.problem_details import ProblemDetail


def build_enrollments_router(container: ApplicationContainer) -> APIRouter:
    router = APIRouter(prefix="/enrollments", tags=["Matrículas"])
    responses: dict[int | str, dict[str, Any]] = {409: {"model": ProblemDetail}}

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
