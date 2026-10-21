"""Conversões explícitas entre DTOs e objetos de domínio."""

from backend.app.modules.students.application.dtos import (
    RegisterStudentInput,
    StudentOutput,
)
from backend.app.modules.students.application.queries import StudentListItem
from backend.app.modules.students.domain.entities import Guardian, Student
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
        )
