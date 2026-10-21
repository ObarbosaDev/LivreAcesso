"""Portas de persistência exigidas pelo domínio de alunos."""

from typing import Protocol

from backend.app.modules.students.domain.entities import Student


class StudentRepository(Protocol):
    """Porta de escrita do agregado; consultas usam projeções próprias."""

    def add(self, student: Student) -> None: ...
