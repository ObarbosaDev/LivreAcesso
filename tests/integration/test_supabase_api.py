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
from backend.app.modules.operations.infrastructure.supabase_health import (
    SupabaseReadinessProbe,
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
        readiness_probe=SupabaseReadinessProbe(gateway),
        in_memory_profile_store=None,
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
        if request.url.path.endswith("/register_student_with_guardian_v2"):
            persisted_at = datetime(2026, 10, 21, 18, 0, tzinfo=UTC).isoformat()
            return httpx2.Response(
                200,
                json={
                    "id": payload["p_student_id"],
                    "created_at": persisted_at,
                    "updated_at": persisted_at,
                },
            )
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
        if rpc_name == "update_student":
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
        "update_student",
        "get_student_detail",
        "change_student_status",
    ]


def test_readiness_uses_public_health_rpc_without_user_token() -> None:
    captured_headers: dict[str, str] = {}

    def healthy(request: httpx2.Request) -> httpx2.Response:
        captured_headers.update(dict(request.headers))
        assert request.url.path.endswith("/health_check")
        return httpx2.Response(200, json={"status": "ok"})

    application, http_client = build_application(healthy)

    with TestClient(application) as client:
        response = client.get("/health/ready")

    asyncio.run(http_client.aclose())

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert "authorization" not in captured_headers
    assert captured_headers["apikey"] == "publishable-test"


