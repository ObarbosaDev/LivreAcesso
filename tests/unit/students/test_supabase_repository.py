"""Testes do adaptador de alunos para as RPCs Supabase."""

import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import httpx2
import pytest

from backend.app.modules.identity.application.authentication import (
    AccessToken,
    AuthenticatedUser,
    InvalidAccessTokenError,
)
from backend.app.modules.students.application.queries import StudentSearchCriteria
from backend.app.modules.students.domain.entities import Guardian, Student, StudentStatus
from backend.app.modules.students.domain.exceptions import (
    DuplicateCPFError,
    GuardianAlreadyLinkedError,
    GuardianNotFoundError,
    GuardianVersionConflictError,
    InvalidGuardianUnlinkReasonError,
    PrimaryGuardianRequiredError,
    StudentNotFoundError,
    StudentVersionConflictError,
)
from backend.app.modules.students.domain.value_objects import (
    CPF,
    Phone,
    StatusChangeReason,
)
from backend.app.modules.students.infrastructure.supabase_repository import (
    SupabaseStudentRepository,
)
from backend.app.shared.application.exceptions import (
    PermissionDeniedError,
    PersistenceRejectedError,
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

    persisted_at = datetime(2026, 10, 21, 18, 0, tzinfo=UTC)

    def respond(request: httpx2.Request) -> httpx2.Response:
        captured_payload.update(json.loads(request.content))
        return httpx2.Response(
            200,
            json={
                "id": str(current_student.id),
                "created_at": persisted_at.isoformat(),
                "updated_at": persisted_at.isoformat(),
            },
        )

    async def add() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            repository = SupabaseStudentRepository(gateway, context())
            version = await repository.add(current_student)
        assert version.created_at == persisted_at
        assert version.updated_at == persisted_at

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
        "updated_at": datetime(2026, 10, 21, tzinfo=UTC).isoformat(),
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
        (401, {"message": "invalid_token"}, InvalidAccessTokenError),
        (403, {"code": "42501", "message": "forbidden"}, PermissionDeniedError),
        (409, {"code": "23505", "message": "duplicate_cpf"}, DuplicateCPFError),
        (409, {"message": "guardian_already_linked"}, GuardianAlreadyLinkedError),
        (404, {"message": "guardian_not_found"}, GuardianNotFoundError),
        (409, {"message": "primary_guardian_required"}, PrimaryGuardianRequiredError),
        (409, {"message": "guardian_version_conflict"}, GuardianVersionConflictError),
        (422, {"message": "invalid_guardian_unlink_reason"}, InvalidGuardianUnlinkReasonError),
        (404, {"message": "student_not_found"}, StudentNotFoundError),
        (409, {"message": "student_version_conflict"}, StudentVersionConflictError),
        (422, {"message": "rejected"}, PersistenceRejectedError),
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


def detail_row(current_student: Student) -> dict[str, object]:
    return {
        "id": str(current_student.id),
        "full_name": current_student.full_name,
        "cpf": current_student.cpf.value,
        "birth_date": current_student.birth_date.isoformat(),
        "status": "active",
        "guardian": {
            "id": str(current_student.guardian.id),
            "full_name": current_student.guardian.full_name,
            "phone": current_student.guardian.phone.value,
            "email": current_student.guardian.email,
        },
        "created_at": current_student.created_at.isoformat(),
        "updated_at": current_student.updated_at.isoformat(),
    }


def test_get_by_id_rehydrates_valid_aggregate() -> None:
    current_student = student()

    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=detail_row(current_student))

    async def get() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            restored = await SupabaseStudentRepository(gateway, context()).get_by_id(
                current_student.id
            )
        assert restored == current_student

    asyncio.run(get())


def test_get_by_id_returns_none_for_missing_student() -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(404, json={"message": "student_not_found"})

    async def get() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            restored = await SupabaseStudentRepository(gateway, context()).get_by_id(student().id)
        assert restored is None

    asyncio.run(get())


def test_update_sends_expected_version_and_returns_database_version() -> None:
    current_student = student()
    expected_version = current_student.updated_at
    database_version = expected_version + timedelta(microseconds=1)
    captured: dict[str, object] = {}

    def respond(request: httpx2.Request) -> httpx2.Response:
        captured.update(json.loads(request.content))
        return httpx2.Response(200, json={"updated_at": database_version.isoformat()})

    async def update() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            returned_version = await SupabaseStudentRepository(gateway, context()).update(
                current_student,
                expected_updated_at=expected_version,
            )
        assert returned_version == database_version

    asyncio.run(update())
    assert captured["p_expected_updated_at"] == expected_version.isoformat()
    assert captured["p_student_id"] == str(current_student.id)
    assert "p_cpf" not in captured


def test_status_change_sends_reason_only_to_transactional_rpc() -> None:
    current_student = student()
    current_student.status = StudentStatus.INACTIVE
    captured: dict[str, object] = {}

    def respond(request: httpx2.Request) -> httpx2.Response:
        captured.update(json.loads(request.content))
        return httpx2.Response(200, json={"updated_at": current_student.updated_at.isoformat()})

    async def change() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            await SupabaseStudentRepository(gateway, context()).change_status(
                current_student,
                reason=StatusChangeReason("Solicitação confirmada pela coordenação"),
                expected_updated_at=current_student.updated_at,
            )

    asyncio.run(change())
    assert captured["p_target_status"] == "inactive"
    assert captured["p_reason"] == "Solicitação confirmada pela coordenação"
