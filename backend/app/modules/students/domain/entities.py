"""Entidades e agregado do contexto de alunos."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from backend.app.modules.students.domain.events import StudentRegistered
from backend.app.modules.students.domain.exceptions import InvalidStudentDataError
from backend.app.modules.students.domain.value_objects import CPF, Phone
from backend.app.shared.domain.events import DomainEvent


class StudentStatus(StrEnum):
    """Ciclo cadastral do aluno, independente de suas matrículas."""

    ACTIVE = "ativo"
    INACTIVE = "inativo"


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
    ) -> "Student":
        # O status inicial pertence ao ciclo do domínio e não ao payload HTTP.
        # Dessa forma, nenhum cliente consegue criar um cadastro já inativo.
        student = cls(
            id=uuid4(),
            full_name=full_name,
            cpf=cpf,
            birth_date=birth_date,
            guardian=guardian,
            status=StudentStatus.ACTIVE,
        )
        student._events.append(StudentRegistered(student_id=student.id))
        return student

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