def test_readiness_failure_returns_sanitized_503() -> None:
    def unavailable(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(503, json={"message": "internal_database_detail"})

    application, http_client = build_application(unavailable)

    with TestClient(application) as client:
        response = client.get("/health/ready")

    asyncio.run(http_client.aclose())

    assert response.status_code == 503
    assert response.json()["code"] == "service_not_ready"
    assert response.headers["Retry-After"] == "30"
    assert "internal_database_detail" not in response.text


def test_profile_management_crosses_fastapi_and_supabase_rpcs() -> None:
    target_id = "00000000-0000-4000-8000-000000000020"
    created_at = datetime(2026, 10, 22, tzinfo=UTC)
    actor_version = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
    target_version = datetime(2026, 10, 23, 10, 1, tzinfo=UTC)
    role_version = datetime(2026, 10, 23, 10, 2, tzinfo=UTC)
    active_version = datetime(2026, 10, 23, 10, 3, tzinfo=UTC)
    target_role = "pending"
    target_active = False
    target_updated_at = target_version
    rpc_names: list[str] = []

    def profile_row(
        profile_id: str,
        name: str,
        role: str,
        active: bool,
        updated_at: datetime,
    ) -> dict[str, object]:
        return {
            "id": profile_id,
            "full_name": name,
            "role": role,
            "active": active,
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat(),
        }

    def respond(request: httpx2.Request) -> httpx2.Response:
        nonlocal target_role, target_active, target_updated_at
        rpc_name = request.url.path.rsplit("/", maxsplit=1)[-1]
        rpc_names.append(rpc_name)
        assert request.headers["Authorization"] == f"Bearer {_ACCESS_TOKEN}"

        if rpc_name == "get_my_profile":
            return httpx2.Response(
                200,
                json=profile_row(
                    str(_USER_ID),
                    "Coordenação Teste",
                    "coordinator",
                    True,
                    actor_version,
                ),
            )
        if rpc_name == "list_profiles":
            return httpx2.Response(
                200,
                json={
                    "items": [
                        profile_row(
                            target_id,
                            "Nova Recepção",
                            target_role,
                            target_active,
                            target_updated_at,
                        )
                    ],
                    "total": 1,
                },
            )
        if rpc_name == "get_profile_detail":
            return httpx2.Response(
                200,
                json=profile_row(
                    target_id,
                    "Nova Recepção",
                    target_role,
                    target_active,
                    target_updated_at,
                ),
            )
        if rpc_name == "change_profile_role":
            target_role = "receptionist"
            target_updated_at = role_version
            return httpx2.Response(200, json={"updated_at": role_version.isoformat()})
        if rpc_name == "change_profile_activation":
            target_active = True
            target_updated_at = active_version
            return httpx2.Response(200, json={"updated_at": active_version.isoformat()})
        return httpx2.Response(404, json={"message": "function_not_found"})

    application, http_client = build_application(respond)

    with TestClient(
        application,
        headers={"Authorization": f"Bearer {_ACCESS_TOKEN}"},
    ) as client:
        current = client.get("/api/v1/me")
        listed = client.get("/api/v1/profiles?role=pendente")
        assigned = client.post(
            f"/api/v1/profiles/{target_id}/role",
            json={
                "expected_updated_at": target_version.isoformat(),
                "role": "recepcao",
                "reason": "Acesso aprovado pela coordenação responsável",
            },
        )
        activated = client.post(
            f"/api/v1/profiles/{target_id}/activate",
            json={
                "expected_updated_at": role_version.isoformat(),
                "reason": "Acesso aprovado pela coordenação responsável",
            },
        )

    asyncio.run(http_client.aclose())

    assert current.status_code == 200
    assert current.json()["role"] == "coordenador"
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert assigned.status_code == 200
    assert assigned.json()["role"] == "recepcao"
    assert assigned.json()["active"] is False
    assert activated.status_code == 200
    assert activated.json()["active"] is True
    assert "profiles:manage" not in activated.json()["capabilities"]
    assert rpc_names == [
        "get_my_profile",
        "get_my_profile",
        "list_profiles",
        "get_my_profile",
        "get_profile_detail",
        "change_profile_role",
        "get_my_profile",
        "get_profile_detail",
        "change_profile_activation",
    ]


def test_profile_list_denial_happens_before_admin_rpc() -> None:
    rpc_names: list[str] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        rpc_name = request.url.path.rsplit("/", maxsplit=1)[-1]
        rpc_names.append(rpc_name)
        return httpx2.Response(
            200,
            json={
                "id": str(_USER_ID),
                "full_name": "Recepção Teste",
                "role": "receptionist",
                "active": True,
                "created_at": datetime(2026, 10, 22, tzinfo=UTC).isoformat(),
                "updated_at": datetime(2026, 10, 23, tzinfo=UTC).isoformat(),
            },
        )

    application, http_client = build_application(respond)

    with TestClient(
        application,
        headers={"Authorization": f"Bearer {_ACCESS_TOKEN}"},
    ) as client:
        response = client.get("/api/v1/profiles")

    asyncio.run(http_client.aclose())

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert rpc_names == ["get_my_profile"]


def test_guardian_management_crosses_fastapi_and_supabase_rpcs() -> None:
    student_id = "00000000-0000-4000-8000-000000000030"
    initial_guardian_id = "00000000-0000-4000-8000-000000000031"
    new_guardian_id: str | None = None
    student_version = datetime(2026, 10, 22, 19, 0, tzinfo=UTC)
    guardian_version = datetime(2026, 10, 22, 19, 1, tzinfo=UTC)
    rpc_names: list[str] = []

    def guardian_detail(
        guardian_id: str,
        *,
        relationship: str,
        is_primary: bool,
        changed: bool,
    ) -> dict[str, object]:
        return {
            "student_id": student_id,
            "student_updated_at": student_version.isoformat(),
            "id": guardian_id,
            "full_name": "Roberto Almeida",
            "phone": "61988881234",
            "email": "roberto@example.com",
            "relationship": relationship,
            "is_primary": is_primary,
            "receives_communications": True,
            "active": True,
            "linked_at": datetime(2026, 10, 22, 18, 0, tzinfo=UTC).isoformat(),
            "guardian_updated_at": guardian_version.isoformat(),
            "changed": changed,
        }

    def respond(request: httpx2.Request) -> httpx2.Response:
        nonlocal new_guardian_id, student_version, guardian_version
        rpc_name = request.url.path.rsplit("/", maxsplit=1)[-1]
        rpc_names.append(rpc_name)
        payload = json.loads(request.content)
        assert request.headers["Authorization"] == f"Bearer {_ACCESS_TOKEN}"

        if rpc_name == "list_student_guardians":
            return httpx2.Response(
                200,
                json={
                    "student_id": student_id,
                    "student_updated_at": student_version.isoformat(),
                    "items": [
                        {
                            "id": initial_guardian_id,
                            "full_name": "Camila Ramos",
                            "phone_masked": "(61) *****-1234",
                            "email_masked": "c***@example.com",
                            "relationship": "responsible_contact",
                            "is_primary": True,
                            "receives_communications": True,
                            "linked_at": student_version.isoformat(),
                            "guardian_updated_at": guardian_version.isoformat(),
                        }
                    ],
                },
            )
        if rpc_name == "add_student_guardian":
            new_guardian_id = str(payload["p_guardian_id"])
            student_version = datetime(2026, 10, 22, 19, 2, tzinfo=UTC)
            return httpx2.Response(
                200,
                json=guardian_detail(
                    new_guardian_id,
                    relationship=str(payload["p_relationship"]),
                    is_primary=False,
                    changed=True,
                ),
            )
        if rpc_name == "update_student_guardian":
            guardian_version = datetime(2026, 10, 22, 19, 3, tzinfo=UTC)
            student_version = datetime(2026, 10, 22, 19, 4, tzinfo=UTC)
            assert new_guardian_id is not None
            return httpx2.Response(
                200,
                json=guardian_detail(
                    new_guardian_id,
                    relationship=str(payload["p_relationship"]),
                    is_primary=False,
                    changed=True,
                ),
            )
        if rpc_name == "set_primary_student_guardian":
            student_version = datetime(2026, 10, 22, 19, 5, tzinfo=UTC)
            assert new_guardian_id is not None
            return httpx2.Response(
                200,
                json=guardian_detail(
                    new_guardian_id,
                    relationship="parent",
                    is_primary=True,
                    changed=True,
                ),
            )
        if rpc_name == "unlink_student_guardian":
            student_version = datetime(2026, 10, 22, 19, 6, tzinfo=UTC)
            return httpx2.Response(
                200,
                json={
                    "student_id": student_id,
                    "guardian_id": initial_guardian_id,
                    "student_updated_at": student_version.isoformat(),
                    "changed": True,
                },
            )
        return httpx2.Response(404, json={"message": "function_not_found"})

    application, http_client = build_application(respond)

    with TestClient(
        application,
        headers={"Authorization": f"Bearer {_ACCESS_TOKEN}"},
    ) as client:
        listed = client.get(f"/api/v1/students/{student_id}/guardians")
        added = client.post(
            f"/api/v1/students/{student_id}/guardians",
            json={
                "expected_student_updated_at": listed.json()["student_updated_at"],
                "relationship": "responsavel_legal",
                "guardian": {
                    "full_name": "Roberto Almeida",
                    "phone": "61988881234",
                    "email": "roberto@example.com",
                },
            },
        )
        updated = client.put(
            f"/api/v1/students/{student_id}/guardians/{added.json()['id']}",
            json={
                "expected_student_updated_at": added.json()["student_updated_at"],
                "expected_guardian_updated_at": added.json()["guardian_updated_at"],
                "full_name": "Roberto Almeida",
                "phone": "61988881234",
                "email": "roberto@example.com",
                "relationship": "pai_ou_mae",
                "receives_communications": True,
            },
        )
        promoted = client.post(
            f"/api/v1/students/{student_id}/guardians/{added.json()['id']}/primary",
            json={"expected_student_updated_at": updated.json()["student_updated_at"]},
        )
        unlinked = client.post(
            f"/api/v1/students/{student_id}/guardians/{initial_guardian_id}/unlink",
            json={
                "expected_student_updated_at": promoted.json()["student_updated_at"],
                "reason": "Vínculo anterior confirmado como incorreto",
            },
        )

    asyncio.run(http_client.aclose())

    assert listed.status_code == 200
    assert "61999991234" not in listed.text
    assert added.status_code == 201
    assert added.json()["relationship"] == "responsavel_legal"
    assert updated.status_code == 200
    assert updated.json()["relationship"] == "pai_ou_mae"
    assert promoted.status_code == 200
    assert promoted.json()["is_primary"] is True
    assert unlinked.status_code == 200
    assert rpc_names == [
        "list_student_guardians",
        "add_student_guardian",
        "update_student_guardian",
        "set_primary_student_guardian",
        "unlink_student_guardian",
    ]
