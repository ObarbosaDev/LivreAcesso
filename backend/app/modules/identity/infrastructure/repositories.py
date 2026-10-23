"""Adaptador em memória dos perfis para desenvolvimento e testes."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from threading import RLock
from unicodedata import combining, normalize
from uuid import UUID

from backend.app.modules.identity.application.queries import (
    ProfileListItem,
    ProfileSearchCriteria,
    ProfileSearchResult,
)
from backend.app.modules.identity.domain.entities import UserProfile, UserRole
from backend.app.modules.identity.domain.exceptions import (
    LastActiveCoordinatorError,
    ProfileNotFoundError,
    ProfileVersionConflictError,
)
from backend.app.modules.identity.domain.value_objects import AccessChangeReason


def _search_key(value: str) -> str:
    decomposed = normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not combining(character))


def _next_version(current: datetime) -> datetime:
    candidate = datetime.now(UTC)
    return candidate if candidate > current else current + timedelta(microseconds=1)


def _snapshot(profile: UserProfile) -> UserProfile:
    result = deepcopy(profile)
    result.pull_events()
    return result


class InMemoryProfileRepository:
    """Reproduz autorização estrutural, versão e proteção da coordenação."""

    def __init__(self) -> None:
        self._profiles: dict[UUID, UserProfile] = {}
        self._reasons: list[tuple[UUID, str, str]] = []
        self._lock = RLock()

    def seed(self, profile: UserProfile) -> None:
        """Adiciona perfil sintético explicitamente; não faz parte da porta de produção."""

        with self._lock:
            self._profiles[profile.id] = _snapshot(profile)

    async def get_current(self, user_id: UUID) -> UserProfile | None:
        return await self.get_by_id(user_id)

    async def get_by_id(self, profile_id: UUID) -> UserProfile | None:
        with self._lock:
            profile = self._profiles.get(profile_id)
            return deepcopy(profile) if profile is not None else None

    async def rename(
        self,
        profile: UserProfile,
        *,
        expected_updated_at: datetime,
    ) -> datetime:
        with self._lock:
            return self._save(profile, expected_updated_at=expected_updated_at)

    async def change_role(
        self,
        profile: UserProfile,
        *,
        reason: AccessChangeReason,
        expected_updated_at: datetime,
    ) -> datetime:
        with self._lock:
            current = self._required_current(profile.id, expected_updated_at)
            if (
                current.active
                and current.role is UserRole.COORDINATOR
                and profile.role is not UserRole.COORDINATOR
                and self._active_coordinator_count() == 1
            ):
                raise LastActiveCoordinatorError

            updated_at = self._save(profile, expected_updated_at=expected_updated_at)
            self._reasons.append((profile.id, "role", reason.value))
            return updated_at

    async def change_activation(
        self,
        profile: UserProfile,
        *,
        reason: AccessChangeReason,
        expected_updated_at: datetime,
    ) -> datetime:
        with self._lock:
            current = self._required_current(profile.id, expected_updated_at)
            if (
                current.active
                and current.role is UserRole.COORDINATOR
                and not profile.active
                and self._active_coordinator_count() == 1
            ):
                raise LastActiveCoordinatorError

            updated_at = self._save(profile, expected_updated_at=expected_updated_at)
            self._reasons.append((profile.id, "activation", reason.value))
            return updated_at

    async def search(self, criteria: ProfileSearchCriteria) -> ProfileSearchResult:
        with self._lock:
            query_key = _search_key(criteria.query) if criteria.query else None
            matches = (
                profile
                for profile in self._profiles.values()
                if (criteria.role is None or profile.role is criteria.role)
                and (criteria.active is None or profile.active is criteria.active)
                and (query_key is None or query_key in _search_key(profile.full_name))
            )
            ordered = tuple(
                sorted(matches, key=lambda profile: (_search_key(profile.full_name), profile.id))
            )
            page_items = ordered[criteria.offset : criteria.offset + criteria.limit]
            return ProfileSearchResult(
                items=tuple(
                    ProfileListItem(
                        id=profile.id,
                        full_name=profile.full_name,
                        role=profile.role,
                        active=profile.active,
                        created_at=profile.created_at,
                        updated_at=profile.updated_at,
                    )
                    for profile in page_items
                ),
                total=len(ordered),
            )

    def _required_current(self, profile_id: UUID, expected_updated_at: datetime) -> UserProfile:
        current = self._profiles.get(profile_id)
        if current is None:
            raise ProfileNotFoundError
        if current.updated_at != expected_updated_at:
            raise ProfileVersionConflictError
        return current

    def _save(self, profile: UserProfile, *, expected_updated_at: datetime) -> datetime:
        current = self._required_current(profile.id, expected_updated_at)
        updated_at = _next_version(current.updated_at)
        profile.mark_persisted(updated_at)
        self._profiles[profile.id] = _snapshot(profile)
        return updated_at

    def _active_coordinator_count(self) -> int:
        return sum(
            profile.active and profile.role is UserRole.COORDINATOR
            for profile in self._profiles.values()
        )
