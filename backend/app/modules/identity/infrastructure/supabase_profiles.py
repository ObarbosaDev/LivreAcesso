"""Persistência de perfis operacionais pelas RPCs protegidas do Supabase."""

from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    model_validator,
)

from backend.app.modules.identity.application.authentication import InvalidAccessTokenError
from backend.app.modules.identity.application.queries import (
    ProfileListItem,
    ProfileSearchCriteria,
    ProfileSearchResult,
)
from backend.app.modules.identity.domain.entities import UserProfile, UserRole
from backend.app.modules.identity.domain.exceptions import (
    LastActiveCoordinatorError,
    ProfileDomainError,
    ProfileNotFoundError,
    ProfileRoleRequiredError,
    ProfileVersionConflictError,
)
from backend.app.modules.identity.domain.value_objects import AccessChangeReason
from backend.app.shared.application.exceptions import (
    PermissionDeniedError,
    PersistenceRejectedError,
    PersistenceUnavailableError,
)
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import (
    SupabaseRPCError,
    SupabaseRPCGateway,
    SupabaseTransportError,
)


class _DatabaseRole(StrEnum):
    PENDING = "pending"
    COORDINATOR = "coordinator"
    RECEPTIONIST = "receptionist"
    INSTRUCTOR = "instructor"
    READ_ONLY = "read_only"


_TO_DOMAIN_ROLE = {
    _DatabaseRole.PENDING: UserRole.PENDING,
    _DatabaseRole.COORDINATOR: UserRole.COORDINATOR,
    _DatabaseRole.RECEPTIONIST: UserRole.RECEPTIONIST,
    _DatabaseRole.INSTRUCTOR: UserRole.INSTRUCTOR,
    _DatabaseRole.READ_ONLY: UserRole.READ_ONLY,
}
_TO_DATABASE_ROLE = {domain: database for database, domain in _TO_DOMAIN_ROLE.items()}


class _ProfileRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    full_name: str = Field(min_length=3, max_length=120)
    role: _DatabaseRole
    active: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime

    @model_validator(mode="after")
    def pending_profile_must_be_inactive(self) -> Self:
        if self.role is _DatabaseRole.PENDING and self.active:
            raise ValueError("Perfil pendente não pode estar ativo.")
        return self


class _ProfileSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[_ProfileRow]
    total: int = Field(ge=0)


class _MutationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    updated_at: AwareDatetime


_PROFILE = TypeAdapter(_ProfileRow)
_PROFILE_SEARCH = TypeAdapter(_ProfileSearchResponse)
_MUTATION = TypeAdapter(_MutationResponse)


class SupabaseProfileRepository:
    """Implementa comandos e consultas usando o JWT efêmero da requisição."""

    def __init__(self, gateway: SupabaseRPCGateway, context: RequestContext) -> None:
        self._gateway = gateway
        self._context = context

    async def get_current(self, user_id: UUID) -> UserProfile | None:
        try:
            result = await self._call("get_my_profile", {})
        except ProfileNotFoundError:
            return None
        profile = self._parse_profile(result)
        if profile.id != user_id:
            # Um token nunca pode receber perfil de outra identidade; divergência
            # indica contrato remoto corrompido e falha fechada.
            raise PersistenceUnavailableError
        return profile

    async def get_by_id(self, profile_id: UUID) -> UserProfile | None:
        try:
            result = await self._call("get_profile_detail", {"p_profile_id": str(profile_id)})
        except ProfileNotFoundError:
            return None
        return self._parse_profile(result)

    async def rename(
        self,
        profile: UserProfile,
        *,
        expected_updated_at: datetime,
    ) -> datetime:
        result = await self._call(
            "update_my_profile_name",
            {
                "p_expected_updated_at": expected_updated_at.isoformat(),
                "p_full_name": profile.full_name,
                "p_request_id": str(self._context.request_id),
            },
        )
        return self._mutation_timestamp(result)

    async def change_role(
        self,
        profile: UserProfile,
        *,
        reason: AccessChangeReason,
        expected_updated_at: datetime,
    ) -> datetime:
        result = await self._call(
            "change_profile_role",
            {
                "p_profile_id": str(profile.id),
                "p_target_role": _TO_DATABASE_ROLE[profile.role].value,
                "p_reason": reason.value,
                "p_expected_updated_at": expected_updated_at.isoformat(),
                "p_request_id": str(self._context.request_id),
            },
        )
        return self._mutation_timestamp(result)

    async def change_activation(
        self,
        profile: UserProfile,
        *,
        reason: AccessChangeReason,
        expected_updated_at: datetime,
    ) -> datetime:
        result = await self._call(
            "change_profile_activation",
            {
                "p_profile_id": str(profile.id),
                "p_active": profile.active,
                "p_reason": reason.value,
                "p_expected_updated_at": expected_updated_at.isoformat(),
                "p_request_id": str(self._context.request_id),
            },
        )
        return self._mutation_timestamp(result)

    async def search(self, criteria: ProfileSearchCriteria) -> ProfileSearchResult:
        database_role = _TO_DATABASE_ROLE[criteria.role].value if criteria.role else None
        result = await self._call(
            "list_profiles",
            {
                "p_role": database_role,
                "p_active": criteria.active,
                "p_query": criteria.query,
                "p_limit": criteria.limit,
                "p_offset": criteria.offset,
            },
        )
        try:
            response = _PROFILE_SEARCH.validate_python(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error

        return ProfileSearchResult(
            items=tuple(self._to_list_item(row) for row in response.items),
            total=response.total,
        )

    async def _call(self, function_name: str, payload: dict[str, object]) -> object:
        try:
            return await self._gateway.call(function_name, payload, self._context)
        except SupabaseTransportError as error:
            raise PersistenceUnavailableError from error
        except SupabaseRPCError as error:
            if error.status_code == 401:
                raise InvalidAccessTokenError from error
            if (
                error.status_code == 403
                or error.database_code == "42501"
                or error.message_code == "forbidden"
            ):
                raise PermissionDeniedError from error
            if error.message_code == "profile_not_found":
                raise ProfileNotFoundError from error
            if error.message_code == "profile_version_conflict":
                raise ProfileVersionConflictError from error
            if error.message_code == "last_active_coordinator":
                raise LastActiveCoordinatorError from error
            if error.message_code == "profile_role_required":
                raise ProfileRoleRequiredError from error
            if error.status_code == 404 or error.status_code >= 500:
                raise PersistenceUnavailableError from error
            raise PersistenceRejectedError from error

    @staticmethod
    def _parse_profile(result: object) -> UserProfile:
        try:
            row = _PROFILE.validate_python(result)
            return SupabaseProfileRepository._to_domain(row)
        except (ValidationError, ProfileDomainError) as error:
            raise PersistenceUnavailableError from error

    @staticmethod
    def _mutation_timestamp(result: object) -> datetime:
        try:
            return _MUTATION.validate_python(result).updated_at
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    @staticmethod
    def _to_domain(row: _ProfileRow) -> UserProfile:
        return UserProfile(
            id=row.id,
            full_name=row.full_name,
            role=_TO_DOMAIN_ROLE[row.role],
            active=row.active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_list_item(row: _ProfileRow) -> ProfileListItem:
        return ProfileListItem(
            id=row.id,
            full_name=row.full_name,
            role=_TO_DOMAIN_ROLE[row.role],
            active=row.active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
