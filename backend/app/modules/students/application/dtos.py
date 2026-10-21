"""DTOs de entrada e saída do módulo de alunos."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.app.modules.students.domain.entities import Modality, StudentStatus


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GuardianInput(DTO):
    full_name: str = Field(min_length=3, max_length=120)
    phone: str = Field(min_length=10, max_length=20)
    email: EmailStr | None = None


class RegisterStudentInput(DTO):
    full_name: str = Field(min_length=3, max_length=120)
    cpf: str = Field(min_length=11, max_length=14)
    birth_date: date
    modality: Modality
    status: StudentStatus = StudentStatus.ACTIVE
    guardian: GuardianInput

    @field_validator("birth_date")
    @classmethod
    def birth_date_must_be_in_the_past(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("A data de nascimento deve estar no passado.")
        return value


class StudentOutput(DTO):
    id: UUID
    full_name: str
    cpf_masked: str
    birth_date: date
    age: int
    modality: Modality
    status: StudentStatus
    guardian_name: str
    guardian_phone_masked: str
    created_at: datetime
