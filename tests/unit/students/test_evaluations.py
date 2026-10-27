"""Cenários centrais do acompanhamento individual."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from backend.app.modules.identity.application.authentication import AccessToken, AuthenticatedUser
from backend.app.modules.students.application.evaluation_dtos import StudentEvaluationInput
from backend.app.modules.students.application.evaluation_use_cases import CreateStudentEvaluation
from backend.app.modules.students.infrastructure.in_memory_evaluation_repository import (
    InMemoryStudentEvaluationRepository,
)
from backend.app.shared.application.request_context import RequestContext


def _context() -> RequestContext:
    return RequestContext(
        request_id=uuid4(),
        user=AuthenticatedUser(uuid4(), AccessToken("token"), None, "aal1"),
    )


def _payload(**changes: object) -> StudentEvaluationInput:
    data: dict[str, object] = {
        "period_start": "2026-01-01",
        "period_end": "2026-01-31",
        "performance_score": 7,
        "evolution_score": 8,
        "interaction_score": 6,
        "participation_score": 7,
        "autonomy_score": 5,
        "wellbeing_score": 9,
        "support_level": "moderado",
        "observations": "Participou com segurança nas atividades propostas.",
        "effective_strategies": "Antecipação visual e instruções curtas funcionaram bem.",
        "next_objective": "Ampliar a autonomia na transição entre atividades.",
    }
    data.update(changes)
    return StudentEvaluationInput.model_validate(data)


def test_creates_and_lists_evaluation_without_comparing_student() -> None:
    async def scenario() -> None:
        repository = InMemoryStudentEvaluationRepository()
        student_id = uuid4()
        item = await CreateStudentEvaluation(repository).execute(
            student_id, _payload(), _context()
        )
        assert item.student_id == student_id
        assert item.performance_score == 7
        assert len(await repository.list(student_id, _context())) == 1

    asyncio.run(scenario())


def test_rejects_period_in_reverse_order() -> None:
    async def scenario() -> None:
        with pytest.raises(ValueError, match="fim do período"):
            await CreateStudentEvaluation(InMemoryStudentEvaluationRepository()).execute(
                uuid4(), _payload(period_start="2026-02-01"), _context()
            )

    asyncio.run(scenario())

