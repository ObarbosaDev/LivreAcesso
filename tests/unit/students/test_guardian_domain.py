"""Testes dos contratos de domínio para responsáveis múltiplos."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.app.modules.students.application.dtos import (
    AddStudentGuardianInput,
    GuardianInput,
)
from backend.app.modules.students.domain.entities import (
    Guardian,
    GuardianRelationship,
    StudentGuardian,
)
from backend.app.modules.students.domain.exceptions import (
    InvalidGuardianUnlinkReasonError,
    InvalidStudentDataError,
)
from backend.app.modules.students.domain.value_objects import (
    GuardianUnlinkReason,
    Phone,
)


def test_primary_guardian_must_remain_active() -> None:
    now = datetime.now(UTC)

    with pytest.raises(InvalidStudentDataError, match="principal"):
        StudentGuardian(
            student_id=uuid4(),
            guardian=Guardian(full_name="Camila Ramos", phone=Phone("61999991234")),
            relationship=GuardianRelationship.PARENT,
            is_primary=True,
            receives_communications=True,
            active=False,
            linked_at=now,
            guardian_updated_at=now,
        )


def test_add_input_requires_exactly_one_guardian_source() -> None:
    now = datetime.now(UTC)
    guardian = GuardianInput(full_name="Camila Ramos", phone="61999991234")

    with pytest.raises(ValidationError):
        AddStudentGuardianInput(
            expected_student_updated_at=now,
            relationship=GuardianRelationship.PARENT,
        )
    with pytest.raises(ValidationError):
        AddStudentGuardianInput(
            expected_student_updated_at=now,
            relationship=GuardianRelationship.PARENT,
            guardian=guardian,
            existing_guardian_id=uuid4(),
        )

    payload = AddStudentGuardianInput(
        expected_student_updated_at=now,
        relationship=GuardianRelationship.PARENT,
        guardian=guardian,
    )
    assert payload.guardian == guardian
    assert payload.existing_guardian_id is None


def test_unlink_reason_is_normalized_and_never_part_of_event_contract() -> None:
    assert GuardianUnlinkReason("  Vínculo informado por engano  ").value == (
        "Vínculo informado por engano"
    )
    with pytest.raises(InvalidGuardianUnlinkReasonError):
        GuardianUnlinkReason("curto")
