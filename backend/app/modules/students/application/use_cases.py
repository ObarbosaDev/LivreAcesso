"""Casos de uso do módulo de alunos."""

from dataclasses import dataclass

from backend.app.modules.students.application.dtos import (
    RegisterStudentInput,
    StudentOutput,
)
from backend.app.modules.students.application.mappers import StudentMapper
from backend.app.modules.students.domain.entities import Modality, StudentStatus
from backend.app.modules.students.domain.exceptions import DuplicateCPFError
from backend.app.modules.students.domain.repositories import StudentRepository
from backend.app.shared.application.event_bus import EventPublisher


@dataclass(slots=True)
class RegisterStudent:
    repository: StudentRepository
    event_publisher: EventPublisher

    def execute(self, dto: RegisterStudentInput) -> StudentOutput:
        student = StudentMapper.to_domain(dto)
        if self.repository.get_by_cpf(student.cpf) is not None:
            raise DuplicateCPFError

        self.repository.add(student)
        for event in student.pull_events():
            self.event_publisher.publish(event)

        return StudentMapper.to_output(student)


@dataclass(slots=True)
class ListStudents:
    repository: StudentRepository

    def execute(
        self,
        *,
        modality: Modality | None = None,
        status: StudentStatus | None = None,
    ) -> tuple[StudentOutput, ...]:
        students = self.repository.list_all()
        return tuple(
            StudentMapper.to_output(student)
            for student in students
            if (modality is None or student.modality is modality)
            and (status is None or student.status is status)
        )
