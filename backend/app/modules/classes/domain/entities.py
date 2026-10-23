"""Entidades e invariantes de modalidades, turmas e horários."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from enum import StrEnum
from itertools import pairwise
from uuid import UUID, uuid4

from backend.app.modules.classes.domain.events import (
    ClassActivationChanged,
    ClassCreated,
    ClassUpdated,
    ModalityActivationChanged,
    ModalityCreated,
    ModalityUpdated,
)
from backend.app.modules.classes.domain.exceptions import (
    InvalidCapacityError,
    InvalidClassDataError,
    InvalidModalityDataError,
    InvalidScheduleError,
)
from backend.app.modules.classes.domain.value_objects import ClassChangeReason
from backend.app.shared.domain.events import DomainEvent


class Weekday(StrEnum):
    """Dias públicos em português; o adaptador traduz para o enum PostgreSQL."""

    MONDAY = "segunda"
    TUESDAY = "terca"
    WEDNESDAY = "quarta"
    THURSDAY = "quinta"
    FRIDAY = "sexta"
    SATURDAY = "sabado"
    SUNDAY = "domingo"


_WEEKDAY_ORDER = {weekday: index for index, weekday in enumerate(Weekday)}


def _normalize_text(value: str, *, minimum: int, maximum: int, message: str) -> str:
    normalized = " ".join(value.split())
    if not minimum <= len(normalized) <= maximum:
        raise InvalidClassDataError(message)
    return normalized


@dataclass(frozen=True, slots=True)
class ClassSchedule:
    """Intervalo semanal local; timezone será definido pela instituição no calendário."""

    weekday: Weekday
    starts_at: time
    ends_at: time

    def __post_init__(self) -> None:
        if self.starts_at.tzinfo is not None or self.ends_at.tzinfo is not None:
            raise InvalidScheduleError("Horários semanais não devem informar fuso horário.")
        if self.starts_at >= self.ends_at:
            raise InvalidScheduleError("O término precisa ocorrer depois do início.")


@dataclass(frozen=True, slots=True)
class ClassInstructor:
    """Projeção mínima de um perfil instrutor ativo."""

    id: UUID
    full_name: str

    def __post_init__(self) -> None:
        normalized = " ".join(self.full_name.split())
        if not 3 <= len(normalized) <= 120:
            raise InvalidClassDataError("O nome do instrutor é inválido.")
        object.__setattr__(self, "full_name", normalized)


def _validate_schedules(schedules: tuple[ClassSchedule, ...]) -> tuple[ClassSchedule, ...]:
    if not 1 <= len(schedules) <= 14:
        raise InvalidScheduleError("Informe entre 1 e 14 horários semanais.")

    ordered = tuple(
        sorted(schedules, key=lambda item: (_WEEKDAY_ORDER[item.weekday], item.starts_at))
    )
    for previous, current in pairwise(ordered):
        if previous.weekday is current.weekday and current.starts_at < previous.ends_at:
            raise InvalidScheduleError("Os horários da turma não podem se sobrepor.")
    return ordered


def _validate_instructors(
    instructors: tuple[ClassInstructor, ...],
) -> tuple[ClassInstructor, ...]:
    if not 1 <= len(instructors) <= 20:
        raise InvalidClassDataError("Informe entre 1 e 20 instrutores ativos.")
    if len({instructor.id for instructor in instructors}) != len(instructors):
        raise InvalidClassDataError("Um instrutor não pode aparecer mais de uma vez.")
    return tuple(sorted(instructors, key=lambda item: (item.full_name.casefold(), item.id)))


@dataclass(slots=True)
class Modality:
    """Tipo de atividade independente das turmas que a oferecem."""

    id: UUID
    name: str
    description: str | None
    active: bool
    created_at: datetime
    updated_at: datetime
    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        normalized = " ".join(self.name.split())
        if not 3 <= len(normalized) <= 80:
            raise InvalidModalityDataError("Informe um nome entre 3 e 80 caracteres.")
        description = " ".join(self.description.split()) if self.description else None
        if description and len(description) > 500:
            raise InvalidModalityDataError("A descrição deve ter no máximo 500 caracteres.")
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise InvalidModalityDataError("Datas da modalidade precisam informar o fuso horário.")
        self.name = normalized
        self.description = description

    @classmethod
    def create(cls, *, name: str, description: str | None) -> "Modality":
        now = datetime.now(UTC)
        modality = cls(
            id=uuid4(),
            name=name,
            description=description,
            active=True,
            created_at=now,
            updated_at=now,
        )
        modality._events.append(ModalityCreated(modality_id=modality.id))
        return modality

    def update(self, *, name: str, description: str | None) -> tuple[str, ...]:
        candidate = Modality(
            id=self.id,
            name=name,
            description=description,
            active=self.active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
        changed: list[str] = []
        if self.name != candidate.name:
            self.name = candidate.name
            changed.append("name")
        if self.description != candidate.description:
            self.description = candidate.description
            changed.append("description")
        result = tuple(changed)
        if result:
            self._events.append(ModalityUpdated(modality_id=self.id, changed_fields=result))
        return result

    def change_activation(self, active: bool, reason: ClassChangeReason) -> bool:
        if self.active is active:
            return False
        self.active = active
        del reason
        self._events.append(ModalityActivationChanged(modality_id=self.id, active=active))
        return True

    def mark_created(self, created_at: datetime, updated_at: datetime) -> None:
        if created_at.tzinfo is None or updated_at.tzinfo is None:
            raise InvalidModalityDataError("Datas persistidas precisam informar o fuso horário.")
        self.created_at = created_at
        self.updated_at = updated_at

    def mark_persisted(self, updated_at: datetime) -> None:
        if updated_at.tzinfo is None:
            raise InvalidModalityDataError(
                "A versão da modalidade precisa informar o fuso horário."
            )
        self.updated_at = updated_at

    def pull_events(self) -> tuple[DomainEvent, ...]:
        events = tuple(self._events)
        self._events.clear()
        return events


@dataclass(slots=True)
class ClassGroup:
    """Oferta concreta de uma modalidade, sem matrículas embutidas."""

    id: UUID
    modality_id: UUID
    name: str
    capacity: int
    location: str
    minimum_age: int | None
    maximum_age: int | None
    schedules: tuple[ClassSchedule, ...]
    instructors: tuple[ClassInstructor, ...]
    active: bool
    created_at: datetime
    updated_at: datetime
    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.name = _normalize_text(
            self.name,
            minimum=3,
            maximum=120,
            message="Informe um nome de turma entre 3 e 120 caracteres.",
        )
        self.location = _normalize_text(
            self.location,
            minimum=2,
            maximum=120,
            message="Informe um local entre 2 e 120 caracteres.",
        )
        if not 1 <= self.capacity <= 500:
            raise InvalidCapacityError
        for age in (self.minimum_age, self.maximum_age):
            if age is not None and not 0 <= age <= 120:
                raise InvalidClassDataError("A faixa etária deve ficar entre 0 e 120 anos.")
        if (
            self.minimum_age is not None
            and self.maximum_age is not None
            and self.minimum_age > self.maximum_age
        ):
            raise InvalidClassDataError("A idade mínima não pode superar a máxima.")
        self.schedules = _validate_schedules(self.schedules)
        self.instructors = _validate_instructors(self.instructors)
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise InvalidClassDataError("Datas da turma precisam informar o fuso horário.")

    @classmethod
    def create(
        cls,
        *,
        modality_id: UUID,
        name: str,
        capacity: int,
        location: str,
        minimum_age: int | None,
        maximum_age: int | None,
        schedules: tuple[ClassSchedule, ...],
        instructors: tuple[ClassInstructor, ...],
    ) -> "ClassGroup":
        now = datetime.now(UTC)
        group = cls(
            id=uuid4(),
            modality_id=modality_id,
            name=name,
            capacity=capacity,
            location=location,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            schedules=schedules,
            instructors=instructors,
            active=True,
            created_at=now,
            updated_at=now,
        )
        group._events.append(ClassCreated(class_id=group.id, modality_id=modality_id))
        return group

    def update(
        self,
        *,
        modality_id: UUID,
        name: str,
        capacity: int,
        location: str,
        minimum_age: int | None,
        maximum_age: int | None,
        schedules: tuple[ClassSchedule, ...],
        instructors: tuple[ClassInstructor, ...],
    ) -> tuple[str, ...]:
        candidate = ClassGroup(
            id=self.id,
            modality_id=modality_id,
            name=name,
            capacity=capacity,
            location=location,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            schedules=schedules,
            instructors=instructors,
            active=self.active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
        changed: list[str] = []
        for field_name in (
            "modality_id",
            "name",
            "capacity",
            "location",
            "minimum_age",
            "maximum_age",
            "schedules",
            "instructors",
        ):
            if getattr(self, field_name) != getattr(candidate, field_name):
                setattr(self, field_name, getattr(candidate, field_name))
                changed.append(field_name)
        result = tuple(changed)
        if result:
            self._events.append(ClassUpdated(class_id=self.id, changed_fields=result))
        return result

    def change_activation(self, active: bool, reason: ClassChangeReason) -> bool:
        if self.active is active:
            return False
        # Horários e instrutores são obrigatórios no próprio agregado; uma turma
        # nunca pode ser reativada parcialmente configurada.
        self.active = active
        del reason
        self._events.append(ClassActivationChanged(class_id=self.id, active=active))
        return True

    def mark_created(self, created_at: datetime, updated_at: datetime) -> None:
        if created_at.tzinfo is None or updated_at.tzinfo is None:
            raise InvalidClassDataError("Datas persistidas precisam informar o fuso horário.")
        self.created_at = created_at
        self.updated_at = updated_at

    def mark_persisted(self, updated_at: datetime) -> None:
        if updated_at.tzinfo is None:
            raise InvalidClassDataError("A versão da turma precisa informar o fuso horário.")
        self.updated_at = updated_at

    def pull_events(self) -> tuple[DomainEvent, ...]:
        events = tuple(self._events)
        self._events.clear()
        return events
