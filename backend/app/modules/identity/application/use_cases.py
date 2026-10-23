"""Casos de uso dos perfis e acessos operacionais."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from backend.app.modules.identity.application.dtos import (
    ChangeProfileActivationInput,
    ChangeProfileRoleInput,
    ProfileOutput,
    ProfilePageOutput,
    UpdateMyProfileInput,
)
from backend.app.modules.identity.application.mappers import ProfileMapper
from backend.app.modules.identity.application.queries import (
    ProfileQueryService,
    ProfileSearchCriteria,
)
from backend.app.modules.identity.domain.entities import UserProfile, UserRole
from backend.app.modules.identity.domain.exceptions import (
    ProfileNotFoundError,
    ProfileVersionConflictError,
)
from backend.app.modules.identity.domain.repositories import ProfileRepository
from backend.app.modules.identity.domain.value_objects import AccessChangeReason
from backend.app.shared.application.event_bus import EventPublisher
from backend.app.shared.application.exceptions import PermissionDeniedError


async def _current_profile(repository: ProfileRepository, actor_id: UUID) -> UserProfile:
    profile = await repository.get_current(actor_id)
    if profile is None:
        raise ProfileNotFoundError
    return profile


async def _require_coordinator(repository: ProfileRepository, actor_id: UUID) -> UserProfile:
    actor = await _current_profile(repository, actor_id)
    if not actor.active or actor.role is not UserRole.COORDINATOR:
        raise PermissionDeniedError
    return actor


def _ensure_version(profile: UserProfile, expected_updated_at: datetime) -> None:
    if profile.updated_at != expected_updated_at:
        raise ProfileVersionConflictError


def _publish(profile: UserProfile, publisher: EventPublisher) -> None:
    for event in profile.pull_events():
        publisher.publish(event)


@dataclass(slots=True)
class GetMyProfile:
    repository: ProfileRepository
    actor_id: UUID

    async def execute(self) -> ProfileOutput:
        profile = await _current_profile(self.repository, self.actor_id)
        return ProfileMapper.to_output(profile)


@dataclass(slots=True)
class UpdateMyProfile:
    repository: ProfileRepository
    event_publisher: EventPublisher
    actor_id: UUID

    async def execute(self, dto: UpdateMyProfileInput) -> ProfileOutput:
        profile = await _current_profile(self.repository, self.actor_id)
        _ensure_version(profile, dto.expected_updated_at)

        if profile.rename(dto.full_name):
            updated_at = await self.repository.rename(
                profile,
                expected_updated_at=dto.expected_updated_at,
            )
            profile.mark_persisted(updated_at)
            _publish(profile, self.event_publisher)
        return ProfileMapper.to_output(profile)


@dataclass(slots=True)
class ListProfiles:
    repository: ProfileRepository
    query_service: ProfileQueryService
    actor_id: UUID

    async def execute(
        self,
        *,
        role: UserRole | None = None,
        active: bool | None = None,
        query: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> ProfilePageOutput:
        await _require_coordinator(self.repository, self.actor_id)
        result = await self.query_service.search(
            ProfileSearchCriteria(
                role=role,
                active=active,
                query=query,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
        )
        total_pages = (result.total + page_size - 1) // page_size if result.total else 0
        return ProfilePageOutput(
            items=[ProfileMapper.list_item_to_output(item) for item in result.items],
            page=page,
            page_size=page_size,
            total=result.total,
            total_pages=total_pages,
            has_previous=page > 1,
            has_next=page < total_pages,
        )


@dataclass(slots=True)
class ChangeProfileRole:
    repository: ProfileRepository
    event_publisher: EventPublisher
    actor_id: UUID

    async def execute(self, profile_id: UUID, dto: ChangeProfileRoleInput) -> ProfileOutput:
        await _require_coordinator(self.repository, self.actor_id)
        profile = await self.repository.get_by_id(profile_id)
        if profile is None:
            raise ProfileNotFoundError
        _ensure_version(profile, dto.expected_updated_at)

        reason = AccessChangeReason(dto.reason)
        target_role = UserRole(dto.role.value)
        if profile.change_role(target_role, reason):
            updated_at = await self.repository.change_role(
                profile,
                reason=reason,
                expected_updated_at=dto.expected_updated_at,
            )
            profile.mark_persisted(updated_at)
            _publish(profile, self.event_publisher)
        return ProfileMapper.to_output(profile)


@dataclass(slots=True)
class ChangeProfileActivation:
    repository: ProfileRepository
    event_publisher: EventPublisher
    actor_id: UUID
    active: bool

    async def execute(
        self,
        profile_id: UUID,
        dto: ChangeProfileActivationInput,
    ) -> ProfileOutput:
        await _require_coordinator(self.repository, self.actor_id)
        profile = await self.repository.get_by_id(profile_id)
        if profile is None:
            raise ProfileNotFoundError
        _ensure_version(profile, dto.expected_updated_at)

        reason = AccessChangeReason(dto.reason)
        if profile.change_activation(self.active, reason):
            updated_at = await self.repository.change_activation(
                profile,
                reason=reason,
                expected_updated_at=dto.expected_updated_at,
            )
            profile.mark_persisted(updated_at)
            _publish(profile, self.event_publisher)
        return ProfileMapper.to_output(profile)
