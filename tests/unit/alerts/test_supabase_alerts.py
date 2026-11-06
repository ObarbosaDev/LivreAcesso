"""Testes do transporte remoto de alertas de frequência."""

import asyncio
from uuid import uuid4

import httpx2
import pytest

from backend.app.modules.alerts.application.dtos import AlertInput
from backend.app.modules.alerts.domain.entities import AlertType
from backend.app.modules.alerts.infrastructure.supabase_repository import (
    SupabaseAlertRepository,
)
from backend.app.modules.identity.application.authentication import (
    AccessToken,
    AuthenticatedUser,
)
from backend.app.shared.application.exceptions import (
    PermissionDeniedError,
    PersistenceRejectedError,
    PersistenceUnavailableError,
)
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway

_PROJECT_URL = "https://example.supabase.co"


def context() -> RequestContext:
    return RequestContext(
        request_id=uuid4(),
        user=AuthenticatedUser(
            user_id=uuid4(),
            access_token=AccessToken("jwt-sintetico"),
            session_id=uuid4(),
            assurance_level="aal1",
        ),
    )


def test_list_open_sends_explicit_rpc() -> None:
    async def scenario() -> None:
        requests: list[httpx2.Request] = []

        async def handler(request: httpx2.Request) -> httpx2.Response:
            requests.append(request)
            return httpx2.Response(200, json=[])

        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
            repository = SupabaseAlertRepository(
                SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client), context()
            )
            assert await repository.list_open() == ()

        assert [request.url.path.rsplit("/", 1)[-1] for request in requests] == [
            "list_open_attendance_alerts"
        ]

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("status_code", "message", "expected"),
    [
        (403, "alert_forbidden", PermissionDeniedError),
        (400, "some_validation_error", PersistenceRejectedError),
        (500, "internal", PersistenceUnavailableError),
    ],
)
def test_alert_repository_maps_rpc_errors(
    status_code: int, message: str, expected: type[Exception]
) -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status_code, json={"message": message, "code": message})

    async def scenario() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            repository = SupabaseAlertRepository(
                SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client), context()
            )
            with pytest.raises(expected):
                await repository.list_open()

    asyncio.run(scenario())


def test_upsert_and_resolve_send_explicit_rpc_payloads() -> None:
    async def scenario() -> None:
        requests: list[httpx2.Request] = []

        async def handler(request: httpx2.Request) -> httpx2.Response:
            requests.append(request)
            return httpx2.Response(
                200,
                json={
                    "id": str(alert_id),
                    "student_id": str(student_id),
                    "class_id": str(class_id),
                    "alert_type": "faltas_consecutivas",
                    "title": "Faltas consecutivas",
                    "detail": "3 faltas seguidas",
                    "threshold": 3,
                    "status": "aberto",
                    "created_at": "2026-10-27T10:00:00Z",
                    "resolved_at": None,
                },
            )

        alert_id = uuid4()
        student_id = uuid4()
        class_id = uuid4()

        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
            repository = SupabaseAlertRepository(
                SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client), context()
            )
            await repository.upsert(
                AlertInput(
                    student_id=student_id,
                    class_id=class_id,
                    alert_type=AlertType.CONSECUTIVE_ABSENCES,
                    title="Faltas consecutivas",
                    detail="3 faltas seguidas",
                    threshold=3,
                )
            )
            await repository.resolve(alert_id)

        assert [request.url.path.rsplit("/", 1)[-1] for request in requests] == [
            "upsert_attendance_alert",
            "resolve_attendance_alert",
        ]

    asyncio.run(scenario())
