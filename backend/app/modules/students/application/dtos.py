"""DTOs de entrada e saída do módulo de alunos."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.app.modules.students.domain.entities import StudentStatus


class DTO(BaseModel):
    """Contrato estrito que rejeita campos desconhecidos em vez de ignorá-los."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GuardianInput(DTO):
    full_name: str = Field(
        min_length=3,
        max_length=120,
        description="Nome completo do responsável ou contato responsável.",
    )
    phone: str = Field(
        min_length=10,
        max_length=20,
        description="Telefone brasileiro com DDD; pontuação é opcional.",
    )
    email: EmailStr | None = Field(
        default=None,
        description="E-mail do responsável, quando informado pela instituição.",
    )


class RegisterStudentInput(DTO):
    """Dados necessários somente para criar o cadastro pessoal do aluno."""

    full_name: str = Field(
        min_length=3,
        max_length=120,
        description="Nome completo do aluno.",
    )
    cpf: str = Field(
        min_length=11,
        max_length=14,
        description="CPF com ou sem pontuação; nunca deve ser enviado para logs.",
    )
    birth_date: date = Field(description="Data de nascimento no formato AAAA-MM-DD.")
    guardian: GuardianInput

    @field_validator("birth_date")
    @classmethod
    def birth_date_must_be_in_the_past(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("A data de nascimento deve estar no passado.")
        return value


class StudentOutput(DTO):
    """Representação segura para listagens e confirmações de cadastro."""

    id: UUID
    full_name: str
    cpf_masked: str
    birth_date: date
    age: int
    status: StudentStatus
    guardian_name: str | None
    guardian_phone_masked: str | None
    created_at: datetime


class StudentPageOutput(DTO):
    """Página com contexto suficiente para navegação previsível."""

    items: list[StudentOutput]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_previous: bool
    has_next: bool
