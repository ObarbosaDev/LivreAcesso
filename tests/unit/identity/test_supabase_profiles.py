"""Testes do adaptador Supabase dos perfis operacionais."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx2
import pytest

from backend.app.modules.identity.application.authentication import AccessToken, AuthenticatedUser
from backend.app.modules.identity.application.queries import ProfileSearchCriteria
from backend.app.modules.identity.domain.entities import UserProfile, UserRole
from backend.app.modules.identity.domain.exceptions import (
    LastActiveCoordinatorError,
    ProfileVersionConflictError,
)
from backend.app.modules.identity.domain.value_objects import AccessChangeReason
from backend.app.modules.identity.infrastructure.supabase_profiles import SupabaseProfileRepository
from backend.app.shared.application.exceptions import (
    PermissionDeniedError,
    PersistenceUnavailableError,
)
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway

_PROJECT_URL = "https://project-ref.supabase.co"
_USER_ID = UUID("00000000-0000-4000-8000-000000000001")


def context() -> RequestContext:
    return RequestContext(
        request_id=UUID("00000000-0000-4000-8000-000000000002"),
        user=AuthenticatedUser(
            user_id=_USER_ID,
            access_token=AccessToken("jwt-sintetico"),
            session_id=None,
            assurance_level="aal1",
        ),
    )


def row(
    *,
    profile_id: UUID = _USER_ID,
    role: str = "coordinator",
    active: bool = True,
    updated_at: datetime | None = None,
) -> dict[str, object]:
    version = updated_at or datetime(2026, 10, 23, tzinfo=UTC)
    return {
        "id": str(profile_id),
        "full_name": "Coordenação Teste",
        "role": role,
        "active": active,
        "created_at": datetime(2026, 10, 22, tzinfo=UTC).isoformat(),
        "updated_at": version.isoformat(),
    }


def domain_profile() -> UserProfile:
    data = row()
    return UserProfile(
        id=_USER_ID,
        full_name="Coordenação Teste",
        role=UserRole.COORDINATOR,
        active=True,
        created_at=datetime.fromisoformat(str(data["created_at"])),
        updated_at=datetime.fromisoformat(str(data["updated_at"])),
    )


def test_get_current_maps_database_role() -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=row())

    async def get() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            profile = await SupabaseProfileRepository(gateway, context()).get_current(_USER_ID)
        assert profile is not None
        assert profile.role is UserRole.COORDINATOR
        assert profile.active is True

    asyncio.run(get())


def test_get_current_rejects_another_identity() -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=row(profile_id=uuid4()))

    async def get() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            with pytest.raises(PersistenceUnavailableError):
                await SupabaseProfileRepository(gateway, context()).get_current(_USER_ID)

    asyncio.run(get())


def test_profile_list_maps_portuguese_role_and_total() -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            json={"items": [row(role="receptionist")], "total": 3},
        )

    async def search() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            result = await SupabaseProfileRepository(gateway, context()).search(
                ProfileSearchCriteria(role=UserRole.RECEPTIONIST)
            )
        assert result.total == 3
        assert result.items[0].role is UserRole.RECEPTIONIST

    asyncio.run(search())


def test_role_change_sends_reason_version_and_database_role() -> None:
    profile = domain_profile()
    profile.role = UserRole.READ_ONLY
    captured: dict[str, object] = {}
    returned_version = profile.updated_at + timedelta(seconds=1)

    def respond(request: httpx2.Request) -> httpx2.Response:
        captured.update(json.loads(request.content))
        return httpx2.Response(200, json={"updated_at": returned_version.isoformat()})

    async def change() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            result = await SupabaseProfileRepository(gateway, context()).change_role(
                profile,
                reason=AccessChangeReason("Mudança aprovada pela coordenação responsável"),
                expected_updated_at=profile.updated_at,
            )
        assert result == returned_version

    asyncio.run(change())
    assert captured["p_target_role"] == "read_only"
    assert captured["p_request_id"] == str(context().request_id)
    assert "p_email" not in captured


@pytest.mark.parametrize(
    ("message", "expected_error"),
    [
        ("profile_version_conflict", ProfileVersionConflictError),
        ("last_active_coordinator", LastActiveCoordinatorError),
        ("forbidden", PermissionDeniedError),
    ],
)
def test_stable_database_errors_are_translated(
    message: str,
    expected_error: type[Exception],
) -> None:
    status_code = 403 if message == "forbidden" else 409

    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status_code, json={"message": message})

    async def get() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            repository = SupabaseProfileRepository(gateway, context())
            with pytest.raises(expected_error):
                await repository.change_role(
                    domain_profile(),
                    reason=AccessChangeReason("Mudança aprovada pela coordenação responsável"),
                    expected_updated_at=domain_profile().updated_at,
                )

    asyncio.run(get())


def test_missing_profile_is_returned_as_none() -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(404, json={"message": "profile_not_found"})

    async def get() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            result = await SupabaseProfileRepository(gateway, context()).get_by_id(uuid4())
        assert result is None

    asyncio.run(get())


def test_remote_pending_active_profile_fails_closed() -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=row(role="pending", active=True))

    async def get() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            with pytest.raises(PersistenceUnavailableError):
                await SupabaseProfileRepository(gateway, context()).get_current(_USER_ID)

    asyncio.run(get())
