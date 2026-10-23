"""Testes das regras de edição e ciclo cadastral do agregado."""

from datetime import UTC, date, datetime

import pytest

from backend.app.modules.students.domain.entities import Guardian, Student, StudentStatus
from backend.app.modules.students.domain.events import StudentStatusChanged, StudentUpdated
from backend.app.modules.students.domain.exceptions import (
    InvalidStatusReasonError,
    InvalidStudentDataError,
)
from backend.app.modules.students.domain.value_objects import CPF, Phone, StatusChangeReason


def student() -> Student:
    current = Student.register(
        full_name="Sophia Almeida Ramos",
        cpf=CPF("52998224725"),
        birth_date=date(2015, 5, 10),
        guardian=Guardian(
            full_name="Camila Ramos",
            phone=Phone("61999991234"),
            email="camila@example.com",
        ),
    )
    current.pull_events()
    return current


def test_update_reports_fields_without_personal_values() -> None:
    current = student()
    original_cpf = current.cpf
    original_guardian = current.guardian

    changed_fields = current.update_personal_data(
        full_name="Sophia Almeida Ramos da Silva",
        birth_date=date(2015, 5, 10),
    )
    events = current.pull_events()

    assert changed_fields == ("full_name",)
    assert current.cpf == original_cpf
    assert current.guardian == original_guardian
    assert len(events) == 1
    assert isinstance(events[0], StudentUpdated)
    assert events[0].changed_fields == changed_fields
    assert "Sophia" not in repr(events[0])


def test_unchanged_profile_emits_no_event() -> None:
    current = student()

    changed_fields = current.update_personal_data(
        full_name=current.full_name,
        birth_date=current.birth_date,
    )

    assert changed_fields == ()
    assert current.pull_events() == ()


def test_status_transition_does_not_copy_sensitive_reason_to_event() -> None:
    current = student()
    reason = StatusChangeReason("Solicitação registrada pela coordenação")

    assert current.change_status(StudentStatus.INACTIVE, reason) is True
    event = current.pull_events()[0]

    assert isinstance(event, StudentStatusChanged)
    assert event.previous_status == "ativo"
    assert event.current_status == "inativo"
    assert reason.value not in repr(event)


def test_repeating_status_is_idempotent() -> None:
    current = student()
    reason = StatusChangeReason("Revisão cadastral confirmada pela coordenação")

    assert current.change_status(StudentStatus.ACTIVE, reason) is False
    assert current.pull_events() == ()


def test_short_status_reason_is_rejected() -> None:
    with pytest.raises(InvalidStatusReasonError):
        StatusChangeReason("curto")


def test_naive_audit_timestamp_is_rejected() -> None:
    with pytest.raises(InvalidStudentDataError, match="fuso horário"):
        Student(
            id=student().id,
            full_name="Sophia Almeida Ramos",
            cpf=CPF("52998224725"),
            birth_date=date(2015, 5, 10),
            guardian=student().guardian,
            created_at=datetime(2026, 10, 21),
            updated_at=datetime.now(UTC),
        )
