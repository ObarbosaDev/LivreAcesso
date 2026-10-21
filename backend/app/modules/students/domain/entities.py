"""Entidades e agregado do contexto de alunos."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from backend.app.modules.students.domain.events import StudentRegistered
from backend.app.modules.students.domain.exceptions import InvalidStudentDataError
from backend.app.modules.students.domain.value_objects import CPF, Phone
from backend.app.shared.domain.events import DomainEvent


class Modality(StrEnum):
    BALLET = "bale"
    JIU_JITSU = "jiu-jitsu"
    DRUMS = "bateria"


class StudentStatus(StrEnum):
    ACTIVE = "ativo"
    WAITING_LIST = "lista-de-espera"
    INACTIVE = "inativo"


@dataclass(frozen=True, slots=True)
class Guardian:
    """Responsável legal ou contato responsável pelo participante."""

    full_name: str
    phone: Phone
    email: str | None = None

    def __post_init__(self) -> None:
        normalized_name = " ".join(self.full_name.split())
        if len(normalized_name) < 3:
            raise InvalidStudentDataError("Informe o nome completo do responsável.")

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
    modality: Modality
    status: StudentStatus = StudentStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        normalized_name = " ".join(self.full_name.split())
        today = date.today()

        if len(normalized_name) < 3:
            raise InvalidStudentDataError("Informe o nome completo do aluno.")
        if self.birth_date >= today:
            raise InvalidStudentDataError("A data de nascimento deve estar no passado.")
        if self.birth_date.year < today.year - 120:
            raise InvalidStudentDataError("A data de nascimento informada é inválida.")

        self.full_name = normalized_name

    @classmethod
    def register(
        cls,
        *,
        full_name: str,
        cpf: CPF,
        birth_date: date,
        guardian: Guardian,
        modality: Modality,
        status: StudentStatus = StudentStatus.ACTIVE,
    ) -> "Student":
        student = cls(
            id=uuid4(),
            full_name=full_name,
            cpf=cpf,
            birth_date=birth_date,
            guardian=guardian,
            modality=modality,
            status=status,
        )
        student._events.append(
            StudentRegistered(student_id=student.id, modality=student.modality.value)
        )
        return student

    def age_on(self, reference_date: date | None = None) -> int:
        reference = reference_date or date.today()
        before_birthday = (reference.month, reference.day) < (
            self.birth_date.month,
            self.birth_date.day,
        )
        return reference.year - self.birth_date.year - before_birthday

    def pull_events(self) -> tuple[DomainEvent, ...]:
        events = tuple(self._events)
        self._events.clear()
        return events
