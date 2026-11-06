"""Testes dos casos de uso de responsáveis do aluno."""

import asyncio
from datetime import date

from backend.app.modules.students.application.dtos import (
    AddStudentGuardianInput,
    GuardianInput,
    RegisterStudentInput,
    SetPrimaryGuardianInput,
    UnlinkStudentGuardianInput,
    UpdateStudentGuardianInput,
)
from backend.app.modules.students.application.use_cases import (
    AddStudentGuardian,
    ListStudentGuardians,
    RegisterStudent,
    SetPrimaryGuardian,
    UnlinkStudentGuardian,
    UpdateStudentGuardian,
)
from backend.app.modules.students.domain.entities import GuardianRelationship
from backend.app.modules.students.infrastructure.repositories import InMemoryStudentRepository
from backend.app.shared.application.event_bus import EventBus


def test_use_cases_mask_list_without_personal_data() -> None:
    async def scenario() -> None:
        repository = InMemoryStudentRepository()
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

        added = await AddStudentGuardian(repository, event_bus).execute(
            created.id,
            AddStudentGuardianInput(
                expected_student_updated_at=created.updated_at,
                relationship=GuardianRelationship.EMERGENCY_CONTACT,
                guardian=GuardianInput(
                    full_name="Roberto Almeida",
                    phone="61988881234",
                    email="roberto@example.com",
                ),
            ),
        )
        listed = await ListStudentGuardians(repository).execute(created.id)

        assert added.phone == "61988881234"
        assert len(listed.items) == 2
        assert listed.items[1].phone_masked == "(61) *****-1234"
        assert listed.items[1].email_masked == "r***@example.com"

    asyncio.run(scenario())


def test_primary_change_precedes_safe_unlink() -> None:
    async def scenario() -> None:
        repository = InMemoryStudentRepository()
        event_bus = EventBus()
        created = await RegisterStudent(repository, event_bus).execute(
            RegisterStudentInput(
                full_name="Sophia Almeida Ramos",
                cpf="52998224725",
                birth_date=date(2015, 5, 10),
                guardian=GuardianInput(full_name="Camila Ramos", phone="61999991234"),
            )
        )
        initial_id = (await ListStudentGuardians(repository).execute(created.id)).items[0].id
        added = await AddStudentGuardian(repository, event_bus).execute(
            created.id,
            AddStudentGuardianInput(
                expected_student_updated_at=created.updated_at,
                relationship=GuardianRelationship.LEGAL_GUARDIAN,
                guardian=GuardianInput(full_name="Roberto Almeida", phone="61988881234"),
            ),
        )
        promoted = await SetPrimaryGuardian(repository, event_bus).execute(
            created.id,
            added.id,
            SetPrimaryGuardianInput(
                expected_student_updated_at=added.student_updated_at,
            ),
        )
        unlinked = await UnlinkStudentGuardian(repository, event_bus).execute(
            created.id,
            initial_id,
            UnlinkStudentGuardianInput(
                expected_student_updated_at=promoted.student_updated_at,
                reason="Vínculo anterior confirmado como incorreto",
            ),
        )

        assert unlinked.guardian_id == initial_id
        assert promoted.id == added.id
        assert promoted.is_primary is True

    asyncio.run(scenario())


def test_update_guardian_changes_full_name() -> None:
    async def scenario() -> None:
        repository = InMemoryStudentRepository()
        event_bus = EventBus()
        created = await RegisterStudent(repository, event_bus).execute(
            RegisterStudentInput(
                full_name="Sophia Almeida Ramos",
                cpf="52998224725",
                birth_date=date(2015, 5, 10),
                guardian=GuardianInput(full_name="Camila Ramos", phone="61999991234"),
            )
        )
        listed = await ListStudentGuardians(repository).execute(created.id)
        current = listed.items[0]
        output = await UpdateStudentGuardian(repository, event_bus).execute(
            created.id,
            current.id,
            UpdateStudentGuardianInput(
                expected_student_updated_at=created.updated_at,
                expected_guardian_updated_at=current.guardian_updated_at,
                full_name="Camila Almeida Ramos",
                phone="61999991234",
                relationship=current.relationship,
                receives_communications=current.receives_communications,
            ),
        )
        assert output.full_name == "Camila Almeida Ramos"

    asyncio.run(scenario())
