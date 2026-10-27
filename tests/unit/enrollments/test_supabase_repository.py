"""Testes do transporte remoto de matrículas."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx2
import pytest

from backend.app.modules.enrollments.domain.entities import Enrollment
from backend.app.modules.enrollments.domain.exceptions import (
    ClassCapacityReachedError,
    DuplicateEnrollmentError,
    EnrollmentNotFoundError,
    EnrollmentVersionConflictError,
)
from backend.app.modules.enrollments.infrastructure.supabase_repository import (
    SupabaseEnrollmentRepository,
)
from backend.app.modules.identity.application.authentication import AccessToken, AuthenticatedUser
from backend.app.shared.application.exceptions import PermissionDeniedError
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway

_PROJECT_URL = "https://project-ref.supabase.co"


def context() -> RequestContext:
    return RequestContext(
        request_id=uuid4(),
        user=AuthenticatedUser(
            user_id=uuid4(),
            access_token=AccessToken("jwt-sintetico"),
            session_id=None,
            assurance_level="aal1",
        ),
    )


def test_find_active_uses_explicit_rpc_and_request_jwt() -> None:
    student_id, class_id = uuid4(), uuid4()
    observed: list[httpx2.Request] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        observed.append(request)
        return httpx2.Response(
            200,
            json={
                "id": str(uuid4()),
                "student_id": str(student_id),
                "class_id": str(class_id),
                "status": "ativa",
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    async def scenario() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(
                "https://example.supabase.co", "publishable", http_client=client
            )
            context = RequestContext(
                user=AuthenticatedUser(
                    user_id=uuid4(),
                    access_token=AccessToken("token"),
                    session_id=None,
                    assurance_level="aal1",
                ),
                request_id=uuid4(),
            )
            result = await SupabaseEnrollmentRepository(gateway, context).find_active(
                student_id, class_id
            )
        assert result is not None
        assert observed[0].url.path.endswith("/rpc/get_active_enrollment")
        assert observed[0].headers["authorization"] == "Bearer token"

    asyncio.run(scenario())


def _row() -> dict[str, str]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid4()),
        "student_id": str(uuid4()),
        "class_id": str(uuid4()),
        "status": "ativa",
        "created_at": now,
        "updated_at": now,
    }


def test_enrollment_repository_maps_crud_list_and_occupancy() -> None:
    calls: list[str] = []
    row = _row()

    def respond(request: httpx2.Request) -> httpx2.Response:
        name = request.url.path.rsplit("/", maxsplit=1)[-1]
        calls.append(name)
        if name == "list_enrollments":
            return httpx2.Response(200, json={"items": [row], "total": 1})
        if name == "get_class_enrollment_occupancy":
            return httpx2.Response(200, json={"capacity": 10, "enrolled": 3, "available": 7})
        return httpx2.Response(200, json=row)

    async def scenario() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            repository = SupabaseEnrollmentRepository(
                SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client), context()
            )
            entity = Enrollment.create(student_id=uuid4(), class_id=uuid4())
            assert (await repository.add(entity)).status.value == "ativa"
            assert (await repository.get(entity.id)) is not None
            assert (await repository.update(entity, expected_updated_at=entity.updated_at)).id
            items, total = await repository.list(
                student_id=None, class_id=None, status=None, limit=10, offset=0
            )
            assert len(items) == total == 1
            assert await repository.occupancy(uuid4()) == (10, 3, 7)

    asyncio.run(scenario())
    assert calls == [
        "register_enrollment",
        "get_enrollment",
        "change_enrollment_status",
        "list_enrollments",
        "get_class_enrollment_occupancy",
    ]


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("duplicate_enrollment", DuplicateEnrollmentError),
        ("class_capacity_reached", ClassCapacityReachedError),
        ("enrollment_not_found", EnrollmentNotFoundError),
        ("enrollment_version_conflict", EnrollmentVersionConflictError),
        ("forbidden", PermissionDeniedError),
    ],
)
def test_enrollment_repository_maps_rpc_errors(message: str, expected: type[Exception]) -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(400, json={"message": message, "code": message})

    async def scenario() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            repository = SupabaseEnrollmentRepository(
                SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client), context()
            )
            if expected is EnrollmentNotFoundError:
                assert await repository.get(uuid4()) is None
            else:
                with pytest.raises(expected):
                    await repository.get(uuid4())

    asyncio.run(scenario())
