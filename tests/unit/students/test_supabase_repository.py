"""Testes do adaptador de alunos para as RPCs Supabase."""

import asyncio
import json
from datetime import UTC, date, datetime
from uuid import UUID

import httpx2
import pytest

from backend.app.modules.identity.application.authentication import AccessToken, AuthenticatedUser
from backend.app.modules.students.application.queries import StudentSearchCriteria
from backend.app.modules.students.domain.entities import Guardian, Student
from backend.app.modules.students.domain.exceptions import DuplicateCPFError
from backend.app.modules.students.domain.value_objects import CPF, Phone
from backend.app.modules.students.infrastructure.supabase_repository import (
    SupabaseStudentRepository,
)
from backend.app.shared.application.exceptions import (
    PermissionDeniedError,
    PersistenceUnavailableError,
)
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway

_PROJECT_URL = "https://project-ref.supabase.co"


def context() -> RequestContext:
    return RequestContext(
        request_id=UUID("00000000-0000-4000-8000-000000000001"),
        user=AuthenticatedUser(
            user_id=UUID("00000000-0000-4000-8000-000000000002"),
            access_token=AccessToken("jwt-sintetico"),
            session_id=None,
            assurance_level="aal1",
        ),
    )


def student() -> Student:
    return Student.register(
        full_name="Sophia Almeida Ramos",
        cpf=CPF("52998224725"),
        birth_date=date(2015, 5, 10),
        guardian=Guardian(
            full_name="Camila Ramos",
            phone=Phone("61999991234"),
            email="camila@example.com",
        ),
    )


def test_add_uses_transactional_rpc_with_generated_ids() -> None:
    current_student = student()
    captured_payload: dict[str, object] = {}

    def respond(request: httpx2.Request) -> httpx2.Response:
        captured_payload.update(json.loads(request.content))
        return httpx2.Response(200, json=str(current_student.id))

    async def add() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            repository = SupabaseStudentRepository(gateway, context())
            await repository.add(current_student)

    asyncio.run(add())

    assert captured_payload["p_student_id"] == str(current_student.id)
    assert captured_payload["p_guardian_id"] == str(current_student.guardian.id)
    assert captured_payload["p_request_id"] == str(context().request_id)
    assert captured_payload["p_relationship"] == "responsible_contact"


def test_search_maps_only_masked_projection() -> None:
    row = {
        "id": "00000000-0000-4000-8000-000000000010",
        "full_name": "Sophia Almeida Ramos",
        "cpf_masked": "***.***.***-25",
        "birth_date": "2015-05-10",
        "age": 11,
        "status": "active",
        "guardian_name": "Camila Ramos",
        "guardian_phone_masked": "(61) *****-1234",
        "created_at": datetime(2026, 10, 21, tzinfo=UTC).isoformat(),
    }

    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"items": [row], "total": 1})

    async def search() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            result = await SupabaseStudentRepository(gateway, context()).search(
                StudentSearchCriteria(query="Sophia")
            )
        assert result.total == 1
        assert result.items[0].cpf_masked == "***.***.***-25"
        assert result.items[0].guardian_phone_masked == "(61) *****-1234"

    asyncio.run(search())


@pytest.mark.parametrize(
    ("status_code", "body", "expected_error"),
    [
        (403, {"code": "42501", "message": "forbidden"}, PermissionDeniedError),
        (409, {"code": "23505", "message": "duplicate_cpf"}, DuplicateCPFError),
        (503, {"message": "internal_detail"}, PersistenceUnavailableError),
    ],
)
def test_rpc_errors_are_translated(
    status_code: int,
    body: dict[str, str],
    expected_error: type[Exception],
) -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status_code, json=body)

    async def add() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            repository = SupabaseStudentRepository(gateway, context())
            with pytest.raises(expected_error):
                await repository.add(student())

    asyncio.run(add())


def test_unexpected_list_shape_fails_closed() -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"raw": "unexpected"})

    async def search() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            repository = SupabaseStudentRepository(gateway, context())
            with pytest.raises(PersistenceUnavailableError):
                await repository.search(StudentSearchCriteria())

    asyncio.run(search())


def test_empty_page_preserves_total_number_of_matches() -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"items": [], "total": 37})

    async def search() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            result = await SupabaseStudentRepository(gateway, context()).search(
                StudentSearchCriteria(offset=100, limit=25)
            )
        assert result.items == ()
        assert result.total == 37

    asyncio.run(search())
