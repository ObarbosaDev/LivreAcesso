"""Portas de persistência exigidas pelo domínio de alunos."""

from typing import Protocol

from backend.app.modules.students.domain.entities import Student


class StudentRepository(Protocol):
    """Porta assíncrona de escrita do agregado; consultas usam projeções próprias."""

    async def add(self, student: Student) -> None: ...
