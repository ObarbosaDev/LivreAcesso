"""Testes dos casos de uso e isolamento de instrutores."""

import asyncio
from datetime import UTC, datetime, time
from uuid import UUID, uuid4

import pytest

from backend.app.modules.classes.application.dtos import (
    ChangeCatalogActivationInput,
    CreateClassInput,
    CreateModalityInput,
    ScheduleInput,
)
from backend.app.modules.classes.application.use_cases import (
    ChangeModalityActivation,
    CreateClass,
    CreateModality,
    GetClass,
    ListClasses,
)
from backend.app.modules.classes.domain.entities import Weekday
from backend.app.modules.classes.domain.exceptions import (
    ActiveClassesExistError,
    ClassNotFoundError,
)
from backend.app.modules.classes.infrastructure.repositories import InMemoryClassRepository
from backend.app.modules.identity.domain.entities import UserProfile, UserRole
from backend.app.modules.identity.infrastructure.repositories import InMemoryProfileRepository
from backend.app.shared.application.event_bus import EventBus
from backend.app.shared.application.exceptions import PermissionDeniedError


def seed_profile(
    repository: InMemoryProfileRepository,
    *,
    role: UserRole,
    active: bool = True,
    name: str,
) -> UserProfile:
    now = datetime.now(UTC)
    profile = UserProfile(
        id=uuid4(),
        full_name=name,
        role=role,
        active=active,
        created_at=now,
        updated_at=now,
    )
    repository.seed(profile)
    return profile


def class_input(modality_id: UUID, instructor_id: UUID, *, name: str) -> CreateClassInput:
    return CreateClassInput(
        modality_id=modality_id,
        name=name,
        capacity=20,
        location="Sala 1",
        minimum_age=7,
        maximum_age=12,
        schedules=[
            ScheduleInput(
                weekday=Weekday.MONDAY,
                starts_at=time(14),
                ends_at=time(15),
            )
        ],
        instructor_ids=[instructor_id],
    )


def test_coordinator_creates_catalog_and_instructor_sees_only_assignment() -> None:
    async def scenario() -> None:
        store = InMemoryClassRepository()
        profiles = InMemoryProfileRepository()
        coordinator = seed_profile(
            profiles,
            role=UserRole.COORDINATOR,
            name="Coordenação Principal",
        )
        assigned = seed_profile(
            profiles,
            role=UserRole.INSTRUCTOR,
            name="Instrutora Ana Silva",
        )
        other = seed_profile(
            profiles,
            role=UserRole.INSTRUCTOR,
            name="Instrutor Bruno Lima",
        )
        publisher = EventBus()
        current_modality = await CreateModality(
            store,
            profiles,
            publisher,
            coordinator.id,
        ).execute(CreateModalityInput(name="Capoeira", description=None))
        assigned_class = await CreateClass(
            store,
            store,
            profiles,
            publisher,
            coordinator.id,
        ).execute(class_input(current_modality.id, assigned.id, name="Turma A"))
        await CreateClass(
            store,
            store,
            profiles,
            publisher,
            coordinator.id,
        ).execute(class_input(current_modality.id, other.id, name="Turma B"))

        listed = await ListClasses(store, profiles, assigned.id).execute(
            active=True,
            modality_id=None,
            query=None,
            page=1,
            page_size=25,
        )
        own_detail = await GetClass(store, profiles, assigned.id).execute(assigned_class.id)

        assert listed.total == 1
        assert listed.items[0].id == assigned_class.id
        assert own_detail.instructors[0].full_name == "Instrutora Ana Silva"

        other_classes = await ListClasses(store, profiles, other.id).execute(
            active=True,
            modality_id=None,
            query=None,
            page=1,
            page_size=25,
        )
        with pytest.raises(ClassNotFoundError):
            await GetClass(store, profiles, other.id).execute(assigned_class.id)
        assert other_classes.total == 1
        assert other_classes.items[0].id != assigned_class.id

    asyncio.run(scenario())


def test_reception_can_read_but_cannot_create_catalog() -> None:
    async def scenario() -> None:
        store = InMemoryClassRepository()
        profiles = InMemoryProfileRepository()
        receptionist = seed_profile(
            profiles,
            role=UserRole.RECEPTIONIST,
            name="Recepção Principal",
        )

        with pytest.raises(PermissionDeniedError):
            await CreateModality(store, profiles, EventBus(), receptionist.id).execute(
                CreateModalityInput(name="Capoeira", description=None)
            )
        listed = await ListClasses(store, profiles, receptionist.id).execute(
            active=None,
            modality_id=None,
            query=None,
            page=1,
            page_size=25,
        )
        assert listed.total == 0

    asyncio.run(scenario())


def test_active_class_must_be_deactivated_before_modality() -> None:
    async def scenario() -> None:
        store = InMemoryClassRepository()
        profiles = InMemoryProfileRepository()
        coordinator = seed_profile(
            profiles,
            role=UserRole.COORDINATOR,
            name="Coordenação Principal",
        )
        instructor = seed_profile(
            profiles,
            role=UserRole.INSTRUCTOR,
            name="Instrutora Ana Silva",
        )
        publisher = EventBus()
        current_modality = await CreateModality(
            store,
            profiles,
            publisher,
            coordinator.id,
        ).execute(CreateModalityInput(name="Capoeira", description=None))
        await CreateClass(store, store, profiles, publisher, coordinator.id).execute(
            class_input(current_modality.id, instructor.id, name="Turma A")
        )

        with pytest.raises(ActiveClassesExistError):
            await ChangeModalityActivation(
                store,
                profiles,
                publisher,
                coordinator.id,
                False,
            ).execute(
                current_modality.id,
                ChangeCatalogActivationInput(
                    expected_updated_at=current_modality.updated_at,
                    reason="Reorganização confirmada pela coordenação",
                ),
            )

    asyncio.run(scenario())
