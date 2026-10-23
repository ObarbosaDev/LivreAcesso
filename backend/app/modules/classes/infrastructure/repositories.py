"""Persistência em memória para desenvolvimento e testes do catálogo."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from threading import RLock
from unicodedata import combining, normalize
from uuid import UUID

from backend.app.modules.classes.application.queries import (
    ClassSearchCriteria,
    ClassSearchResult,
    ModalitySearchCriteria,
    ModalitySearchResult,
)
from backend.app.modules.classes.domain.entities import ClassGroup, Modality
from backend.app.modules.classes.domain.exceptions import (
    ActiveClassesExistError,
    ClassNotFoundError,
    ClassVersionConflictError,
    DuplicateClassError,
    DuplicateModalityError,
    ModalityNotFoundError,
    ModalityVersionConflictError,
)
from backend.app.modules.classes.domain.repositories import PersistedCatalogVersion
from backend.app.modules.classes.domain.value_objects import ClassChangeReason


def _search_key(value: str) -> str:
    decomposed = normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not combining(character))


def _next_version(current: datetime) -> datetime:
    candidate = datetime.now(UTC)
    return candidate if candidate > current else current + timedelta(microseconds=1)


def _modality_snapshot(modality: Modality) -> Modality:
    result = deepcopy(modality)
    result.pull_events()
    return result


def _class_snapshot(group: ClassGroup) -> ClassGroup:
    result = deepcopy(group)
    result.pull_events()
    return result


class InMemoryClassRepository:
    """Armazena catálogo transitório sem relaxar regras de concorrência."""

    def __init__(self) -> None:
        self._modalities: dict[UUID, Modality] = {}
        self._classes: dict[UUID, ClassGroup] = {}
        self._activation_reasons: list[tuple[str, UUID, str]] = []
        self._lock = RLock()

    async def add_modality(self, modality: Modality) -> PersistedCatalogVersion:
        with self._lock:
            self._ensure_unique_modality_name(modality.name)
            self._modalities[modality.id] = _modality_snapshot(modality)
            return PersistedCatalogVersion(modality.created_at, modality.updated_at)

    async def get_modality(self, modality_id: UUID) -> Modality | None:
        with self._lock:
            modality = self._modalities.get(modality_id)
            return deepcopy(modality) if modality is not None else None

    async def update_modality(
        self,
        modality: Modality,
        *,
        expected_updated_at: datetime,
    ) -> datetime:
        with self._lock:
            current = self._modalities.get(modality.id)
            if current is None:
                raise ModalityNotFoundError
            if current.updated_at != expected_updated_at:
                raise ModalityVersionConflictError
            self._ensure_unique_modality_name(modality.name, excluding=modality.id)
            updated_at = _next_version(current.updated_at)
            modality.mark_persisted(updated_at)
            self._modalities[modality.id] = _modality_snapshot(modality)
            return updated_at

    async def change_modality_activation(
        self,
        modality: Modality,
        *,
        reason: ClassChangeReason,
        expected_updated_at: datetime,
    ) -> datetime:
        with self._lock:
            current = self._modalities.get(modality.id)
            if current is None:
                raise ModalityNotFoundError
            if current.updated_at != expected_updated_at:
                raise ModalityVersionConflictError
            if not modality.active and any(
                group.modality_id == modality.id and group.active
                for group in self._classes.values()
            ):
                raise ActiveClassesExistError
            updated_at = _next_version(current.updated_at)
            modality.mark_persisted(updated_at)
            self._modalities[modality.id] = _modality_snapshot(modality)
            self._activation_reasons.append(("modality", modality.id, reason.value))
            return updated_at

    async def search_modalities(
        self,
        criteria: ModalitySearchCriteria,
    ) -> ModalitySearchResult:
        with self._lock:
            query_key = _search_key(criteria.query) if criteria.query else None
            matches = [
                deepcopy(modality)
                for modality in self._modalities.values()
                if (criteria.active is None or modality.active is criteria.active)
                and (query_key is None or query_key in _search_key(modality.name))
            ]
            ordered = sorted(matches, key=lambda item: (_search_key(item.name), item.id))
            page = ordered[criteria.offset : criteria.offset + criteria.limit]
            return ModalitySearchResult(items=tuple(page), total=len(ordered))

    async def add_class(self, group: ClassGroup) -> PersistedCatalogVersion:
        with self._lock:
            self._require_active_modality(group.modality_id)
            self._ensure_unique_class_name(group.modality_id, group.name)
            self._classes[group.id] = _class_snapshot(group)
            return PersistedCatalogVersion(group.created_at, group.updated_at)

    async def get_class(self, class_id: UUID) -> ClassGroup | None:
        with self._lock:
            group = self._classes.get(class_id)
            return deepcopy(group) if group is not None else None

    async def update_class(
        self,
        group: ClassGroup,
        *,
        expected_updated_at: datetime,
    ) -> datetime:
        with self._lock:
            current = self._classes.get(group.id)
            if current is None:
                raise ClassNotFoundError
            if current.updated_at != expected_updated_at:
                raise ClassVersionConflictError
            self._require_active_modality(group.modality_id)
            self._ensure_unique_class_name(
                group.modality_id,
                group.name,
                excluding=group.id,
            )
            updated_at = _next_version(current.updated_at)
            group.mark_persisted(updated_at)
            self._classes[group.id] = _class_snapshot(group)
            return updated_at

    async def change_class_activation(
        self,
        group: ClassGroup,
        *,
        reason: ClassChangeReason,
        expected_updated_at: datetime,
    ) -> datetime:
        with self._lock:
            current = self._classes.get(group.id)
            if current is None:
                raise ClassNotFoundError
            if current.updated_at != expected_updated_at:
                raise ClassVersionConflictError
            if group.active:
                self._require_active_modality(group.modality_id)
            updated_at = _next_version(current.updated_at)
            group.mark_persisted(updated_at)
            self._classes[group.id] = _class_snapshot(group)
            self._activation_reasons.append(("class", group.id, reason.value))
            return updated_at

    async def search_classes(self, criteria: ClassSearchCriteria) -> ClassSearchResult:
        with self._lock:
            query_key = _search_key(criteria.query) if criteria.query else None
            matches = [
                deepcopy(group)
                for group in self._classes.values()
                if (criteria.active is None or group.active is criteria.active)
                and (criteria.modality_id is None or group.modality_id == criteria.modality_id)
                and (query_key is None or query_key in _search_key(group.name))
                and (
                    criteria.viewer_instructor_id is None
                    or any(
                        instructor.id == criteria.viewer_instructor_id
                        for instructor in group.instructors
                    )
                )
            ]
            ordered = sorted(matches, key=lambda item: (_search_key(item.name), item.id))
            page = ordered[criteria.offset : criteria.offset + criteria.limit]
            return ClassSearchResult(items=tuple(page), total=len(ordered))

    def _ensure_unique_modality_name(
        self,
        name: str,
        *,
        excluding: UUID | None = None,
    ) -> None:
        key = _search_key(name)
        if any(
            _search_key(item.name) == key and item.id != excluding
            for item in self._modalities.values()
        ):
            raise DuplicateModalityError

    def _ensure_unique_class_name(
        self,
        modality_id: UUID,
        name: str,
        *,
        excluding: UUID | None = None,
    ) -> None:
        key = _search_key(name)
        if any(
            item.modality_id == modality_id
            and _search_key(item.name) == key
            and item.id != excluding
            for item in self._classes.values()
        ):
            raise DuplicateClassError

    def _require_active_modality(self, modality_id: UUID) -> Modality:
        modality = self._modalities.get(modality_id)
        if modality is None or not modality.active:
            raise ModalityNotFoundError
        return modality
