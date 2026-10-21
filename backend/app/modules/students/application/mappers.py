"""Conversões explícitas entre DTOs e objetos de domínio."""

from backend.app.modules.students.application.dtos import (
    RegisterStudentInput,
    StudentOutput,
)
from backend.app.modules.students.domain.entities import Guardian, Student
from backend.app.modules.students.domain.value_objects import CPF, Phone


class StudentMapper:
    @staticmethod
    def to_domain(dto: RegisterStudentInput) -> Student:
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
            modality=dto.modality,
            status=dto.status,
        )

    @staticmethod
    def to_output(student: Student) -> StudentOutput:
        return StudentOutput(
            id=student.id,
            full_name=student.full_name,
            cpf_masked=student.cpf.masked,
            birth_date=student.birth_date,
            age=student.age_on(),
            modality=student.modality,
            status=student.status,
            guardian_name=student.guardian.full_name,
            guardian_phone_masked=student.guardian.phone.masked,
            created_at=student.created_at,
        )
