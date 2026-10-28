"""Testes do transporte remoto de frequência."""

import asyncio
from datetime import date
from uuid import uuid4

import httpx2

from backend.app.modules.attendance.application.dtos import (
    AttendanceMarkInput,
    OpenAttendanceInput,
)
from backend.app.modules.attendance.domain.entities import AttendanceStatus
from backend.app.modules.attendance.infrastructure.supabase_repository import (
    SupabaseAttendanceRepository,
)
from backend.app.modules.identity.application.authentication import (
    AccessToken,
    AuthenticatedUser,
)
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway


def request_context() -> RequestContext:
    return RequestContext(
        request_id=uuid4(),
        user=AuthenticatedUser(
            user_id=uuid4(),
            access_token=AccessToken("jwt-sintetico"),
            session_id=uuid4(),
            assurance_level="aal1",
        ),
    )


def test_remote_attendance_sends_explicit_rpc_payloads() -> None:
    async def scenario() -> None:
        requests: list[httpx2.Request] = []

        async def handler(request: httpx2.Request) -> httpx2.Response:
            requests.append(request)
            name = request.url.path.rsplit("/", 1)[-1]
            if name == "open_attendance_session":
                return httpx2.Response(
                    200,
                    json={
                        "id": str(uuid4()),
                        "class_id": str(class_id),
                        "session_date": "2026-10-27",
                        "status": "aberta",
                        "closed_at": None,
                    },
                )
            return httpx2.Response(
                200,
                json={
                    "id": str(session_id),
                    "class_id": str(class_id),
                    "session_date": "2026-10-27",
                    "status": "fechada",
                    "closed_at": "2026-10-27T20:00:00Z",
                },
            )

        class_id = uuid4()
        session_id = uuid4()
        client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
        gateway = SupabaseRPCGateway(
            "https://example.supabase.co", "publishable", http_client=client
        )
        context: RequestContext = request_context()
        repository = SupabaseAttendanceRepository(gateway, context)

        opened = await repository.open(
            OpenAttendanceInput(class_id=class_id, session_date=date(2026, 10, 27))
        )
        await repository.record(
            opened.id,
            (AttendanceMarkInput(enrollment_id=uuid4(), status=AttendanceStatus.PRESENT),),
        )
        await repository.close(session_id)

        assert [request.url.path.rsplit("/", 1)[-1] for request in requests] == [
            "open_attendance_session",
            "record_attendance",
            "close_attendance_session",
        ]
        await client.aclose()

    asyncio.run(scenario())
