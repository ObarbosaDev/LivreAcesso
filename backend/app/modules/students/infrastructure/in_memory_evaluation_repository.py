"""Armazenamento local pequeno para desenvolvimento e testes."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from backend.app.modules.students.application.evaluation_dtos import (
    StudentEvaluationInput,
    StudentEvaluationOutput,
)
from backend.app.shared.application.request_context import RequestContext


class InMemoryStudentEvaluationRepository:
    def __init__(self) -> None:
        self._items: list[StudentEvaluationOutput] = []

    async def create(
        self, student_id: UUID, payload: StudentEvaluationInput, context: RequestContext
    ) -> StudentEvaluationOutput:
        now = datetime.now(UTC)
        item = StudentEvaluationOutput(
            id=uuid4(),
            student_id=student_id,
            evaluator_id=context.user.user_id,
            created_at=now,
            updated_at=now,
            **payload.model_dump(),
        )
        self._items.append(item)
        return item

    async def list(
        self, student_id: UUID, context: RequestContext
    ) -> list[StudentEvaluationOutput]:
        del context
        return [item for item in self._items if item.student_id == student_id]
