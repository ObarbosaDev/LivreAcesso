"""Integração HTTP completa da API com as RPCs Supabase simuladas."""

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import httpx2
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.container import ApplicationContainer
from backend.app.main import create_app
from backend.app.modules.identity.application.authentication import (
    AccessToken,
    AuthenticatedUser,
)
from backend.app.shared.application.event_bus import EventBus
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway

_PROJECT_URL = "https://project-ref.supabase.co"
_ACCESS_TOKEN = "jwt-sintetico-integracao"
_USER_ID = UUID("00000000-0000-4000-8000-000000000001")


class IntegrationTokenVerifier:
    """Double que preserva o token para validar seu encaminhamento à RPC."""

    async def verify(self, raw_access_token: str) -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id=_USER_ID,
            access_token=AccessToken(raw_access_token),
            session_id=None,
            assurance_level="aal1",
        )


def settings() -> Settings:
    return Settings(
        app_name="Livre Acesso Integration",
        version="test",
        environment="test",
        host="127.0.0.1",
        port=8000,
        debug=False,
        api_prefix="/api/v1",
        cors_origins=(),
        supabase_url=_PROJECT_URL,
        supabase_publishable_key="publishable-test",
    )


def build_application(
    handler: Callable[[httpx2.Request], httpx2.Response],
) -> tuple[FastAPI, httpx2.AsyncClient]:
    transport = httpx2.MockTransport(handler)
    http_client = httpx2.AsyncClient(transport=transport)
    gateway = SupabaseRPCGateway(
        _PROJECT_URL,
        "publishable-test",
        http_client=http_client,
    )
    container = ApplicationContainer(
        event_bus=EventBus(),
        in_memory_student_store=None,
        supabase_gateway=gateway,
    )
    application = create_app(
        settings=settings(),
        container=container,
        token_verifier=IntegrationTokenVerifier(),
    )
    return application, http_client


def student_payload() -> dict[str, object]:
    return {
        "full_name": "Sophia Almeida Ramos",
        "cpf": "529.982.247-25",
        "birth_date": "2015-05-10",
        "guardian": {
            "full_name": "Camila Ramos",
            "phone": "(61) 99999-1234",
            "email": "camila@example.com",
        },
    }


def test_authenticated_request_crosses_api_and_supabase_adapter() -> None:
    captured_requests: list[dict[str, object]] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        payload = json.loads(request.content)
        captured_requests.append(
            {
                "path": request.url.path,
                "authorization": request.headers["Authorization"],
                "request_id": request.headers["X-Request-ID"],
                "payload": payload,
            }
        )
        if request.url.path.endswith("/register_student_with_guardian"):
            return httpx2.Response(200, json=payload["p_student_id"])
        return httpx2.Response(
            200,
            json={
                "items": [
                    {
                        "id": "00000000-0000-4000-8000-000000000010",
                        "full_name": "Sophia Almeida Ramos",
                        "cpf_masked": "***.***.***-25",
                        "birth_date": "2015-05-10",
                        "age": 11,
                        "status": "active",
                        "guardian_name": "Camila Ramos",
                        "guardian_phone_masked": "(61) *****-1234",
                        "created_at": datetime(2026, 10, 21, tzinfo=UTC).isoformat(),
                        "updated_at": datetime(2026, 10, 21, tzinfo=UTC).isoformat(),
                    }
                ],
                "total": 1,
            },
        )

    application, http_client = build_application(respond)
    headers = {"Authorization": f"Bearer {_ACCESS_TOKEN}"}

    with TestClient(application, headers=headers) as client:
        created = client.post("/api/v1/students", json=student_payload())
        listed = client.get("/api/v1/students?query=Sophia&page_size=10")

    asyncio.run(http_client.aclose())

    assert created.status_code == 201
    assert created.json()["cpf_masked"] == "***.***.***-25"
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["guardian_phone_masked"] == "(61) *****-1234"
    assert len(captured_requests) == 2
    assert all(
        request["authorization"] == f"Bearer {_ACCESS_TOKEN}" for request in captured_requests
    )
    assert all(UUID(str(request["request_id"])) for request in captured_requests)


