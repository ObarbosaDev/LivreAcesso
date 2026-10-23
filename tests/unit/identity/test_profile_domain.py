"""Testes das regras do perfil operacional."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from backend.app.modules.identity.domain.entities import Capability, UserProfile, UserRole
from backend.app.modules.identity.domain.events import (
    ProfileActivationChanged,
    ProfileNameUpdated,
    ProfileRoleChanged,
)
from backend.app.modules.identity.domain.exceptions import (
    InvalidAccessChangeReasonError,
    InvalidProfileDataError,
    InvalidProfileRoleError,
    ProfileRoleRequiredError,
)
from backend.app.modules.identity.domain.value_objects import AccessChangeReason


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


def reason() -> AccessChangeReason:
    return AccessChangeReason("Alteração confirmada pela coordenação responsável")


def test_active_coordinator_receives_all_implemented_capabilities() -> None:
    current = profile()

    assert set(current.capabilities) == set(Capability)


def test_inactive_profile_receives_no_capability() -> None:
    current = profile(active=False)

    assert current.capabilities == ()


def test_rename_emits_event_without_personal_name() -> None:
    current = profile()

    assert current.rename("Novo Nome Operacional") is True
    event = current.pull_events()[0]

    assert isinstance(event, ProfileNameUpdated)
    assert "Novo Nome Operacional" not in repr(event)


def test_role_change_emits_only_role_transition() -> None:
    current = profile()
    protected_reason = reason()

    assert current.change_role(UserRole.RECEPTIONIST, protected_reason) is True
    event = current.pull_events()[0]

    assert isinstance(event, ProfileRoleChanged)
    assert event.previous_role == "coordenador"
    assert event.current_role == "recepcao"
    assert protected_reason.value not in repr(event)


def test_activation_change_omits_reason_from_event() -> None:
    current = profile()
    protected_reason = reason()

    assert current.change_activation(False, protected_reason) is True
    event = current.pull_events()[0]

    assert isinstance(event, ProfileActivationChanged)
    assert event.active is False
    assert protected_reason.value not in repr(event)


def test_pending_role_cannot_be_assigned_as_operational_role() -> None:
    with pytest.raises(InvalidProfileRoleError):
        profile().change_role(UserRole.PENDING, reason())


def test_pending_profile_cannot_be_active() -> None:
    with pytest.raises(ProfileRoleRequiredError):
        profile(role=UserRole.PENDING, active=True)


def test_short_access_reason_is_rejected() -> None:
    with pytest.raises(InvalidAccessChangeReasonError):
        AccessChangeReason("curto")


def test_naive_timestamps_are_rejected() -> None:
    with pytest.raises(InvalidProfileDataError, match="fuso horário"):
        UserProfile(
            id=uuid4(),
            full_name="Perfil Teste",
            role=UserRole.READ_ONLY,
            active=False,
            created_at=datetime(2026, 10, 23),
            updated_at=datetime.now(UTC),
        )
