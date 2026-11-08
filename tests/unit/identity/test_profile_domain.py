"""Testes das regras do perfil operacional."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from backend.app.modules.identity.domain.entities import Capability, UserProfile, UserRole
from backend.app.modules.identity.domain.exceptions import (
    InvalidProfileDataError,
    InvalidProfileRoleError,
    ProfileRoleRequiredError,
)


def profile(
    *,
    role: UserRole = UserRole.COORDINATOR,
    active: bool = True,
) -> UserProfile:
    now = datetime.now(UTC)
    return UserProfile(
        id=uuid4(),
        full_name="Coordenação Teste",
        role=role,
        active=active,
        created_at=now,
        updated_at=now,
    )


def test_active_coordinator_receives_all_implemented_capabilities() -> None:
    current = profile()

    assert set(current.capabilities) == set(Capability)


def test_inactive_profile_receives_no_capability() -> None:
    current = profile(active=False)

    assert current.capabilities == ()


def test_rename_changes_full_name() -> None:
    current = profile()

    assert current.rename("Novo Nome Operacional") is True
    assert current.full_name == "Novo Nome Operacional"
    assert current.rename("Novo Nome Operacional") is False


def test_role_change_updates_role() -> None:
    current = profile()

    assert current.change_role(UserRole.RECEPTIONIST) is True
    assert current.role is UserRole.RECEPTIONIST
    assert current.change_role(UserRole.RECEPTIONIST) is False


def test_activation_change_updates_active_flag() -> None:
    current = profile()

    assert current.change_activation(False) is True
    assert current.active is False
    assert current.change_activation(False) is False


def test_pending_role_cannot_be_assigned_as_operational_role() -> None:
    with pytest.raises(InvalidProfileRoleError):
        profile().change_role(UserRole.PENDING)


def test_pending_profile_cannot_be_active() -> None:
    with pytest.raises(ProfileRoleRequiredError):
        profile(role=UserRole.PENDING, active=True)


def test_naive_timestamps_are_rejected() -> None:
    with pytest.raises(InvalidProfileDataError, match="fuso horário"):
        UserProfile(
            id=uuid4(),
            full_name="Perfil Teste",
            role=UserRole.INSTRUCTOR,
            active=False,
            created_at=datetime(2026, 10, 23),
            updated_at=datetime.now(UTC),
        )
