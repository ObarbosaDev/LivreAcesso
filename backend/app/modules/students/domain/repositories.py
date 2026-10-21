"""Portas de persistência exigidas pelo domínio de alunos."""

from typing import Protocol
from uuid import UUID

from backend.app.modules.students.domain.entities import Student
from backend.app.modules.students.domain.value_objects import CPF


class StudentRepository(Protocol):
    def add(self, student: Student) -> None: ...

    def get_by_id(self, student_id: UUID) -> Student | None: ...

    def get_by_cpf(self, cpf: CPF) -> Student | None: ...

    def list_all(self) -> tuple[Student, ...]: ...
