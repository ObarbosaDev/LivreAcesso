"""Portas de consulta paginada do catálogo de turmas."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from backend.app.modules.classes.domain.entities import ClassGroup, Modality


def _normalize_query(value: str | None) -> str | None:
    normalized = " ".join(value.split()) if value else None
    return normalized or None


@dataclass(frozen=True, slots=True)
class ModalitySearchCriteria:
    active: bool | None = None
    query: str | None = None
    offset: int = 0
    limit: int = 25

    def __post_init__(self) -> None:
        if self.offset < 0 or not 1 <= self.limit <= 100:
            raise ValueError("Paginação de modalidades inválida.")
        object.__setattr__(self, "query", _normalize_query(self.query))


@dataclass(frozen=True, slots=True)
class ModalitySearchResult:
    items: tuple[Modality, ...]
    total: int


@dataclass(frozen=True, slots=True)
class ClassSearchCriteria:
    active: bool | None = None
    modality_id: UUID | None = None
    query: str | None = None
    offset: int = 0
    limit: int = 25
    # Somente o adaptador em memória usa este campo. A RPC ignora parâmetros de
    # identidade e deriva o instrutor exclusivamente de auth.uid().
    viewer_instructor_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.offset < 0 or not 1 <= self.limit <= 100:
            raise ValueError("Paginação de turmas inválida.")
        object.__setattr__(self, "query", _normalize_query(self.query))


@dataclass(frozen=True, slots=True)
class ClassSearchResult:
    items: tuple[ClassGroup, ...]
    total: int


class ModalityQueryService(Protocol):
    async def search_modalities(
        self,
        criteria: ModalitySearchCriteria,
    ) -> ModalitySearchResult: ...


class ClassQueryService(Protocol):
    async def search_classes(self, criteria: ClassSearchCriteria) -> ClassSearchResult: ...
