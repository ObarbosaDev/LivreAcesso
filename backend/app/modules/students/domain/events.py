"""Eventos emitidos pelo agregado de aluno."""

from dataclasses import dataclass
from uuid import UUID

from backend.app.shared.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class StudentRegistered(DomainEvent):
    """Informa que o cadastro terminou sem carregar dados pessoais no evento."""

    # O identificador técnico permite buscar dados autorizados posteriormente.
    # Nome, CPF e contato não viajam no evento para reduzir exposição acidental.
    student_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class StudentUpdated(DomainEvent):
    """Informa quais campos mudaram, mas nunca carrega os valores pessoais."""

    student_id: UUID
    changed_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class StudentStatusChanged(DomainEvent):
    """Registra a transição cadastral sem copiar o motivo potencialmente sensível."""

    student_id: UUID
    previous_status: str
    current_status: str
