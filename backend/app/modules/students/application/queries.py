"""Portas e projeções de leitura do módulo de alunos."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from backend.app.modules.students.domain.entities import StudentStatus


@dataclass(frozen=True, slots=True)
class StudentSearchCriteria:
    """Critérios limitados para evitar consultas sem paginação."""

    status: StudentStatus | None = None
    query: str | None = None
    offset: int = 0
    limit: int = 25

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("O deslocamento não pode ser negativo.")
        if not 1 <= self.limit <= 100:
            raise ValueError("O limite deve estar entre 1 e 100.")

        # O termo pode conter nome de pessoa e, portanto, não deve ser registrado
        # em logs. Aqui apenas removemos espaços redundantes antes da persistência.
        normalized_query = " ".join(self.query.split()) if self.query else None
        object.__setattr__(self, "query", normalized_query or None)


@dataclass(frozen=True, slots=True)
class StudentListItem:
    """Projeção segura que nunca carrega CPF ou telefone completos."""

    id: UUID
    full_name: str
    cpf_masked: str
    birth_date: date
    age: int
    status: StudentStatus
    guardian_name: str
    guardian_phone_masked: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StudentSearchResult:
    """Resultado paginado cujo total é calculado antes do recorte."""

    items: tuple[StudentListItem, ...]
    total: int


class StudentQueryService(Protocol):
    """Porta assíncrona de leitura que retorna somente projeções seguras."""

    async def search(self, criteria: StudentSearchCriteria) -> StudentSearchResult: ...
