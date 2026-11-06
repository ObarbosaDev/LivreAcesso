"""Testes da busca paginada de alunos."""

import asyncio
from datetime import date
from uuid import UUID, uuid4

import pytest

from backend.app.modules.students.application.dtos import GuardianInput, RegisterStudentInput
from backend.app.modules.students.application.queries import StudentSearchCriteria
from backend.app.modules.students.application.use_cases import (
    GetStudentNames,
    ListStudents,
    RegisterStudent,
)
from backend.app.modules.students.infrastructure.repositories import InMemoryStudentRepository
from backend.app.shared.application.event_bus import EventBus


def register(repository: InMemoryStudentRepository, *, name: str, cpf: str) -> UUID:
    output = asyncio.run(
        RegisterStudent(repository, EventBus()).execute(
            RegisterStudentInput(
                full_name=name,
                cpf=cpf,
                birth_date=date(2014, 4, 2),
                guardian=GuardianInput(
                    full_name="Responsável de Teste",
                    phone="(61) 99999-1234",
                ),
            )
        )
    )
    return output.id


def test_search_ignores_case_and_accents() -> None:
    repository = InMemoryStudentRepository()
    register(repository, name="João da Silva", cpf="52998224725")
    register(repository, name="Maria de Souza", cpf="11144477735")

    result = asyncio.run(ListStudents(repository).execute(query="JOAO"))

    assert result.total == 1
    assert result.items[0].full_name == "João da Silva"


def test_page_metadata_describes_navigation() -> None:
    repository = InMemoryStudentRepository()
    register(repository, name="Ana de Souza", cpf="52998224725")
    register(repository, name="Bruno de Souza", cpf="11144477735")

    first_page = asyncio.run(ListStudents(repository).execute(page=1, page_size=1))
    second_page = asyncio.run(ListStudents(repository).execute(page=2, page_size=1))

    assert first_page.total == 2
    assert first_page.total_pages == 2
    assert first_page.has_previous is False
    assert first_page.has_next is True
    assert second_page.has_previous is True
    assert second_page.has_next is False


@pytest.mark.parametrize(
    ("offset", "limit"),
    [(-1, 25), (0, 0), (0, 101)],
)
def test_repository_rejects_unbounded_pagination(offset: int, limit: int) -> None:
    with pytest.raises(ValueError):
        StudentSearchCriteria(offset=offset, limit=limit)


def test_get_student_names_resolves_only_known_ids() -> None:
    repository = InMemoryStudentRepository()
    joao_id = register(repository, name="João da Silva", cpf="52998224725")

    result = asyncio.run(GetStudentNames(repository).execute([joao_id, uuid4()]))

    assert result.names == {joao_id: "João da Silva"}
