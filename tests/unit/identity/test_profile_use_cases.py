"""Testes dos casos de uso de perfis e acessos."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from backend.app.modules.identity.application.dtos import (
    AssignableRole,
    ChangeProfileActivationInput,
    ChangeProfileRoleInput,
    UpdateMyProfileInput,
)
from backend.app.modules.identity.application.use_cases import (
    ChangeProfileActivation,
    ChangeProfileRole,
    GetMyProfile,
    ListProfiles,
    UpdateMyProfile,
)
from backend.app.modules.identity.domain.entities import Capability, UserProfile, UserRole
from backend.app.modules.identity.domain.events import ProfileActivationChanged, ProfileRoleChanged
from backend.app.modules.identity.domain.exceptions import (
    LastActiveCoordinatorError,
    ProfileVersionConflictError,
)
from backend.app.modules.identity.infrastructure.repositories import InMemoryProfileRepository
from backend.app.shared.application.event_bus import EventBus
from backend.app.shared.application.exceptions import PermissionDeniedError


def profile(name: str, role: UserRole, active: bool) -> UserProfile:
    now = datetime.now(UTC)
    return UserProfile(
        id=uuid4(),
        full_name=name,
        role=role,
        active=active,
        created_at=now,
        updated_at=now,
    )


def role_input(current: UserProfile, role: AssignableRole) -> ChangeProfileRoleInput:
    return ChangeProfileRoleInput(
        expected_updated_at=current.updated_at,
        role=role,
        reason="Acesso aprovado pela coordenação responsável",
    )


def activation_input(current: UserProfile) -> ChangeProfileActivationInput:
    return ChangeProfileActivationInput(
        expected_updated_at=current.updated_at,
        reason="Acesso aprovado pela coordenação responsável",
    )


def test_my_profile_exposes_only_implemented_capabilities() -> None:
    repository = InMemoryProfileRepository()
    coordinator = profile("Coordenação Teste", UserRole.COORDINATOR, True)
    repository.seed(coordinator)

    output = asyncio.run(GetMyProfile(repository, coordinator.id).execute())

    assert output.id == coordinator.id
    assert set(output.capabilities) == set(Capability)


def test_non_coordinator_cannot_list_profiles() -> None:
    repository = InMemoryProfileRepository()
    receptionist = profile("Recepção Teste", UserRole.RECEPTIONIST, True)
    repository.seed(receptionist)

    with pytest.raises(PermissionDeniedError):
        asyncio.run(ListProfiles(repository, repository, receptionist.id).execute())


def test_coordinator_assigns_role_then_activates_profile() -> None:
    repository = InMemoryProfileRepository()
    event_bus = EventBus()
    coordinator = profile("Coordenação Teste", UserRole.COORDINATOR, True)
    pending = profile("Novo Perfil", UserRole.PENDING, False)
    repository.seed(coordinator)
    repository.seed(pending)
    role_events: list[ProfileRoleChanged] = []
    activation_events: list[ProfileActivationChanged] = []
    event_bus.subscribe(ProfileRoleChanged, role_events.append)
    event_bus.subscribe(ProfileActivationChanged, activation_events.append)

    assigned = asyncio.run(
        ChangeProfileRole(repository, event_bus, coordinator.id).execute(
            pending.id,
            role_input(pending, AssignableRole.RECEPTIONIST),
        )
    )
    activated = asyncio.run(
        ChangeProfileActivation(repository, event_bus, coordinator.id, True).execute(
            pending.id,
            activation_input(
                UserProfile(
                    id=assigned.id,
                    full_name=assigned.full_name,
                    role=assigned.role,
                    active=assigned.active,
                    created_at=assigned.created_at,
                    updated_at=assigned.updated_at,
                )
            ),
        )
    )

    assert assigned.role is UserRole.RECEPTIONIST
    assert assigned.active is False
    assert activated.active is True
    assert Capability.STUDENTS_CREATE in activated.capabilities
    assert len(role_events) == 1
    assert len(activation_events) == 1


def test_last_coordinator_protection_reaches_use_case() -> None:
    repository = InMemoryProfileRepository()
    event_bus = EventBus()
    coordinator = profile("Coordenação Teste", UserRole.COORDINATOR, True)
    repository.seed(coordinator)

    with pytest.raises(LastActiveCoordinatorError):
        asyncio.run(
            ChangeProfileActivation(repository, event_bus, coordinator.id, False).execute(
                coordinator.id,
                activation_input(coordinator),
            )
        )


def test_profile_name_update_uses_optimistic_version() -> None:
    repository = InMemoryProfileRepository()
    event_bus = EventBus()
    coordinator = profile("Coordenação Teste", UserRole.COORDINATOR, True)
    repository.seed(coordinator)

    updated = asyncio.run(
        UpdateMyProfile(repository, event_bus, coordinator.id).execute(
            UpdateMyProfileInput(
                expected_updated_at=coordinator.updated_at,
                full_name="Coordenação Principal",
            )
        )
    )

    assert updated.full_name == "Coordenação Principal"
    assert updated.updated_at > coordinator.updated_at


def test_stale_role_change_is_rejected_before_mutation() -> None:
    repository = InMemoryProfileRepository()
    event_bus = EventBus()
    coordinator = profile("Coordenação Teste", UserRole.COORDINATOR, True)
    target = profile("Consulta Teste", UserRole.READ_ONLY, True)
    repository.seed(coordinator)
    repository.seed(target)
    stale = target.updated_at - timedelta(seconds=1)

    with pytest.raises(ProfileVersionConflictError):
        asyncio.run(
            ChangeProfileRole(repository, event_bus, coordinator.id).execute(
                target.id,
                ChangeProfileRoleInput(
                    expected_updated_at=stale,
                    role=AssignableRole.INSTRUCTOR,
                    reason="Alteração aprovada pela coordenação responsável",
                ),
            )
        )
