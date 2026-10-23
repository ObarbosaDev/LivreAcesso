"""DTOs de entrada e saída do módulo de alunos."""

from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from backend.app.modules.students.domain.entities import GuardianRelationship, StudentStatus


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


class UpdateStudentInput(DTO):
    """Substitui somente dados do aluno; responsáveis têm endpoints versionados."""

    expected_updated_at: AwareDatetime = Field(
        description="Versão recebida na última consulta; evita sobrescrever outra alteração."
    )
    full_name: str = Field(min_length=3, max_length=120)
    birth_date: date

    @field_validator("birth_date")
    @classmethod
    def birth_date_must_be_in_the_past(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("A data de nascimento deve estar no passado.")
        return value


class ChangeStudentStatusInput(DTO):
    """Exige versão e justificativa para uma mudança cadastral de alto impacto."""

    expected_updated_at: AwareDatetime
    reason: str = Field(min_length=10, max_length=500)


class AddStudentGuardianInput(DTO):
    """Cria um contato ou reutiliza, por UUID, um responsável de outro aluno."""

    expected_student_updated_at: AwareDatetime
    relationship: GuardianRelationship
    receives_communications: bool = True
    make_primary: bool = False
    guardian: GuardianInput | None = None
    existing_guardian_id: UUID | None = None

    @model_validator(mode="after")
    def exactly_one_guardian_source(self) -> Self:
        # Separar criação de reutilização evita atualizar silenciosamente um
        # contato compartilhado quando o objetivo era apenas vinculá-lo a um irmão.
        if (self.guardian is None) == (self.existing_guardian_id is None):
            raise ValueError("Informe um novo responsável ou um UUID existente, mas não ambos.")
        return self


class UpdateStudentGuardianInput(DTO):
    """Atualiza contato compartilhado e propriedades deste vínculo com duas versões."""

    expected_student_updated_at: AwareDatetime
    expected_guardian_updated_at: AwareDatetime
    full_name: str = Field(min_length=3, max_length=120)
    phone: str = Field(min_length=10, max_length=20)
    email: EmailStr | None = None
    relationship: GuardianRelationship
    receives_communications: bool = True


class SetPrimaryGuardianInput(DTO):
    """Troca o principal usando a versão atual do agregado de aluno."""

    expected_student_updated_at: AwareDatetime


class UnlinkStudentGuardianInput(DTO):
    """Desativa o vínculo sem apagar responsável ou histórico."""

    expected_student_updated_at: AwareDatetime
    reason: str = Field(min_length=10, max_length=500)


class StudentOutput(DTO):
    """Representação mascarada para listagens e confirmações de cadastro."""

    id: UUID
    full_name: str
    cpf_masked: str
    birth_date: date
    age: int
    status: StudentStatus
    guardian_name: str | None
    guardian_phone_masked: str | None
    created_at: datetime
    updated_at: datetime


class GuardianDetailOutput(DTO):
    """Contato principal mantido no detalhe legado do aluno."""

    id: UUID
    full_name: str
    phone: str
    email: EmailStr | None


class StudentDetailOutput(DTO):
    """Cadastro completo autorizado; CPF continua mascarado e imutável."""

    id: UUID
    full_name: str
    cpf_masked: str
    birth_date: date
    age: int
    status: StudentStatus
    guardian: GuardianDetailOutput
    created_at: datetime
    updated_at: datetime


class StudentPageOutput(DTO):
    """Página com contexto suficiente para navegação previsível."""

    items: list[StudentOutput]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_previous: bool
    has_next: bool


class StudentGuardianListItemOutput(DTO):
    """Contato mascarado para escolha segura na interface."""

    id: UUID
    full_name: str
    phone_masked: str
    email_masked: str | None
    relationship: GuardianRelationship
    is_primary: bool
    receives_communications: bool
    linked_at: datetime
    guardian_updated_at: datetime


class StudentGuardianListOutput(DTO):
    """Coleção ativa e versão atual do aluno."""

    student_id: UUID
    student_updated_at: datetime
    items: list[StudentGuardianListItemOutput]


class StudentGuardianDetailOutput(DTO):
    """Contato integral cuja consulta é auditada no armazenamento remoto."""

    student_id: UUID
    student_updated_at: datetime
    id: UUID
    full_name: str
    phone: str
    email: EmailStr | None
    relationship: GuardianRelationship
    is_primary: bool
    receives_communications: bool
    linked_at: datetime
    guardian_updated_at: datetime


class StudentGuardianUnlinkOutput(DTO):
    """Confirma a desvinculação e devolve a nova versão do aluno."""

    student_id: UUID
    guardian_id: UUID
    student_updated_at: datetime
