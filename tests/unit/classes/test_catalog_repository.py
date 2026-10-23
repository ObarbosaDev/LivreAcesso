"""Testes do catálogo em memória e de suas versões."""

import asyncio
from datetime import UTC, datetime, time, timedelta
from uuid import UUID, uuid4

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
)
from backend.app.modules.classes.domain.value_objects import ClassChangeReason
from backend.app.modules.classes.infrastructure.repositories import InMemoryClassRepository


def modality(name: str = "Capoeira") -> Modality:
    return Modality.create(name=name, description="Atividade corporal e cultural")


def group(
    modality_id: UUID,
    *,
    name: str = "Turma Infantil",
    instructor_id: UUID | None = None,
) -> ClassGroup:
    return ClassGroup.create(
        modality_id=modality_id,
        name=name,
        capacity=20,
        location="Sala 1",
        minimum_age=7,
        maximum_age=12,
        schedules=(ClassSchedule(Weekday.MONDAY, time(14), time(15)),),
        instructors=(
            ClassInstructor(
                id=instructor_id or uuid4(),
                full_name="Instrutora Ana Silva",
            ),
        ),
    )


def test_repository_rejects_normalized_duplicate_names() -> None:
    async def scenario() -> None:
        repository = InMemoryClassRepository()
        first = modality("Capoeira")
        await repository.add_modality(first)

        with pytest.raises(DuplicateModalityError):
            await repository.add_modality(modality("capoeíra"))

        current_group = group(first.id, name="Turma Águia")
        await repository.add_class(current_group)
        with pytest.raises(DuplicateClassError):
            await repository.add_class(group(first.id, name="turma aguia"))

    asyncio.run(scenario())


def test_repository_checks_versions_and_blocks_active_modality_deactivation() -> None:
    async def scenario() -> None:
        repository = InMemoryClassRepository()
        current_modality = modality()
        await repository.add_modality(current_modality)
        current_group = group(current_modality.id)
        await repository.add_class(current_group)

        current_group.name = "Turma Atualizada"
        with pytest.raises(ClassVersionConflictError):
            await repository.update_class(
                current_group,
                expected_updated_at=current_group.updated_at - timedelta(seconds=1),
            )

        current_modality.active = False
        with pytest.raises(ActiveClassesExistError):
            await repository.change_modality_activation(
                current_modality,
                reason=ClassChangeReason("Reorganização confirmada pela coordenação"),
                expected_updated_at=current_modality.updated_at,
            )

    asyncio.run(scenario())


def test_search_is_paginated_accent_insensitive_and_scoped_to_instructor() -> None:
    async def scenario() -> None:
        repository = InMemoryClassRepository()
        current_modality = modality("Dança")
        await repository.add_modality(current_modality)
        assigned_instructor = uuid4()
        await repository.add_class(
            group(
                current_modality.id,
                name="Turma Iniciação",
                instructor_id=assigned_instructor,
            )
        )
        await repository.add_class(group(current_modality.id, name="Turma Avançada"))

        modalities = await repository.search_modalities(
            ModalitySearchCriteria(query="danca", limit=1)
        )
        classes = await repository.search_classes(
            ClassSearchCriteria(viewer_instructor_id=assigned_instructor)
        )

        assert modalities.total == 1
        assert classes.total == 1
        assert classes.items[0].name == "Turma Iniciação"

    asyncio.run(scenario())


def test_persisted_versions_are_timezone_aware_and_monotonic() -> None:
    async def scenario() -> None:
        repository = InMemoryClassRepository()
        current = modality()
        created = await repository.add_modality(current)
        current.description = "Descrição atualizada"
        updated = await repository.update_modality(
            current,
            expected_updated_at=created.updated_at,
        )

        assert created.created_at.tzinfo is UTC
        assert updated > created.updated_at
        assert updated > datetime.now(UTC) - timedelta(minutes=1)

    asyncio.run(scenario())
