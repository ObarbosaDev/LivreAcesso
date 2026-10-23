"""Eventos mínimos do catálogo, sempre sem nomes ou horários."""

from dataclasses import dataclass
from uuid import UUID

from backend.app.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class ModalityCreated(DomainEvent):
    modality_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class ModalityUpdated(DomainEvent):
    modality_id: UUID
    changed_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ModalityActivationChanged(DomainEvent):
    modality_id: UUID
    active: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class ClassCreated(DomainEvent):
    class_id: UUID
    modality_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class ClassUpdated(DomainEvent):
    class_id: UUID
    changed_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ClassActivationChanged(DomainEvent):
    class_id: UUID
    active: bool
