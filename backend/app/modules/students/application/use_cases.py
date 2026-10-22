"""Casos de uso do módulo de alunos."""

from dataclasses import dataclass
from uuid import UUID

from backend.app.modules.students.application.dtos import (
    ChangeStudentStatusInput,
    RegisterStudentInput,
    StudentDetailOutput,
    StudentOutput,
    StudentPageOutput,
    UpdateStudentInput,
)
from backend.app.modules.students.application.mappers import StudentMapper
from backend.app.modules.students.application.queries import (
    StudentQueryService,
    StudentSearchCriteria,
)
from backend.app.modules.students.domain.entities import Guardian, Student, StudentStatus
from backend.app.modules.students.domain.exceptions import (
    StudentNotFoundError,
    StudentVersionConflictError,
)
from backend.app.modules.students.domain.repositories import StudentRepository
from backend.app.modules.students.domain.value_objects import Phone, StatusChangeReason
from backend.app.shared.application.event_bus import EventPublisher


def _publish_pending_events(student: Student, publisher: EventPublisher) -> None:
    # Publicação ocorre somente após persistência. Um evento nunca deve anunciar
    # uma alteração que o armazenamento recusou por versão ou permissão.
    for event in student.pull_events():
        publisher.publish(event)


@dataclass(slots=True)
class RegisterStudent:
    """Cria um cadastro pessoal; matrícula em turma é outro caso de uso."""

    repository: StudentRepository
    event_publisher: EventPublisher

    async def execute(self, dto: RegisterStudentInput) -> StudentOutput:
        student = StudentMapper.to_domain(dto)

        # Uma única operação de persistência reduz tráfego e deixa a constraint
        # única como autoridade contra concorrência, tanto em memória quanto no SQL.
        await self.repository.add(student)
        _publish_pending_events(student, self.event_publisher)
        return StudentMapper.to_output(student)


@dataclass(slots=True)
class GetStudent:
    """Obtém o detalhe autorizado; o adaptador remoto audita a leitura sensível."""

    repository: StudentRepository

    async def execute(self, student_id: UUID) -> StudentDetailOutput:
        student = await self.repository.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError
        return StudentMapper.to_detail_output(student)


@dataclass(slots=True)
class UpdateStudent:
    """Atualiza dados pessoais sem permitir alteração implícita de CPF ou status."""

    repository: StudentRepository
    event_publisher: EventPublisher

    async def execute(self, student_id: UUID, dto: UpdateStudentInput) -> StudentDetailOutput:
        student = await self.repository.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError
        if student.updated_at != dto.expected_updated_at:
            raise StudentVersionConflictError

        guardian = Guardian(
            id=student.guardian.id,
            full_name=dto.guardian.full_name,
            phone=Phone(dto.guardian.phone),
            email=str(dto.guardian.email) if dto.guardian.email else None,
        )
        changed_fields = student.update_personal_data(
            full_name=dto.full_name,
            birth_date=dto.birth_date,
            guardian=guardian,
        )

        if changed_fields:
            updated_at = await self.repository.update(
                student,
                expected_updated_at=dto.expected_updated_at,
            )
            student.mark_persisted(updated_at)
            _publish_pending_events(student, self.event_publisher)

        return StudentMapper.to_detail_output(student)


@dataclass(slots=True)
class ChangeStudentStatus:
    """Executa transição explícita com motivo e concorrência otimista."""

    repository: StudentRepository
    event_publisher: EventPublisher
    target_status: StudentStatus

    async def execute(
        self,
        student_id: UUID,
        dto: ChangeStudentStatusInput,
    ) -> StudentDetailOutput:
        student = await self.repository.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError
        if student.updated_at != dto.expected_updated_at:
            raise StudentVersionConflictError

        reason = StatusChangeReason(dto.reason)
        changed = student.change_status(self.target_status, reason)
        if changed:
            updated_at = await self.repository.change_status(
                student,
                reason=reason,
                expected_updated_at=dto.expected_updated_at,
            )
            student.mark_persisted(updated_at)
            _publish_pending_events(student, self.event_publisher)

        return StudentMapper.to_detail_output(student)


@dataclass(slots=True)
class ListStudents:
    """Busca projeções paginadas sem carregar dados pessoais integrais."""

    query_service: StudentQueryService

    async def execute(
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
        result = await self.query_service.search(criteria)
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
