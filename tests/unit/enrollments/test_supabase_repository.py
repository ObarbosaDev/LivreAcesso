"""Testes do transporte remoto de matrículas."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx2

from backend.app.modules.enrollments.infrastructure.supabase_repository import (
    SupabaseEnrollmentRepository,
)
from backend.app.modules.identity.application.authentication import AccessToken, AuthenticatedUser
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway


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
