"""Testes dos contratos RPC do catálogo de turmas."""

import asyncio
import json
from datetime import UTC, datetime, time, timedelta
from uuid import UUID

import httpx2
import pytest

from backend.app.modules.classes.application.queries import (
    ClassSearchCriteria,
    ModalitySearchCriteria,
)
from backend.app.modules.classes.domain.entities import (
    ClassGroup,
    ClassInstructor,
    ClassSchedule,
    Modality,
    Weekday,
)
from backend.app.modules.classes.domain.exceptions import (
    ActiveClassesExistError,
    ClassVersionConflictError,
    DuplicateClassError,
    DuplicateModalityError,
    InvalidInstructorAssignmentError,
    InvalidScheduleError,
    ModalityNotFoundError,
    ModalityVersionConflictError,
)
from backend.app.modules.classes.domain.value_objects import ClassChangeReason
from backend.app.modules.classes.infrastructure.supabase_repository import (
    SupabaseClassRepository,
)
from backend.app.modules.identity.application.authentication import AccessToken, AuthenticatedUser
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway

_PROJECT_URL = "https://project-ref.supabase.co"
_MODALITY_ID = UUID("00000000-0000-4000-8000-000000000401")
_CLASS_ID = UUID("00000000-0000-4000-8000-000000000402")
_INSTRUCTOR_ID = UUID("00000000-0000-4000-8000-000000000403")
_VERSION = datetime(2026, 10, 22, 20, 0, tzinfo=UTC)


def context() -> RequestContext:
    return RequestContext(
        request_id=UUID("00000000-0000-4000-8000-000000000404"),
        user=AuthenticatedUser(
            user_id=UUID("00000000-0000-4000-8000-000000000405"),
            access_token=AccessToken("jwt-sintetico"),
            session_id=None,
            assurance_level="aal1",
        ),
    )


def modality_row() -> dict[str, object]:
    return {
        "id": str(_MODALITY_ID),
        "name": "Capoeira",
        "description": "Atividade corporal e cultural",
        "active": True,
        "created_at": _VERSION.isoformat(),
        "updated_at": _VERSION.isoformat(),
    }


def class_row() -> dict[str, object]:
    return {
        "id": str(_CLASS_ID),
        "modality_id": str(_MODALITY_ID),
        "name": "Turma Infantil",
        "capacity": 20,
        "location": "Sala 1",
        "minimum_age": 7,
        "maximum_age": 12,
        "schedules": [{"weekday": "monday", "starts_at": "14:00:00", "ends_at": "15:00:00"}],
        "instructors": [{"id": str(_INSTRUCTOR_ID), "full_name": "Instrutora Ana Silva"}],
        "active": True,
        "created_at": _VERSION.isoformat(),
        "updated_at": _VERSION.isoformat(),
    }


def modality() -> Modality:
    return Modality(
        id=_MODALITY_ID,
        name="Capoeira",
        description="Atividade corporal e cultural",
        active=True,
        created_at=_VERSION,
        updated_at=_VERSION,
    )


def group() -> ClassGroup:
    return ClassGroup(
        id=_CLASS_ID,
        modality_id=_MODALITY_ID,
        name="Turma Infantil",
        capacity=20,
        location="Sala 1",
        minimum_age=7,
        maximum_age=12,
        schedules=(ClassSchedule(Weekday.MONDAY, time(14), time(15)),),
        instructors=(ClassInstructor(_INSTRUCTOR_ID, "Instrutora Ana Silva"),),
        active=True,
        created_at=_VERSION,
        updated_at=_VERSION,
    )