def test_database_permission_error_becomes_accessible_problem() -> None:
    def deny(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(403, json={"code": "42501", "message": "forbidden"})

    application, http_client = build_application(deny)

    with TestClient(
        application,
        headers={"Authorization": f"Bearer {_ACCESS_TOKEN}"},
    ) as client:
        response = client.get("/api/v1/students")

    asyncio.run(http_client.aclose())

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "permission_denied"
    assert response.json()["title"] == "Operação não permitida"


def test_supabase_management_rpc_flow_preserves_version_and_status() -> None:
    student_id = "00000000-0000-4000-8000-000000000010"
    guardian_id = "00000000-0000-4000-8000-000000000011"
    initial_version = datetime(2026, 10, 21, 18, 0, tzinfo=UTC)
    updated_version = datetime(2026, 10, 21, 18, 1, tzinfo=UTC)
    inactive_version = datetime(2026, 10, 21, 18, 2, tzinfo=UTC)
    rpc_names: list[str] = []

    def detail_payload(*, status: str, updated_at: datetime) -> dict[str, object]:
        return {
            "id": student_id,
            "full_name": "Sophia Almeida Ramos",
            "cpf": "52998224725",
            "birth_date": "2015-05-10",
            "status": status,
            "guardian": {
                "id": guardian_id,
                "full_name": "Camila Ramos",
                "phone": "61999991234",
                "email": "camila@example.com",
            },
            "created_at": initial_version.isoformat(),
            "updated_at": updated_at.isoformat(),
        }

    current_status = "active"
    current_version = initial_version

    def respond(request: httpx2.Request) -> httpx2.Response:
        nonlocal current_status, current_version
        rpc_name = request.url.path.rsplit("/", maxsplit=1)[-1]
        rpc_names.append(rpc_name)

        if rpc_name == "get_student_detail":
            return httpx2.Response(
                200,
                json=detail_payload(status=current_status, updated_at=current_version),
            )
        if rpc_name == "update_student_with_guardian":
            current_version = updated_version
            return httpx2.Response(200, json={"updated_at": current_version.isoformat()})
        if rpc_name == "change_student_status":
            payload = json.loads(request.content)
            current_status = payload["p_target_status"]
            current_version = inactive_version
            return httpx2.Response(200, json={"updated_at": current_version.isoformat()})
        return httpx2.Response(404, json={"message": "function_not_found"})

    application, http_client = build_application(respond)
    headers = {"Authorization": f"Bearer {_ACCESS_TOKEN}"}

    with TestClient(application, headers=headers) as client:
        detail = client.get(f"/api/v1/students/{student_id}")
        updated = client.put(
            f"/api/v1/students/{student_id}",
            json={
                "expected_updated_at": initial_version.isoformat(),
                "full_name": "Sophia Almeida Ramos da Silva",
                "birth_date": "2015-05-10",
                "guardian": {
                    "full_name": "Camila Ramos",
                    "phone": "61988881234",
                    "email": "camila@example.com",
                },
            },
        )
        inactive = client.post(
            f"/api/v1/students/{student_id}/deactivate",
            json={
                "expected_updated_at": updated_version.isoformat(),
                "reason": "Solicitação confirmada pela coordenação responsável",
            },
        )

    asyncio.run(http_client.aclose())

    assert detail.status_code == 200
    assert detail.json()["cpf_masked"] == "***.***.***-25"
    assert updated.status_code == 200
    assert updated.json()["updated_at"] == updated_version.isoformat().replace("+00:00", "Z")
    assert inactive.status_code == 200
    assert inactive.json()["status"] == "inativo"
    assert rpc_names == [
        "get_student_detail",
        "get_student_detail",
        "update_student_with_guardian",
        "get_student_detail",
        "change_student_status",
    ]
