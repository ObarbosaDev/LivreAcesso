"""Adaptadores de persistência disponíveis para o módulo de alunos."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from threading import RLock
from unicodedata import combining, normalize
from uuid import UUID

from backend.app.modules.students.application.queries import (
    StudentListItem,
    StudentSearchCriteria,
    StudentSearchResult,
)
from backend.app.modules.students.domain.entities import Student
from backend.app.modules.students.domain.exceptions import (
    DuplicateCPFError,
    StudentNotFoundError,
    StudentVersionConflictError,
)
from backend.app.modules.students.domain.value_objects import StatusChangeReason


def _search_key(value: str) -> str:
    """Produz comparação sem diferença de caixa ou acento para busca por nome."""

    decomposed = normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not combining(character))


def _to_list_item(student: Student) -> StudentListItem:
    """Cria a mesma projeção mascarada que a RPC entrega em produção."""

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
        updated_at=student.updated_at,
    )


def _next_version(current: datetime) -> datetime:
    candidate = datetime.now(UTC)
    return candidate if candidate > current else current + timedelta(microseconds=1)


def _persistent_snapshot(student: Student) -> Student:
    """Copia estado persistente e remove a fila transitória de eventos."""

    snapshot = deepcopy(student)
    snapshot.pull_events()
    return snapshot


class InMemoryStudentRepository:
    """Adaptador transitório de escrita e leitura para desenvolvimento e testes."""

    def __init__(self) -> None:
        self._students: dict[UUID, Student] = {}
        self._student_ids_by_cpf: dict[str, UUID] = {}
        self._status_reasons: list[tuple[UUID, str]] = []
        self._lock = RLock()

    async def add(self, student: Student) -> None:
        with self._lock:
            # A verificação e a escrita compartilham o mesmo lock. Isso reproduz,
            # em menor escala, a garantia do índice único que existe no Postgres.
            if student.cpf.value in self._student_ids_by_cpf:
                raise DuplicateCPFError
            self._students[student.id] = _persistent_snapshot(student)
            self._student_ids_by_cpf[student.cpf.value] = student.id

    async def get_by_id(self, student_id: UUID) -> Student | None:
        with self._lock:
            student = self._students.get(student_id)
            # Retornar cópia impede que o caso de uso altere o estado persistido
            # antes de o controle de concorrência validar a versão esperada.
            return deepcopy(student) if student is not None else None

    async def update(
        self,
        student: Student,
        *,
        expected_updated_at: datetime,
    ) -> datetime:
        with self._lock:
            return self._save(student, expected_updated_at=expected_updated_at)

    async def change_status(
        self,
        student: Student,
        *,
        reason: StatusChangeReason,
        expected_updated_at: datetime,
    ) -> datetime:
        with self._lock:
            updated_at = self._save(student, expected_updated_at=expected_updated_at)
            # O adaptador em memória preserva o motivo apenas para reproduzir o
            # comportamento do histórico; nenhum log recebe esse texto.
            self._status_reasons.append((student.id, reason.value))
            return updated_at

    async def search(self, criteria: StudentSearchCriteria) -> StudentSearchResult:
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

    def _save(self, student: Student, *, expected_updated_at: datetime) -> datetime:
        current = self._students.get(student.id)
        if current is None:
            raise StudentNotFoundError
        if current.updated_at != expected_updated_at:
            raise StudentVersionConflictError

        updated_at = _next_version(current.updated_at)
        student.mark_persisted(updated_at)
        self._students[student.id] = _persistent_snapshot(student)
        return updated_at
