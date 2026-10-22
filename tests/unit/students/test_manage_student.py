"""Testes dos casos de uso de consulta, edição e status de alunos."""

import asyncio
from datetime import date, timedelta
from uuid import uuid4

import pytest

from backend.app.modules.students.application.dtos import (
    ChangeStudentStatusInput,
    GuardianInput,
    RegisterStudentInput,
    StudentOutput,
    UpdateStudentInput,
)
from backend.app.modules.students.application.use_cases import (
    ChangeStudentStatus,
    GetStudent,
    RegisterStudent,
    UpdateStudent,
)
from backend.app.modules.students.domain.entities import StudentStatus
from backend.app.modules.students.domain.events import StudentStatusChanged, StudentUpdated
from backend.app.modules.students.domain.exceptions import (
    StudentNotFoundError,
    StudentVersionConflictError,
)
from backend.app.modules.students.infrastructure.repositories import InMemoryStudentRepository
from backend.app.shared.application.event_bus import EventBus


async def registered_student(
    repository: InMemoryStudentRepository,
) -> tuple[StudentOutput, EventBus]:
    event_bus = EventBus()
    created = await RegisterStudent(repository, event_bus).execute(
        RegisterStudentInput(
            full_name="Sophia Almeida Ramos",
            cpf="52998224725",
            birth_date=date(2015, 5, 10),
            guardian=GuardianInput(
                full_name="Camila Ramos",
                phone="61999991234",
                email="camila@example.com",
            ),
        )
    )
    return created, event_bus


def test_detail_keeps_cpf_masked_and_reveals_authorized_contact() -> None:
    async def scenario() -> None:
        repository = InMemoryStudentRepository()
        created, _ = await registered_student(repository)

        detail = await GetStudent(repository).execute(created.id)

        assert detail.cpf_masked == "***.***.***-25"
        assert detail.guardian.phone == "61999991234"
        assert detail.guardian.email == "camila@example.com"

    asyncio.run(scenario())


def test_update_changes_version_and_publishes_safe_event() -> None:
    async def scenario() -> None:
        repository = InMemoryStudentRepository()
        created, event_bus = await registered_student(repository)
        recorded: list[StudentUpdated] = []
        event_bus.subscribe(StudentUpdated, recorded.append)

        detail = await UpdateStudent(repository, event_bus).execute(
            created.id,
            UpdateStudentInput(
                expected_updated_at=created.updated_at,
                full_name="Sophia Almeida Ramos da Silva",
                birth_date=date(2015, 5, 10),
                guardian=GuardianInput(
                    full_name="Camila Ramos",
                    phone="61988881234",
                    email="camila@example.com",
                ),
            ),
        )

        assert detail.full_name == "Sophia Almeida Ramos da Silva"
        assert detail.updated_at > created.updated_at
        assert recorded[0].changed_fields == ("full_name", "guardian")

    asyncio.run(scenario())


def test_stale_update_is_rejected() -> None:
    async def scenario() -> None:
        repository = InMemoryStudentRepository()
        created, event_bus = await registered_student(repository)
        stale_version = created.updated_at - timedelta(seconds=1)

        with pytest.raises(StudentVersionConflictError):
            await UpdateStudent(repository, event_bus).execute(
                created.id,
                UpdateStudentInput(
                    expected_updated_at=stale_version,
                    full_name="Outro Nome",
                    birth_date=date(2015, 5, 10),
                    guardian=GuardianInput(
                        full_name="Camila Ramos",
                        phone="61999991234",
                    ),
                ),
            )

    asyncio.run(scenario())


def test_deactivate_and_reactivate_preserve_same_record() -> None:
    async def scenario() -> None:
        repository = InMemoryStudentRepository()
        created, event_bus = await registered_student(repository)
        events: list[StudentStatusChanged] = []
        event_bus.subscribe(StudentStatusChanged, events.append)

        deactivate = ChangeStudentStatus(repository, event_bus, StudentStatus.INACTIVE)
        inactive = await deactivate.execute(
            created.id,
            ChangeStudentStatusInput(
                expected_updated_at=created.updated_at,
                reason="Solicitação confirmada pela coordenação",
            ),
        )
        activate = ChangeStudentStatus(repository, event_bus, StudentStatus.ACTIVE)
        active = await activate.execute(
            inactive.id,
            ChangeStudentStatusInput(
                expected_updated_at=inactive.updated_at,
                reason="Retorno confirmado pela coordenação responsável",
            ),
        )

        assert inactive.status is StudentStatus.INACTIVE
        assert active.status is StudentStatus.ACTIVE
        assert active.id == created.id
        assert len(events) == 2

    asyncio.run(scenario())


def test_missing_student_returns_domain_error() -> None:
    with pytest.raises(StudentNotFoundError):
        asyncio.run(GetStudent(InMemoryStudentRepository()).execute(uuid4()))
