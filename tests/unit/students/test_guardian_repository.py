"""Testes do repositório em memória para vínculos de responsáveis."""

import asyncio
from datetime import date, timedelta

import pytest

from backend.app.modules.students.application.dtos import (
    GuardianInput,
    RegisterStudentInput,
    StudentOutput,
)
from backend.app.modules.students.application.use_cases import RegisterStudent
from backend.app.modules.students.domain.entities import Guardian, GuardianRelationship
from backend.app.modules.students.domain.exceptions import (
    GuardianVersionConflictError,
    PrimaryGuardianRequiredError,
    StudentVersionConflictError,
)
from backend.app.modules.students.domain.value_objects import GuardianUnlinkReason, Phone
from backend.app.modules.students.infrastructure.repositories import InMemoryStudentRepository
from backend.app.shared.application.event_bus import EventBus


async def register_student(
    repository: InMemoryStudentRepository,
    *,
    name: str = "Sophia Almeida Ramos",
    cpf: str = "52998224725",
    guardian_name: str = "Camila Ramos",
) -> StudentOutput:
    return await RegisterStudent(repository, EventBus()).execute(
        RegisterStudentInput(
            full_name=name,
            cpf=cpf,
            birth_date=date(2015, 5, 10),
            guardian=GuardianInput(
                full_name=guardian_name,
                phone="61999991234",
                email="camila@example.com",
            ),
        )
    )


def test_initial_guardian_is_primary_and_list_is_masked() -> None:
    async def scenario() -> None:
        repository = InMemoryStudentRepository()
        created = await register_student(repository)

        result = await repository.list_guardians(created.id)

        assert result.student_updated_at == created.updated_at
        assert len(result.items) == 1
        assert result.items[0].is_primary is True
        assert result.items[0].phone_masked == "(61) *****-1234"
        assert result.items[0].email_masked == "c***@example.com"
        assert "61999991234" not in repr(result)

    asyncio.run(scenario())


def test_new_guardian_can_become_primary_and_old_link_can_be_unlinked() -> None:
    async def scenario() -> None:
        repository = InMemoryStudentRepository()
        created = await register_student(repository)
        initial = (await repository.list_guardians(created.id)).items[0]
        new_guardian = Guardian(
            full_name="Roberto Almeida",
            phone=Phone("61988881234"),
            email="roberto@example.com",
        )

        added = await repository.add_guardian(
            created.id,
            guardian=new_guardian,
            existing_guardian_id=None,
            relationship=GuardianRelationship.LEGAL_GUARDIAN,
            make_primary=False,
            receives_communications=True,
            expected_student_updated_at=created.updated_at,
        )
        promoted = await repository.set_primary_guardian(
            created.id,
            new_guardian.id,
            expected_student_updated_at=added.snapshot.student_updated_at,
        )
        unlinked = await repository.unlink_guardian(
            created.id,
            initial.id,
            reason=GuardianUnlinkReason("Vínculo antigo confirmado como incorreto"),
            expected_student_updated_at=promoted.snapshot.student_updated_at,
        )

        result = await repository.list_guardians(created.id)
        student = await repository.get_by_id(created.id)
        assert unlinked.student_updated_at == result.student_updated_at
        assert [item.id for item in result.items] == [new_guardian.id]
        assert result.items[0].is_primary is True
        assert student is not None and student.guardian.id == new_guardian.id

        with pytest.raises(PrimaryGuardianRequiredError):
            await repository.unlink_guardian(
                created.id,
                new_guardian.id,
                reason=GuardianUnlinkReason("Contato não deve mais receber comunicações"),
                expected_student_updated_at=result.student_updated_at,
            )

    asyncio.run(scenario())


def test_existing_guardian_can_be_shared_between_siblings() -> None:
    async def scenario() -> None:
        repository = InMemoryStudentRepository()
        first = await register_student(repository)
        second = await register_student(
            repository,
            name="Lucas Almeida Ramos",
            cpf="11144477735",
            guardian_name="Outro Contato Inicial",
        )
        shared_id = (await repository.list_guardians(first.id)).items[0].id

        linked = await repository.add_guardian(
            second.id,
            guardian=None,
            existing_guardian_id=shared_id,
            relationship=GuardianRelationship.PARENT,
            make_primary=False,
            receives_communications=True,
            expected_student_updated_at=second.updated_at,
        )

        assert linked.snapshot.link.guardian.id == shared_id
        assert linked.snapshot.link.guardian.full_name == "Camila Ramos"
        assert len((await repository.list_guardians(second.id)).items) == 2

    asyncio.run(scenario())


def test_student_and_guardian_versions_are_checked_independently() -> None:
    async def scenario() -> None:
        repository = InMemoryStudentRepository()
        created = await register_student(repository)
        current = await repository.list_guardians(created.id)
        initial = current.items[0]

        updated = await repository.update_guardian(
            created.id,
            Guardian(
                id=initial.id,
                full_name="Camila Ramos da Silva",
                phone=Phone("61988881234"),
                email="camila@example.com",
            ),
            relationship=GuardianRelationship.PARENT,
            receives_communications=True,
            expected_student_updated_at=current.student_updated_at,
            expected_guardian_updated_at=initial.guardian_updated_at,
        )
        assert updated.snapshot.link.guardian_updated_at > initial.guardian_updated_at
        assert updated.snapshot.student_updated_at > current.student_updated_at

        with pytest.raises(GuardianVersionConflictError):
            await repository.update_guardian(
                created.id,
                updated.snapshot.link.guardian,
                relationship=GuardianRelationship.PARENT,
                receives_communications=False,
                expected_student_updated_at=updated.snapshot.student_updated_at,
                expected_guardian_updated_at=initial.guardian_updated_at,
            )

        with pytest.raises(StudentVersionConflictError):
            await repository.set_primary_guardian(
                created.id,
                initial.id,
                expected_student_updated_at=(
                    updated.snapshot.student_updated_at - timedelta(seconds=1)
                ),
            )

    asyncio.run(scenario())
