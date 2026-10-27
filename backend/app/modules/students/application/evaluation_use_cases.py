"""Casos de uso do relatório de acompanhamento individual."""

from dataclasses import dataclass
from uuid import UUID

from backend.app.modules.students.application.evaluation_dtos import (
    StudentEvaluationInput,
    StudentEvaluationOutput,
)
from backend.app.modules.students.domain.evaluation_repositories import (
    StudentEvaluationRepository,
)
from backend.app.shared.application.request_context import RequestContext


@dataclass(slots=True)
class CreateStudentEvaluation:
    repository: StudentEvaluationRepository

    async def execute(
        self, student_id: UUID, payload: StudentEvaluationInput, context: RequestContext
    ) -> StudentEvaluationOutput:
        if payload.period_end < payload.period_start:
            raise ValueError("O fim do período deve ser posterior ao início.")
        return await self.repository.create(student_id, payload, context)


@dataclass(slots=True)
class ListStudentEvaluations:
    repository: StudentEvaluationRepository

    async def execute(
        self, student_id: UUID, context: RequestContext
    ) -> list[StudentEvaluationOutput]:
        return await self.repository.list(student_id, context)
