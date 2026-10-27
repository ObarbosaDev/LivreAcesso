"""Porta de persistência das avaliações individuais."""

from typing import Protocol
from uuid import UUID

from backend.app.modules.students.application.evaluation_dtos import (
    StudentEvaluationInput,
    StudentEvaluationOutput,
)
from backend.app.shared.application.request_context import RequestContext


class StudentEvaluationRepository(Protocol):
    async def create(
        self,
        student_id: UUID,
        payload: StudentEvaluationInput,
        context: RequestContext,
    ) -> StudentEvaluationOutput: ...

    async def list(
        self, student_id: UUID, context: RequestContext
    ) -> list[StudentEvaluationOutput]: ...