def test_modality_crud_uses_strict_rpc_contracts() -> None:
    rpc_names: list[str] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        rpc_name = request.url.path.rsplit("/", maxsplit=1)[-1]
        rpc_names.append(rpc_name)
        if rpc_name == "list_modalities":
            return httpx2.Response(200, json={"items": [modality_row()], "total": 1})
        if rpc_name in {"update_modality", "change_modality_activation"}:
            return httpx2.Response(200, json={"updated_at": _VERSION.isoformat()})
        return httpx2.Response(200, json=modality_row())

    async def scenario() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            repository = SupabaseClassRepository(
                SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client),
                context(),
            )
            await repository.add_modality(modality())
            restored = await repository.get_modality(_MODALITY_ID)
            listed = await repository.search_modalities(ModalitySearchCriteria(query="capoeira"))
            await repository.update_modality(modality(), expected_updated_at=_VERSION)
            await repository.change_modality_activation(
                modality(),
                reason=ClassChangeReason("Alteração confirmada pela coordenação"),
                expected_updated_at=_VERSION,
            )
            assert restored is not None and restored.name == "Capoeira"
            assert listed.total == 1

    asyncio.run(scenario())
    assert rpc_names == [
        "create_modality",
        "get_modality",
        "list_modalities",
        "update_modality",
        "change_modality_activation",
    ]


def test_class_payload_maps_schedule_and_never_sends_viewer_identity() -> None:
    captured: list[dict[str, object]] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        payload = json.loads(request.content)
        captured.append(payload)
        if request.url.path.endswith("/list_classes"):
            return httpx2.Response(200, json={"items": [class_row()], "total": 1})
        return httpx2.Response(200, json=class_row())

    async def scenario() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            repository = SupabaseClassRepository(
                SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client),
                context(),
            )
            await repository.add_class(group())
            listed = await repository.search_classes(
                ClassSearchCriteria(viewer_instructor_id=_INSTRUCTOR_ID)
            )
            restored = await repository.get_class(_CLASS_ID)
            assert listed.items[0].schedules[0].weekday is Weekday.MONDAY
            assert restored is not None and restored.instructors[0].id == _INSTRUCTOR_ID

    asyncio.run(scenario())
    assert captured[0]["p_schedules"] == [
        {"weekday": "monday", "starts_at": "14:00:00", "ends_at": "15:00:00"}
    ]
    assert captured[0]["p_instructor_ids"] == [str(_INSTRUCTOR_ID)]
    assert all("viewer" not in key for payload in captured for key in payload)


def test_class_mutations_return_authoritative_version() -> None:
    database_version = _VERSION + timedelta(minutes=1)
    rpc_names: list[str] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        rpc_names.append(request.url.path.rsplit("/", maxsplit=1)[-1])
        return httpx2.Response(200, json={"updated_at": database_version.isoformat()})

    async def scenario() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            repository = SupabaseClassRepository(
                SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client),
                context(),
            )
            updated = await repository.update_class(group(), expected_updated_at=_VERSION)
            changed = await repository.change_class_activation(
                group(),
                reason=ClassChangeReason("Alteração confirmada pela coordenação"),
                expected_updated_at=_VERSION,
            )
            assert updated == database_version
            assert changed == database_version

    asyncio.run(scenario())
    assert rpc_names == ["update_class", "change_class_activation"]


@pytest.mark.parametrize(
    ("message", "expected_error"),
    [
        ("duplicate_modality", DuplicateModalityError),
        ("duplicate_class", DuplicateClassError),
        ("modality_not_found", ModalityNotFoundError),
        ("modality_version_conflict", ModalityVersionConflictError),
        ("class_version_conflict", ClassVersionConflictError),
        ("invalid_instructor_assignment", InvalidInstructorAssignmentError),
        ("schedule_overlap", InvalidScheduleError),
        ("active_classes_exist", ActiveClassesExistError),
    ],
)
def test_rpc_errors_are_translated(message: str, expected_error: type[Exception]) -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(400, json={"message": message})

    async def scenario() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            repository = SupabaseClassRepository(
                SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client),
                context(),
            )
            with pytest.raises(expected_error):
                await repository.get_class(_CLASS_ID)

    asyncio.run(scenario())


def test_missing_class_is_returned_as_none() -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(404, json={"message": "class_not_found"})

    async def scenario() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            repository = SupabaseClassRepository(
                SupabaseRPCGateway(_PROJECT_URL, "publishable", http_client=client),
                context(),
            )
            assert await repository.get_class(_CLASS_ID) is None

    asyncio.run(scenario())
