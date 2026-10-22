"""Entidades e agregado do contexto de alunos."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from backend.app.modules.students.domain.events import (
    StudentRegistered,
    StudentStatusChanged,
    StudentUpdated,
)
from backend.app.modules.students.domain.exceptions import InvalidStudentDataError
from backend.app.modules.students.domain.value_objects import CPF, Phone, StatusChangeReason
from backend.app.shared.domain.events import DomainEvent


class StudentStatus(StrEnum):
    """Ciclo cadastral do aluno, independente de suas matrículas."""

    ACTIVE = "ativo"
    INACTIVE = "inativo"


def _normalize_student_data(full_name: str, birth_date: date) -> str:
    normalized_name = " ".join(full_name.split())
    today = date.today()

    if len(normalized_name) < 3:
        raise InvalidStudentDataError("Informe o nome completo do aluno.")
    if birth_date >= today:
        raise InvalidStudentDataError("A data de nascimento deve estar no passado.")
    if birth_date.year < today.year - 120:
        raise InvalidStudentDataError("A data de nascimento informada é inválida.")
    return normalized_name


@dataclass(frozen=True, slots=True)
class Guardian:
    """Responsável legal ou contato responsável pelo participante."""

    full_name: str
    phone: Phone
    email: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        normalized_name = " ".join(self.full_name.split())
        if len(normalized_name) < 3:
            raise InvalidStudentDataError("Informe o nome completo do responsável.")

        # E-mail e telefone são dados pessoais. A entidade apenas os normaliza;
        # apresentação, logs e auditoria decidem quando devem ser mascarados.
        normalized_email = self.email.strip().lower() if self.email else None
        object.__setattr__(self, "full_name", normalized_name)
        object.__setattr__(self, "email", normalized_email)


@dataclass(slots=True)
class Student:
    """Agregado raiz que protege as regras cadastrais do aluno."""

    id: UUID
    full_name: str
    cpf: CPF
    birth_date: date
    guardian: Guardian
    status: StudentStatus = StudentStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _events: list[DomainEvent] = field(
        default_factory=list,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        self.full_name = _normalize_student_data(self.full_name, self.birth_date)
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise InvalidStudentDataError("Datas de auditoria precisam informar o fuso horário.")

    @classmethod
    def register(
        cls,
        *,
        full_name: str,
        cpf: CPF,
        birth_date: date,
        guardian: Guardian,
    ) -> "Student":
        # O status inicial pertence ao ciclo do domínio e não ao payload HTTP.
        # Dessa forma, nenhum cliente consegue criar um cadastro já inativo.
        now = datetime.now(UTC)
        student = cls(
            id=uuid4(),
            full_name=full_name,
            cpf=cpf,
            birth_date=birth_date,
            guardian=guardian,
            status=StudentStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        student._events.append(StudentRegistered(student_id=student.id))
        return student

    def update_personal_data(
        self,
        *,
        full_name: str,
        birth_date: date,
        guardian: Guardian,
    ) -> tuple[str, ...]:
        """Altera dados editáveis e informa campos, nunca valores, no evento."""

        normalized_name = _normalize_student_data(full_name, birth_date)
        changed_fields: list[str] = []

        if self.full_name != normalized_name:
            self.full_name = normalized_name
            changed_fields.append("full_name")
        if self.birth_date != birth_date:
            self.birth_date = birth_date
            changed_fields.append("birth_date")
        if self.guardian != guardian:
            self.guardian = guardian
            changed_fields.append("guardian")

        result = tuple(changed_fields)
        if result:
            self._events.append(StudentUpdated(student_id=self.id, changed_fields=result))
        return result

    def change_status(
        self,
        target_status: StudentStatus,
        reason: StatusChangeReason,
    ) -> bool:
        """Muda o ciclo cadastral sem usar ausência ou inatividade como decisão automática."""

        if self.status is target_status:
            return False

        previous_status = self.status
        self.status = target_status
        # O motivo pode descrever situação familiar ou pessoal. Ele segue para a
        # tabela de histórico protegida, não para o evento distribuído/outbox.
        del reason
        self._events.append(
            StudentStatusChanged(
                student_id=self.id,
                previous_status=previous_status.value,
                current_status=target_status.value,
            )
        )
        return True

    def mark_created(self, created_at: datetime, updated_at: datetime) -> None:
        """Sincroniza os timestamps autoritativos após o primeiro insert."""

        if created_at.tzinfo is None or updated_at.tzinfo is None:
            raise InvalidStudentDataError("Datas persistidas precisam informar o fuso horário.")
        self.created_at = created_at
        self.updated_at = updated_at

    def mark_persisted(self, updated_at: datetime) -> None:
        """Sincroniza a versão gerada pelo banco após uma escrita bem-sucedida."""

        if updated_at.tzinfo is None:
            raise InvalidStudentDataError("A versão do cadastro precisa informar o fuso horário.")
        self.updated_at = updated_at

    def age_on(self, reference_date: date | None = None) -> int:
        """Calcula idade civil na data informada sem armazenar valor derivado."""

        reference = reference_date or date.today()
        before_birthday = (reference.month, reference.day) < (
            self.birth_date.month,
            self.birth_date.day,
        )
        return reference.year - self.birth_date.year - before_birthday

    def pull_events(self) -> tuple[DomainEvent, ...]:
        """Entrega eventos uma única vez para evitar publicação duplicada."""

        events = tuple(self._events)
        self._events.clear()
        return events
