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
