"""Testes das invariantes de modalidades, turmas e horários."""

from datetime import UTC, datetime, time
from uuid import uuid4

import pytest

from backend.app.modules.classes.domain.entities import (
    ClassGroup,
    ClassInstructor,
    ClassSchedule,
    Modality,
    Weekday,
)
from backend.app.modules.classes.domain.events import ClassUpdated, ModalityCreated
from backend.app.modules.classes.domain.exceptions import (
    InvalidCapacityError,
    InvalidClassDataError,
    InvalidScheduleError,
)
from backend.app.modules.identity.domain.entities import Capability, UserRole, capabilities_for_role


def instructor() -> ClassInstructor:
    return ClassInstructor(id=uuid4(), full_name="Instrutora Ana Silva")


def schedules() -> tuple[ClassSchedule, ...]:
    return (
        ClassSchedule(Weekday.WEDNESDAY, time(14), time(15)),
        ClassSchedule(Weekday.MONDAY, time(14), time(15)),
    )


def group() -> ClassGroup:
    return ClassGroup.create(
        modality_id=uuid4(),
        name="Turma Infantil A",
        capacity=20,
        location="Sala 1",
        minimum_age=7,
        maximum_age=12,
        schedules=schedules(),
        instructors=(instructor(),),
    )


def test_modality_normalizes_text_and_emits_identifier_only() -> None:
    modality = Modality.create(name="  Capoeira   Infantil ", description="  Movimento  e ritmo ")

    event = modality.pull_events()[0]

    assert modality.name == "Capoeira Infantil"
    assert modality.description == "Movimento e ritmo"
    assert isinstance(event, ModalityCreated)
    assert "Capoeira" not in repr(event)


def test_class_orders_schedules_and_rejects_overlap() -> None:
    current = group()

    assert [item.weekday for item in current.schedules] == [
        Weekday.MONDAY,
        Weekday.WEDNESDAY,
    ]

    with pytest.raises(InvalidScheduleError, match="sobrepor"):
        ClassGroup.create(
            modality_id=current.modality_id,
            name="Turma com conflito",
            capacity=20,
            location="Sala 2",
            minimum_age=None,
            maximum_age=None,
            schedules=(
                ClassSchedule(Weekday.MONDAY, time(9), time(10, 30)),
                ClassSchedule(Weekday.MONDAY, time(10), time(11)),
            ),
            instructors=(instructor(),),
        )


def test_class_rejects_capacity_age_and_duplicate_instructor() -> None:
    current_instructor = instructor()

    with pytest.raises(InvalidCapacityError):
        ClassGroup.create(
            modality_id=uuid4(),
            name="Turma inválida",
            capacity=0,
            location="Sala 1",
            minimum_age=None,
            maximum_age=None,
            schedules=schedules(),
            instructors=(current_instructor,),
        )
    with pytest.raises(InvalidClassDataError, match="mínima"):
        ClassGroup.create(
            modality_id=uuid4(),
            name="Turma inválida",
            capacity=10,
            location="Sala 1",
            minimum_age=15,
            maximum_age=10,
            schedules=schedules(),
            instructors=(current_instructor,),
        )
    with pytest.raises(InvalidClassDataError, match="mais de uma vez"):
        ClassGroup.create(
            modality_id=uuid4(),
            name="Turma inválida",
            capacity=10,
            location="Sala 1",
            minimum_age=None,
            maximum_age=None,
            schedules=schedules(),
            instructors=(current_instructor, current_instructor),
        )


def test_class_update_reports_fields_without_values() -> None:
    current = group()
    current.pull_events()

    changed = current.update(
        modality_id=current.modality_id,
        name=current.name,
        capacity=25,
        location="Sala 3",
        minimum_age=current.minimum_age,
        maximum_age=current.maximum_age,
        schedules=current.schedules,
        instructors=current.instructors,
    )
    event = current.pull_events()[0]

    assert changed == ("capacity", "location")
    assert isinstance(event, ClassUpdated)
    assert event.changed_fields == changed
    assert "Sala 3" not in repr(event)


def test_catalog_timestamps_require_timezone() -> None:
    current = group()

    with pytest.raises(InvalidClassDataError, match="fuso horário"):
        ClassGroup(
            id=current.id,
            modality_id=current.modality_id,
            name=current.name,
            capacity=current.capacity,
            location=current.location,
            minimum_age=current.minimum_age,
            maximum_age=current.maximum_age,
            schedules=current.schedules,
            instructors=current.instructors,
            active=True,
            created_at=datetime(2026, 10, 22),
            updated_at=datetime.now(UTC),
        )


def test_operational_roles_receive_only_needed_class_capabilities() -> None:
    assert Capability.CLASSES_MANAGE in capabilities_for_role(UserRole.COORDINATOR)
    assert Capability.CLASSES_READ in capabilities_for_role(UserRole.RECEPTIONIST)
    assert Capability.CLASSES_READ in capabilities_for_role(UserRole.READ_ONLY)
    assert capabilities_for_role(UserRole.INSTRUCTOR) == (
        Capability.CLASSES_LIST,
        Capability.CLASSES_READ,
    )
    assert capabilities_for_role(UserRole.PENDING) == ()
