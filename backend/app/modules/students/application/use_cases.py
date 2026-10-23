"""Casos de uso do módulo de alunos."""

from dataclasses import dataclass
from uuid import UUID

from backend.app.modules.students.application.dtos import (
    AddStudentGuardianInput,
    ChangeStudentStatusInput,
    RegisterStudentInput,
    SetPrimaryGuardianInput,
    StudentDetailOutput,
    StudentGuardianDetailOutput,
    StudentGuardianListOutput,
    StudentGuardianUnlinkOutput,
    StudentOutput,
    StudentPageOutput,
    UnlinkStudentGuardianInput,
    UpdateStudentGuardianInput,
    UpdateStudentInput,
)
from backend.app.modules.students.application.mappers import StudentMapper
from backend.app.modules.students.application.queries import (
    StudentGuardianQueryService,
    StudentQueryService,
    StudentSearchCriteria,
)
from backend.app.modules.students.domain.entities import Guardian, Student, StudentStatus
from backend.app.modules.students.domain.events import (
    StudentGuardianLinked,
    StudentGuardianUnlinked,
    StudentGuardianUpdated,
    StudentPrimaryGuardianChanged,
)
from backend.app.modules.students.domain.exceptions import (
    StudentNotFoundError,
    StudentVersionConflictError,
)
from backend.app.modules.students.domain.repositories import (
    StudentGuardianRepository,
    StudentRepository,
)
from backend.app.modules.students.domain.value_objects import (
    GuardianUnlinkReason,
    Phone,
    StatusChangeReason,
)
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
        persisted_version = await self.repository.add(student)
        student.mark_created(
            persisted_version.created_at,
            persisted_version.updated_at,
        )
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
    """Atualiza o aluno sem alterar implicitamente CPF, status ou responsáveis."""

    repository: StudentRepository
    event_publisher: EventPublisher

    async def execute(self, student_id: UUID, dto: UpdateStudentInput) -> StudentDetailOutput:
        student = await self.repository.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError
        if student.updated_at != dto.expected_updated_at:
            raise StudentVersionConflictError

        changed_fields = student.update_personal_data(
            full_name=dto.full_name,
            birth_date=dto.birth_date,
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


@dataclass(slots=True)
class ListStudentGuardians:
    """Lista contatos ativos com telefone e e-mail mascarados."""

    query_service: StudentGuardianQueryService

    async def execute(self, student_id: UUID) -> StudentGuardianListOutput:
        result = await self.query_service.list_guardians(student_id)
        return StudentMapper.guardian_list_to_output(result)


@dataclass(slots=True)
class GetStudentGuardian:
    """Obtém contato integral; a implementação Supabase audita esta leitura."""

    repository: StudentGuardianRepository

    async def execute(self, student_id: UUID, guardian_id: UUID) -> StudentGuardianDetailOutput:
        snapshot = await self.repository.get_guardian(student_id, guardian_id)
        return StudentMapper.guardian_snapshot_to_output(snapshot)


@dataclass(slots=True)
class AddStudentGuardian:
    """Inclui contato novo ou revincula um responsável compartilhado."""

    repository: StudentGuardianRepository
    event_publisher: EventPublisher

    async def execute(
        self,
        student_id: UUID,
        dto: AddStudentGuardianInput,
    ) -> StudentGuardianDetailOutput:
        guardian = None
        if dto.guardian is not None:
            guardian = Guardian(
                full_name=dto.guardian.full_name,
                phone=Phone(dto.guardian.phone),
                email=str(dto.guardian.email) if dto.guardian.email else None,
            )

        result = await self.repository.add_guardian(
            student_id,
            guardian=guardian,
            existing_guardian_id=dto.existing_guardian_id,
            relationship=dto.relationship,
            make_primary=dto.make_primary,
            receives_communications=dto.receives_communications,
            expected_student_updated_at=dto.expected_student_updated_at,
        )
        if result.changed:
            self.event_publisher.publish(
                StudentGuardianLinked(
                    student_id=student_id,
                    guardian_id=result.snapshot.link.guardian.id,
                )
            )
        return StudentMapper.guardian_snapshot_to_output(result.snapshot)


@dataclass(slots=True)
class UpdateStudentGuardian:
    """Atualiza contato e vínculo sem aceitar versões obsoletas."""

    repository: StudentGuardianRepository
    event_publisher: EventPublisher

    async def execute(
        self,
        student_id: UUID,
        guardian_id: UUID,
        dto: UpdateStudentGuardianInput,
    ) -> StudentGuardianDetailOutput:
        guardian = Guardian(
            id=guardian_id,
            full_name=dto.full_name,
            phone=Phone(dto.phone),
            email=str(dto.email) if dto.email else None,
        )
        result = await self.repository.update_guardian(
            student_id,
            guardian,
            relationship=dto.relationship,
            receives_communications=dto.receives_communications,
            expected_student_updated_at=dto.expected_student_updated_at,
            expected_guardian_updated_at=dto.expected_guardian_updated_at,
        )
        if result.changed:
            self.event_publisher.publish(
                StudentGuardianUpdated(student_id=student_id, guardian_id=guardian_id)
            )
        return StudentMapper.guardian_snapshot_to_output(result.snapshot)


@dataclass(slots=True)
class SetPrimaryGuardian:
    """Promove um vínculo ativo e rebaixa o principal anterior atomicamente."""

    repository: StudentGuardianRepository
    event_publisher: EventPublisher

    async def execute(
        self,
        student_id: UUID,
        guardian_id: UUID,
        dto: SetPrimaryGuardianInput,
    ) -> StudentGuardianDetailOutput:
        result = await self.repository.set_primary_guardian(
            student_id,
            guardian_id,
            expected_student_updated_at=dto.expected_student_updated_at,
        )
        if result.changed:
            self.event_publisher.publish(
                StudentPrimaryGuardianChanged(student_id=student_id, guardian_id=guardian_id)
            )
        return StudentMapper.guardian_snapshot_to_output(result.snapshot)


@dataclass(slots=True)
class UnlinkStudentGuardian:
    """Desativa apenas vínculo não principal e preserva a justificativa privada."""

    repository: StudentGuardianRepository
    event_publisher: EventPublisher

    async def execute(
        self,
        student_id: UUID,
        guardian_id: UUID,
        dto: UnlinkStudentGuardianInput,
    ) -> StudentGuardianUnlinkOutput:
        result = await self.repository.unlink_guardian(
            student_id,
            guardian_id,
            reason=GuardianUnlinkReason(dto.reason),
            expected_student_updated_at=dto.expected_student_updated_at,
        )
        if result.changed:
            self.event_publisher.publish(
                StudentGuardianUnlinked(student_id=student_id, guardian_id=guardian_id)
            )
        return StudentGuardianUnlinkOutput(
            student_id=result.student_id,
            guardian_id=result.guardian_id,
            student_updated_at=result.student_updated_at,
        )
