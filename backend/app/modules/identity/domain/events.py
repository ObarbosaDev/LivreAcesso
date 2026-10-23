"""Eventos do ciclo dos perfis operacionais."""

from dataclasses import dataclass
from uuid import UUID

from backend.app.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileNameUpdated(DomainEvent):
    """Informa alteração de nome sem carregar o valor pessoal."""

    profile_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileRoleChanged(DomainEvent):
    """Informa mudança de papel sem carregar motivo ou dados pessoais."""

    profile_id: UUID
    previous_role: str
    current_role: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileActivationChanged(DomainEvent):
    """Informa bloqueio/liberação sem replicar a justificativa protegida."""

    profile_id: UUID
    active: bool
