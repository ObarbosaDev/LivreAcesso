"""Testes do adaptador Supabase para responsáveis múltiplos."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx2
import pytest

from backend.app.modules.identity.application.authentication import AccessToken, AuthenticatedUser
from backend.app.modules.students.domain.entities import Guardian, GuardianRelationship
from backend.app.modules.students.domain.exceptions import (
    GuardianAlreadyLinkedError,
    GuardianNotFoundError,
    GuardianVersionConflictError,
    PrimaryGuardianRequiredError,
)
from backend.app.modules.students.domain.value_objects import GuardianUnlinkReason, Phone
from backend.app.modules.students.infrastructure.supabase_repository import (
    SupabaseStudentRepository,
)
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway

_PROJECT_URL = "https://project-ref.supabase.co"
_STUDENT_ID = UUID("00000000-0000-4000-8000-000000000010")
_GUARDIAN_ID = UUID("00000000-0000-4000-8000-000000000011")
_REQUEST_ID = UUID("00000000-0000-4000-8000-000000000012")
_STUDENT_VERSION = datetime(2026, 10, 22, 18, 0, tzinfo=UTC)
_GUARDIAN_VERSION = datetime(2026, 10, 22, 18, 1, tzinfo=UTC)


def context() -> RequestContext:
    return RequestContext(
        request_id=_REQUEST_ID,
        user=AuthenticatedUser(
            user_id=UUID("00000000-0000-4000-8000-000000000001"),
            access_token=AccessToken("jwt-sintetico"),
            session_id=None,
            assurance_level="aal1",
        ),
    )


def detail_row(*, changed: bool | None = None) -> dict[str, object]:
    row: dict[str, object] = {
        "student_id": str(_STUDENT_ID),
        "student_updated_at": _STUDENT_VERSION.isoformat(),
        "id": str(_GUARDIAN_ID),
        "full_name": "Camila Ramos",
        "phone": "61999991234",
        "email": "camila@example.com",
        "relationship": "parent",
        "is_primary": True,
        "receives_communications": True,
        "active": True,
        "linked_at": _STUDENT_VERSION.isoformat(),
        "guardian_updated_at": _GUARDIAN_VERSION.isoformat(),
    }
    if changed is not None:
        row["changed"] = changed
    return row


def test_list_is_masked_and_detail_is_rehydrated() -> None:
    rpc_names: list[str] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        rpc_name = request.url.path.rsplit("/", maxsplit=1)[-1]
        rpc_names.append(rpc_name)
        if rpc_name == "list_student_guardians":
            return httpx2.Response(
                200,
                json={
                    "student_id": str(_STUDENT_ID),
                    "student_updated_at": _STUDENT_VERSION.isoformat(),
                    "items": [
                        {
                            "id": str(_GUARDIAN_ID),
                            "full_name": "Camila Ramos",
                            "phone_masked": "(61) *****-1234",
                            "email_masked": "c***@example.com",
                            "relationship": "parent",
                            "is_primary": True,
                            "receives_communications": True,
                            "linked_at": _STUDENT_VERSION.isoformat(),
                            "guardian_updated_at": _GUARDIAN_VERSION.isoformat(),
                        }
                    ],
                },
            )
        return httpx2.Response(200, json=detail_row())

    async def scenario() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            repository = SupabaseStudentRepository(gateway, context())
            listed = await repository.list_guardians(_STUDENT_ID)
            detail = await repository.get_guardian(_STUDENT_ID, _GUARDIAN_ID)

        assert listed.items[0].phone_masked == "(61) *****-1234"
        assert listed.items[0].relationship is GuardianRelationship.PARENT
        assert detail.link.guardian.phone.value == "61999991234"
        assert detail.link.guardian_updated_at == _GUARDIAN_VERSION

    asyncio.run(scenario())
    assert rpc_names == ["list_student_guardians", "get_student_guardian_detail"]


def test_mutations_send_versions_relationship_and_private_reason() -> None:
    captured: list[tuple[str, dict[str, object]]] = []
    next_student_version = _STUDENT_VERSION + timedelta(minutes=1)

    def respond(request: httpx2.Request) -> httpx2.Response:
        rpc_name = request.url.path.rsplit("/", maxsplit=1)[-1]
        payload = json.loads(request.content)
        captured.append((rpc_name, payload))
        if rpc_name == "unlink_student_guardian":
            return httpx2.Response(
                200,
                json={
                    "student_id": str(_STUDENT_ID),
                    "guardian_id": str(_GUARDIAN_ID),
                    "student_updated_at": next_student_version.isoformat(),
                    "changed": True,
                },
            )
        row = detail_row(changed=True)
        row["student_updated_at"] = next_student_version.isoformat()
        row["is_primary"] = rpc_name == "set_primary_student_guardian"
        return httpx2.Response(200, json=row)

    async def scenario() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            repository = SupabaseStudentRepository(gateway, context())
            guardian = Guardian(
                id=_GUARDIAN_ID,
                full_name="Camila Ramos",
                phone=Phone("61999991234"),
                email="camila@example.com",
            )
            added = await repository.add_guardian(
                _STUDENT_ID,
                guardian=guardian,
                existing_guardian_id=None,
                relationship=GuardianRelationship.PARENT,
                make_primary=False,
                receives_communications=True,
                expected_student_updated_at=_STUDENT_VERSION,
            )
            await repository.update_guardian(
                _STUDENT_ID,
                guardian,
                relationship=GuardianRelationship.LEGAL_GUARDIAN,
                receives_communications=False,
                expected_student_updated_at=added.snapshot.student_updated_at,
                expected_guardian_updated_at=_GUARDIAN_VERSION,
            )
            await repository.set_primary_guardian(
                _STUDENT_ID,
                _GUARDIAN_ID,
                expected_student_updated_at=next_student_version,
            )
            unlinked = await repository.unlink_guardian(
                _STUDENT_ID,
                _GUARDIAN_ID,
                reason=GuardianUnlinkReason("Vínculo confirmado como incorreto"),
                expected_student_updated_at=next_student_version,
            )
            assert unlinked.changed is True

    asyncio.run(scenario())
    assert [name for name, _ in captured] == [
        "add_student_guardian",
        "update_student_guardian",
        "set_primary_student_guardian",
        "unlink_student_guardian",
    ]
    assert captured[0][1]["p_create_guardian"] is True
    assert captured[0][1]["p_relationship"] == "parent"
    assert captured[1][1]["p_expected_guardian_updated_at"] == (_GUARDIAN_VERSION.isoformat())
    assert captured[3][1]["p_reason"] == "Vínculo confirmado como incorreto"


@pytest.mark.parametrize(
    ("message", "expected_error"),
    [
        ("guardian_not_found", GuardianNotFoundError),
        ("guardian_already_linked", GuardianAlreadyLinkedError),
        ("primary_guardian_required", PrimaryGuardianRequiredError),
        ("guardian_version_conflict", GuardianVersionConflictError),
    ],
)
def test_guardian_rpc_errors_are_translated(
    message: str,
    expected_error: type[Exception],
) -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(400, json={"message": message})

    async def scenario() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client)
            repository = SupabaseStudentRepository(gateway, context())
            with pytest.raises(expected_error):
                await repository.get_guardian(_STUDENT_ID, _GUARDIAN_ID)

    asyncio.run(scenario())
