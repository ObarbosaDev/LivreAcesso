"""Porta e critérios de leitura paginada dos perfis."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.app.modules.identity.domain.entities import UserRole


@dataclass(frozen=True, slots=True)
class ProfileSearchCriteria:
    role: UserRole | None = None
    active: bool | None = None
    query: str | None = None
    offset: int = 0
    limit: int = 25

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError("O deslocamento não pode ser negativo.")
        if not 1 <= self.limit <= 100:
            raise ValueError("O limite deve estar entre 1 e 100.")
        normalized_query = " ".join(self.query.split()) if self.query else None
        object.__setattr__(self, "query", normalized_query or None)


@dataclass(frozen=True, slots=True)
class ProfileListItem:
    id: UUID
    full_name: str
    role: UserRole
    active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProfileSearchResult:
    items: tuple[ProfileListItem, ...]
    total: int


class ProfileQueryService(Protocol):
    async def search(self, criteria: ProfileSearchCriteria) -> ProfileSearchResult: ...
