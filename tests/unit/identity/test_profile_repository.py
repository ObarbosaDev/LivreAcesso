"""Testes do armazenamento em memória dos perfis."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from backend.app.modules.identity.application.queries import ProfileSearchCriteria
from backend.app.modules.identity.domain.entities import UserProfile, UserRole
from backend.app.modules.identity.domain.exceptions import (
    LastActiveCoordinatorError,
    ProfileVersionConflictError,
)
from backend.app.modules.identity.domain.value_objects import AccessChangeReason
from backend.app.modules.identity.infrastructure.repositories import InMemoryProfileRepository


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


def reason() -> AccessChangeReason:
    return AccessChangeReason("Alteração confirmada pela coordenação responsável")


def test_last_active_coordinator_cannot_change_role() -> None:
    repository = InMemoryProfileRepository()
    coordinator = profile("Coordenação Teste", UserRole.COORDINATOR, True)
    repository.seed(coordinator)
    changed = asyncio.run(repository.get_by_id(coordinator.id))
    assert changed is not None
    changed.change_role(UserRole.RECEPTIONIST, reason())

    with pytest.raises(LastActiveCoordinatorError):
        asyncio.run(
            repository.change_role(
                changed,
                reason=reason(),
                expected_updated_at=coordinator.updated_at,
            )
        )


def test_last_active_coordinator_cannot_be_deactivated() -> None:
    repository = InMemoryProfileRepository()
    coordinator = profile("Coordenação Teste", UserRole.COORDINATOR, True)
    repository.seed(coordinator)
    changed = asyncio.run(repository.get_by_id(coordinator.id))
    assert changed is not None
    changed.change_activation(False, reason())

    with pytest.raises(LastActiveCoordinatorError):
        asyncio.run(
            repository.change_activation(
                changed,
                reason=reason(),
                expected_updated_at=coordinator.updated_at,
            )
        )


def test_one_of_two_coordinators_can_be_deactivated() -> None:
    repository = InMemoryProfileRepository()
    first = profile("Primeira Coordenação", UserRole.COORDINATOR, True)
    second = profile("Segunda Coordenação", UserRole.COORDINATOR, True)
    repository.seed(first)
    repository.seed(second)
    changed = asyncio.run(repository.get_by_id(second.id))
    assert changed is not None
    changed.change_activation(False, reason())

    updated_at = asyncio.run(
        repository.change_activation(
            changed,
            reason=reason(),
            expected_updated_at=second.updated_at,
        )
    )

    assert updated_at > second.updated_at


def test_stale_profile_write_is_rejected() -> None:
    repository = InMemoryProfileRepository()
    current = profile("Coordenação Teste", UserRole.COORDINATOR, True)
    repository.seed(current)
    changed = asyncio.run(repository.get_by_id(current.id))
    assert changed is not None
    changed.rename("Nome Atualizado")

    with pytest.raises(ProfileVersionConflictError):
        asyncio.run(
            repository.rename(
                changed,
                expected_updated_at=current.updated_at - timedelta(seconds=1),
            )
        )


def test_search_ignores_case_and_accents() -> None:
    repository = InMemoryProfileRepository()
    repository.seed(profile("João Coordenação", UserRole.COORDINATOR, True))
    repository.seed(profile("Maria Recepção", UserRole.RECEPTIONIST, True))

    result = asyncio.run(repository.search(ProfileSearchCriteria(query="JOAO")))

    assert result.total == 1
    assert result.items[0].full_name == "João Coordenação"
