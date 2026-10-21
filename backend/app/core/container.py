"""Ponto único de composição das dependências da aplicação."""

from dataclasses import dataclass

from backend.app.modules.students.application.listeners import (
    StudentRegisteredAuditListener,
)
from backend.app.modules.students.application.use_cases import ListStudents, RegisterStudent
from backend.app.modules.students.domain.events import StudentRegistered
from backend.app.modules.students.infrastructure.repositories import InMemoryStudentRepository
from backend.app.shared.application.event_bus import EventBus


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    student_repository: InMemoryStudentRepository
    event_bus: EventBus
    register_student: RegisterStudent
    list_students: ListStudents


def build_container() -> ApplicationContainer:
    event_bus = EventBus()
    student_repository = InMemoryStudentRepository()

    event_bus.subscribe(StudentRegistered, StudentRegisteredAuditListener())

    return ApplicationContainer(
        student_repository=student_repository,
        event_bus=event_bus,
        register_student=RegisterStudent(student_repository, event_bus),
        list_students=ListStudents(student_repository),
    )
