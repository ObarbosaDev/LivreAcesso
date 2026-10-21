"""Adaptadores de persistência disponíveis para o módulo de alunos."""

from threading import RLock
from unicodedata import combining, normalize
from uuid import UUID

from backend.app.modules.students.application.queries import (
    StudentListItem,
    StudentSearchCriteria,
    StudentSearchResult,
)
from backend.app.modules.students.domain.entities import Student
from backend.app.modules.students.domain.exceptions import DuplicateCPFError


def _search_key(value: str) -> str:
    """Produz comparação sem diferença de caixa ou acento para busca por nome."""

    decomposed = normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not combining(character))


def _to_list_item(student: Student) -> StudentListItem:
    """Cria a mesma projeção mascarada que a RPC entregará em produção."""

    return StudentListItem(
        id=student.id,
        full_name=student.full_name,
        cpf_masked=student.cpf.masked,
        birth_date=student.birth_date,
        age=student.age_on(),
        status=student.status,
        guardian_name=student.guardian.full_name,
        guardian_phone_masked=student.guardian.phone.masked,
        created_at=student.created_at,
    )


class InMemoryStudentRepository:
    """Adaptador transitório de escrita e leitura para desenvolvimento e testes."""

    def __init__(self) -> None:
        self._students: dict[UUID, Student] = {}
        self._student_ids_by_cpf: dict[str, UUID] = {}
        self._lock = RLock()

    def add(self, student: Student) -> None:
        with self._lock:
            # A verificação e a escrita compartilham o mesmo lock. Isso reproduz,
            # em menor escala, a garantia do índice único que existirá no Postgres.
            if student.cpf.value in self._student_ids_by_cpf:
                raise DuplicateCPFError
            self._students[student.id] = student
            self._student_ids_by_cpf[student.cpf.value] = student.id

    def search(self, criteria: StudentSearchCriteria) -> StudentSearchResult:
        with self._lock:
            query_key = _search_key(criteria.query) if criteria.query else None
            matches = (
                student
                for student in self._students.values()
                if (criteria.status is None or student.status is criteria.status)
                and (query_key is None or query_key in _search_key(student.full_name))
            )

            # Nome e UUID formam uma ordenação estável. O UUID desempata homônimos
            # para que uma pessoa não veja registros pulando entre páginas.
            ordered = tuple(
                sorted(matches, key=lambda student: (_search_key(student.full_name), student.id))
            )
            page_items = ordered[criteria.offset : criteria.offset + criteria.limit]
            return StudentSearchResult(
                items=tuple(_to_list_item(student) for student in page_items),
                total=len(ordered),
            )
