"""Adaptadores de persistência disponíveis para o módulo de alunos."""

from threading import RLock
from uuid import UUID

from backend.app.modules.students.domain.entities import Student
from backend.app.modules.students.domain.exceptions import DuplicateCPFError
from backend.app.modules.students.domain.value_objects import CPF


class InMemoryStudentRepository:
    """Repositório transitório para desenvolvimento e testes iniciais."""

    def __init__(self) -> None:
        self._students: dict[UUID, Student] = {}
        self._student_ids_by_cpf: dict[str, UUID] = {}
        self._lock = RLock()

    def add(self, student: Student) -> None:
        with self._lock:
            if student.cpf.value in self._student_ids_by_cpf:
                raise DuplicateCPFError
            self._students[student.id] = student
            self._student_ids_by_cpf[student.cpf.value] = student.id

    def get_by_id(self, student_id: UUID) -> Student | None:
        with self._lock:
            return self._students.get(student_id)

    def get_by_cpf(self, cpf: CPF) -> Student | None:
        with self._lock:
            student_id = self._student_ids_by_cpf.get(cpf.value)
            return self._students.get(student_id) if student_id else None

    def list_all(self) -> tuple[Student, ...]:
        with self._lock:
            return tuple(sorted(self._students.values(), key=lambda student: student.full_name.casefold()))
