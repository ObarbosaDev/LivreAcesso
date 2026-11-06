"""Entidade de perfil e regras de acesso operacional."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.app.modules.identity.domain.exceptions import (
    InvalidProfileDataError,
    InvalidProfileRoleError,
    ProfileRoleRequiredError,
)
from backend.app.modules.identity.domain.value_objects import AccessChangeReason
from backend.app.shared.domain.events import DomainEvent


class UserRole(StrEnum):
    """Papel de negócio; valores públicos ficam em português."""

    PENDING = "pendente"
    COORDINATOR = "coordenador"
    RECEPTIONIST = "recepcao"
    INSTRUCTOR = "instrutor"
    READ_ONLY = "consulta"


class Capability(StrEnum):
    """Ações implementadas que uma interface pode apresentar à pessoa."""

    PROFILES_READ = "profiles:read"
    PROFILES_MANAGE = "profiles:manage"
    STUDENTS_LIST = "students:list"
    STUDENTS_READ = "students:read"
    STUDENTS_CREATE = "students:create"
    STUDENTS_UPDATE = "students:update"
    STUDENTS_CHANGE_STATUS = "students:change-status"
    CLASSES_LIST = "classes:list"
    CLASSES_READ = "classes:read"
    CLASSES_MANAGE = "classes:manage"
    ENROLLMENTS_CREATE = "enrollments:create"
    ENROLLMENTS_MANAGE = "enrollments:manage"
    AGENDA_MANAGE = "agenda:manage"


_ROLE_CAPABILITIES: dict[UserRole, tuple[Capability, ...]] = {
    UserRole.PENDING: (),
    UserRole.COORDINATOR: tuple(Capability),
    UserRole.RECEPTIONIST: (
        Capability.STUDENTS_LIST,
        Capability.STUDENTS_READ,
        Capability.STUDENTS_CREATE,
        Capability.STUDENTS_UPDATE,
        Capability.CLASSES_LIST,
        Capability.CLASSES_READ,
        Capability.ENROLLMENTS_CREATE,
        Capability.AGENDA_MANAGE,
    ),
    UserRole.INSTRUCTOR: (
        Capability.CLASSES_LIST,
        Capability.CLASSES_READ,
    ),
    UserRole.READ_ONLY: (
        Capability.STUDENTS_LIST,
        Capability.CLASSES_LIST,
        Capability.CLASSES_READ,
    ),
}


def capabilities_for_role(role: UserRole) -> tuple[Capability, ...]:
    """Expõe a matriz de capacidades sem duplicá-la na camada de aplicação."""

    return _ROLE_CAPABILITIES[role]


def _normalize_name(value: str) -> str:
    normalized = " ".join(value.split())
    if not 3 <= len(normalized) <= 120:
        raise InvalidProfileDataError("Informe um nome entre 3 e 120 caracteres.")
    return normalized


@dataclass(slots=True)
class UserProfile:
    """Perfil operacional separado da senha e da identidade do Supabase Auth."""

    id: UUID
    full_name: str
    role: UserRole
    active: bool
    created_at: datetime
    updated_at: datetime
    _events: list[DomainEvent] = field(
        default_factory=list,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        self.full_name = _normalize_name(self.full_name)
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise InvalidProfileDataError("Datas do perfil precisam informar o fuso horário.")
        if self.active and self.role is UserRole.PENDING:
            raise ProfileRoleRequiredError

    @property
    def capabilities(self) -> tuple[Capability, ...]:
        """Oculta todas as ações quando o acesso administrativo está bloqueado."""

        return capabilities_for_role(self.role) if self.active else ()

    def rename(self, full_name: str) -> bool:
        normalized = _normalize_name(full_name)
        if normalized == self.full_name:
            return False
        self.full_name = normalized
        return True

    def change_role(self, target_role: UserRole, reason: AccessChangeReason) -> bool:
        if target_role is UserRole.PENDING:
            raise InvalidProfileRoleError
        if target_role is self.role:
            return False

        self.role = target_role
        # O motivo segue somente para o histórico privado no repositório.
        del reason
        return True

    def change_activation(self, active: bool, reason: AccessChangeReason) -> bool:
        if active and self.role is UserRole.PENDING:
            raise ProfileRoleRequiredError
        if active is self.active:
            return False

        self.active = active
        del reason
        return True

    def mark_persisted(self, updated_at: datetime) -> None:
        if updated_at.tzinfo is None:
            raise InvalidProfileDataError("A versão do perfil precisa informar o fuso horário.")
        self.updated_at = updated_at

    def pull_events(self) -> tuple[DomainEvent, ...]:
        events = tuple(self._events)
        self._events.clear()
        return events
