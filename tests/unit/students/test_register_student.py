"""Testes unitários do caso de uso de cadastro de aluno."""

import asyncio
from datetime import date

import pytest

from backend.app.modules.students.application.dtos import GuardianInput, RegisterStudentInput
from backend.app.modules.students.application.queries import StudentSearchCriteria
from backend.app.modules.students.application.use_cases import RegisterStudent
from backend.app.modules.students.domain.events import StudentRegistered
from backend.app.modules.students.domain.exceptions import DuplicateCPFError
from backend.app.modules.students.infrastructure.repositories import InMemoryStudentRepository
from backend.app.shared.application.event_bus import EventBus


def build_input() -> RegisterStudentInput:
    return RegisterStudentInput(
        full_name="Sophia Almeida Ramos",
        cpf="529.982.247-25",
        birth_date=date(2015, 5, 10),
        guardian=GuardianInput(
            full_name="Camila Ramos",
            phone="(61) 99999-1234",
            email="camila@example.com",
        ),
    )


def test_registers_student_and_publishes_domain_event() -> None:
    repository = InMemoryStudentRepository()
    event_bus = EventBus()
    recorded_events: list[StudentRegistered] = []
    event_bus.subscribe(StudentRegistered, recorded_events.append)
    use_case = RegisterStudent(repository, event_bus)

    output = asyncio.run(use_case.execute(build_input()))

    assert output.full_name == "Sophia Almeida Ramos"
    assert output.cpf_masked == "***.***.***-25"
    assert output.guardian_phone_masked == "(61) *****-1234"
    search_result = asyncio.run(repository.search(StudentSearchCriteria()))
    assert search_result.total == 1
    assert len(recorded_events) == 1
    assert recorded_events[0].student_id == output.id


def test_rejects_duplicate_cpf_even_with_different_formatting() -> None:
    repository = InMemoryStudentRepository()
    use_case = RegisterStudent(repository, EventBus())
    asyncio.run(use_case.execute(build_input()))

    duplicate = build_input().model_copy(update={"cpf": "52998224725"})

    with pytest.raises(DuplicateCPFError):
        asyncio.run(use_case.execute(duplicate))
