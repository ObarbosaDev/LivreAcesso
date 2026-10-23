"""Portas de persistência dos perfis operacionais."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.app.modules.identity.domain.entities import UserProfile
from backend.app.modules.identity.domain.value_objects import AccessChangeReason


class ProfileRepository(Protocol):
    async def get_current(self, user_id: UUID) -> UserProfile | None: ...

    async def get_by_id(self, profile_id: UUID) -> UserProfile | None: ...

    async def rename(
        self,
        profile: UserProfile,
        *,
        expected_updated_at: datetime,
    ) -> datetime: ...

    async def change_role(
        self,
        profile: UserProfile,
        *,
        reason: AccessChangeReason,
        expected_updated_at: datetime,
    ) -> datetime: ...

    async def change_activation(
        self,
        profile: UserProfile,
        *,
        reason: AccessChangeReason,
        expected_updated_at: datetime,
    ) -> datetime: ...
