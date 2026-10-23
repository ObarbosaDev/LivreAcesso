"""Portas de escrita para modalidades e turmas."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.app.modules.classes.domain.entities import ClassGroup, Modality
from backend.app.modules.classes.domain.value_objects import ClassChangeReason


@dataclass(frozen=True, slots=True)
class PersistedCatalogVersion:
    """Timestamps autoritativos devolvidos pelo armazenamento."""

    created_at: datetime
    updated_at: datetime


class ModalityRepository(Protocol):
    async def add_modality(self, modality: Modality) -> PersistedCatalogVersion: ...

    async def get_modality(self, modality_id: UUID) -> Modality | None: ...

    async def update_modality(
        self,
        modality: Modality,
        *,
        expected_updated_at: datetime,
    ) -> datetime: ...

    async def change_modality_activation(
        self,
        modality: Modality,
        *,
        reason: ClassChangeReason,
        expected_updated_at: datetime,
    ) -> datetime: ...


class ClassRepository(Protocol):
    async def add_class(self, group: ClassGroup) -> PersistedCatalogVersion: ...

    async def get_class(self, class_id: UUID) -> ClassGroup | None: ...

    async def update_class(
        self,
        group: ClassGroup,
        *,
        expected_updated_at: datetime,
    ) -> datetime: ...

    async def change_class_activation(
        self,
        group: ClassGroup,
        *,
        reason: ClassChangeReason,
        expected_updated_at: datetime,
    ) -> datetime: ...
