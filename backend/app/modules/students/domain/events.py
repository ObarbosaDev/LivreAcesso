"""Eventos emitidos pelo agregado de aluno."""

from dataclasses import dataclass
from uuid import UUID

from backend.app.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class StudentRegistered(DomainEvent):
    """Emitido depois que um novo aluno é registrado."""

    student_id: UUID
    modality: str
