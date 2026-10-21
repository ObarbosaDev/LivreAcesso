"""Casos de uso do módulo de alunos."""

from dataclasses import dataclass

from backend.app.modules.students.application.dtos import (
    RegisterStudentInput,
    StudentOutput,
    StudentPageOutput,
)
from backend.app.modules.students.application.mappers import StudentMapper
from backend.app.modules.students.application.queries import (
    StudentQueryService,
    StudentSearchCriteria,
)
from backend.app.modules.students.domain.entities import StudentStatus
from backend.app.modules.students.domain.repositories import StudentRepository
from backend.app.shared.application.event_bus import EventPublisher


@dataclass(slots=True)
class RegisterStudent:
    """Cria um cadastro pessoal; matrícula em turma é outro caso de uso."""

    repository: StudentRepository
    event_publisher: EventPublisher

    def execute(self, dto: RegisterStudentInput) -> StudentOutput:
        student = StudentMapper.to_domain(dto)

        # Uma única operação de persistência reduz tráfego e deixa a constraint
        # única como autoridade contra concorrência, tanto em memória quanto no SQL.
        self.repository.add(student)

        # Eventos só saem após a persistência principal. Assim, listeners não
        # reagem a um cadastro que falhou antes de ser salvo.
        for event in student.pull_events():
            self.event_publisher.publish(event)

        return StudentMapper.to_output(student)


@dataclass(slots=True)
class ListStudents:
    """Busca projeções paginadas sem carregar dados pessoais integrais."""

    query_service: StudentQueryService

    def execute(
        self,
        *,
        status: StudentStatus | None = None,
        query: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> StudentPageOutput:
        criteria = StudentSearchCriteria(
            status=status,
            query=query,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        result = self.query_service.search(criteria)
        total_pages = (result.total + page_size - 1) // page_size if result.total else 0

        return StudentPageOutput(
            items=[StudentMapper.list_item_to_output(item) for item in result.items],
            page=page,
            page_size=page_size,
            total=result.total,
            total_pages=total_pages,
            has_previous=page > 1,
            has_next=page < total_pages,
        )
