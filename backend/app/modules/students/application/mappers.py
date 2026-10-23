"""Conversões explícitas entre DTOs e objetos de domínio."""

from backend.app.modules.students.application.dtos import (
    GuardianDetailOutput,
    RegisterStudentInput,
    StudentDetailOutput,
    StudentGuardianDetailOutput,
    StudentGuardianListItemOutput,
    StudentGuardianListOutput,
    StudentOutput,
)
from backend.app.modules.students.application.queries import (
    StudentGuardianListItem,
    StudentGuardianListResult,
    StudentListItem,
)
from backend.app.modules.students.domain.entities import Guardian, Student
from backend.app.modules.students.domain.repositories import StudentGuardianSnapshot
from backend.app.modules.students.domain.value_objects import CPF, Phone


class StudentMapper:
    """Mantém detalhes de transporte fora das entidades de domínio."""

    @staticmethod
    def to_domain(dto: RegisterStudentInput) -> Student:
        # A conversão cria value objects antes da entidade para que CPF e telefone
        # inválidos nunca alcancem o repositório ou sejam publicados em eventos.
        guardian = Guardian(
            full_name=dto.guardian.full_name,
            phone=Phone(dto.guardian.phone),
            email=str(dto.guardian.email) if dto.guardian.email else None,
        )
        return Student.register(
            full_name=dto.full_name,
            cpf=CPF(dto.cpf),
            birth_date=dto.birth_date,
            guardian=guardian,
        )

    @staticmethod
    def to_output(student: Student) -> StudentOutput:
        # Confirmações de escrita também são mascaradas; nem mesmo a criação
        # devolve CPF ou telefone completos para o cliente.
        return StudentOutput(
            id=student.id,
            full_name=student.full_name,
            cpf_masked=student.cpf.masked,
            birth_date=student.birth_date,
            age=student.age_on(),
            status=student.status,
            guardian_name=student.guardian.full_name,
            guardian_phone_masked=student.guardian.phone.masked,
            created_at=student.created_at,
            updated_at=student.updated_at,
        )

    @staticmethod
    def to_detail_output(student: Student) -> StudentDetailOutput:
        # Telefone e e-mail integrais aparecem somente neste contrato protegido.
        # CPF permanece mascarado porque não é necessário para a rotina comum.
        return StudentDetailOutput(
            id=student.id,
            full_name=student.full_name,
            cpf_masked=student.cpf.masked,
            birth_date=student.birth_date,
            age=student.age_on(),
            status=student.status,
            guardian=GuardianDetailOutput(
                id=student.guardian.id,
                full_name=student.guardian.full_name,
                phone=student.guardian.phone.value,
                email=student.guardian.email,
            ),
            created_at=student.created_at,
            updated_at=student.updated_at,
        )

    @staticmethod
    def list_item_to_output(item: StudentListItem) -> StudentOutput:
        """Converte projeção segura sem inventar uma entidade de domínio."""

        return StudentOutput(
            id=item.id,
            full_name=item.full_name,
            cpf_masked=item.cpf_masked,
            birth_date=item.birth_date,
            age=item.age,
            status=item.status,
            guardian_name=item.guardian_name,
            guardian_phone_masked=item.guardian_phone_masked,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @staticmethod
    def guardian_list_to_output(result: StudentGuardianListResult) -> StudentGuardianListOutput:
        return StudentGuardianListOutput(
            student_id=result.student_id,
            student_updated_at=result.student_updated_at,
            items=[StudentMapper.guardian_list_item_to_output(item) for item in result.items],
        )

    @staticmethod
    def guardian_list_item_to_output(
        item: StudentGuardianListItem,
    ) -> StudentGuardianListItemOutput:
        return StudentGuardianListItemOutput(
            id=item.id,
            full_name=item.full_name,
            phone_masked=item.phone_masked,
            email_masked=item.email_masked,
            relationship=item.relationship,
            is_primary=item.is_primary,
            receives_communications=item.receives_communications,
            linked_at=item.linked_at,
            guardian_updated_at=item.guardian_updated_at,
        )

    @staticmethod
    def guardian_snapshot_to_output(
        snapshot: StudentGuardianSnapshot,
    ) -> StudentGuardianDetailOutput:
        link = snapshot.link
        return StudentGuardianDetailOutput(
            student_id=link.student_id,
            student_updated_at=snapshot.student_updated_at,
            id=link.guardian.id,
            full_name=link.guardian.full_name,
            phone=link.guardian.phone.value,
            email=link.guardian.email,
            relationship=link.relationship,
            is_primary=link.is_primary,
            receives_communications=link.receives_communications,
            linked_at=link.linked_at,
            guardian_updated_at=link.guardian_updated_at,
        )
