"""Endpoints do relatório pedagógico individual."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from backend.app.core.container import ApplicationContainer
from backend.app.modules.identity.presentation.dependencies import require_request_context
from backend.app.modules.students.application.evaluation_dtos import (
    StudentEvaluationInput,
    StudentEvaluationListOutput,
    StudentEvaluationOutput,
)
from backend.app.shared.application.request_context import RequestContext


def build_student_evaluations_router(container: ApplicationContainer) -> APIRouter:
    router = APIRouter(prefix="/students/{student_id}/evaluations", tags=["Avaliações"])

    @router.get("", response_model=StudentEvaluationListOutput)
    async def list_evaluations(
        student_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> StudentEvaluationListOutput:
        items = await container.evaluations_for(context).list.execute(student_id, context)
        return StudentEvaluationListOutput(items=items)

    @router.post("", response_model=StudentEvaluationOutput, status_code=status.HTTP_201_CREATED)
    async def create_evaluation(
        student_id: UUID,
        payload: StudentEvaluationInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> StudentEvaluationOutput:
        return await container.evaluations_for(context).create.execute(student_id, payload, context)

    return router
