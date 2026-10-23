"""Adaptadores de persistência disponíveis para o módulo de alunos."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from threading import RLock
from unicodedata import combining, normalize
from uuid import UUID

from backend.app.modules.students.application.queries import (
    StudentGuardianListItem,
    StudentGuardianListResult,
    StudentListItem,
    StudentSearchCriteria,
    StudentSearchResult,
)
from backend.app.modules.students.domain.entities import (
    Guardian,
    GuardianRelationship,
    Student,
    StudentGuardian,
)
from backend.app.modules.students.domain.exceptions import (
    DuplicateCPFError,
    GuardianAlreadyLinkedError,
    GuardianNotFoundError,
    GuardianVersionConflictError,
    PrimaryGuardianRequiredError,
    StudentNotFoundError,
    StudentVersionConflictError,
)
from backend.app.modules.students.domain.repositories import (
    PersistedStudentVersion,
    StudentGuardianMutation,
    StudentGuardianSnapshot,
    StudentGuardianUnlinkResult,
)
from backend.app.modules.students.domain.value_objects import (
    GuardianUnlinkReason,
    StatusChangeReason,
)


def _search_key(value: str) -> str:
    """Produz comparação sem diferença de caixa ou acento para busca por nome."""

    decomposed = normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not combining(character))


def _mask_email(value: str | None) -> str | None:
    """Preserva contexto suficiente para reconhecer o contato sem expor o endereço."""

    if value is None:
        return None
    local, separator, domain = value.partition("@")
    if not separator:
        return "***"
    return f"{local[:1]}***@{domain}"


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
        self._guardians: dict[UUID, Guardian] = {}
        self._guardian_versions: dict[UUID, datetime] = {}
        self._guardian_links: dict[tuple[UUID, UUID], StudentGuardian] = {}
        self._guardian_unlink_reasons: list[tuple[UUID, UUID, str]] = []
        self._lock = RLock()

    async def add(self, student: Student) -> PersistedStudentVersion:
        with self._lock:
            # A verificação e a escrita compartilham o mesmo lock. Isso reproduz,
            # em menor escala, a garantia do índice único que existe no Postgres.
            if student.cpf.value in self._student_ids_by_cpf:
                raise DuplicateCPFError
            self._students[student.id] = _persistent_snapshot(student)
            self._student_ids_by_cpf[student.cpf.value] = student.id
            self._guardians[student.guardian.id] = deepcopy(student.guardian)
            self._guardian_versions[student.guardian.id] = student.created_at
            self._guardian_links[(student.id, student.guardian.id)] = StudentGuardian(
                student_id=student.id,
                guardian=deepcopy(student.guardian),
                relationship=GuardianRelationship.RESPONSIBLE_CONTACT,
                is_primary=True,
                receives_communications=True,
                active=True,
                linked_at=student.created_at,
                guardian_updated_at=student.created_at,
            )
            return PersistedStudentVersion(
                created_at=student.created_at,
                updated_at=student.updated_at,
            )

    async def get_by_id(self, student_id: UUID) -> Student | None:
        with self._lock:
            student = self._students.get(student_id)
            if student is None:
                return None
            # O responsável principal é reidratado do cadastro global. Assim,
            # irmãos vinculados ao mesmo contato sempre observam a última versão.
            return self._hydrate_primary_guardian(student)

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
                self._hydrate_primary_guardian(student)
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

    async def list_guardians(self, student_id: UUID) -> StudentGuardianListResult:
        with self._lock:
            student = self._require_student(student_id)
            links = [
                self._current_link(link)
                for (linked_student_id, _), link in self._guardian_links.items()
                if linked_student_id == student_id and link.active
            ]
            ordered = sorted(
                links,
                key=lambda link: (
                    not link.is_primary,
                    _search_key(link.guardian.full_name),
                    link.guardian.id,
                ),
            )
            return StudentGuardianListResult(
                student_id=student_id,
                student_updated_at=student.updated_at,
                items=tuple(
                    StudentGuardianListItem(
                        id=link.guardian.id,
                        full_name=link.guardian.full_name,
                        phone_masked=link.guardian.phone.masked,
                        email_masked=_mask_email(link.guardian.email),
                        relationship=link.relationship,
                        is_primary=link.is_primary,
                        receives_communications=link.receives_communications,
                        linked_at=link.linked_at,
                        guardian_updated_at=link.guardian_updated_at,
                    )
                    for link in ordered
                ),
            )

    async def get_guardian(
        self,
        student_id: UUID,
        guardian_id: UUID,
    ) -> StudentGuardianSnapshot:
        with self._lock:
            student = self._require_student(student_id)
            link = self._require_active_link(student_id, guardian_id)
            return self._snapshot(student, link)

    async def add_guardian(
        self,
        student_id: UUID,
        *,
        guardian: Guardian | None,
        existing_guardian_id: UUID | None,
        relationship: GuardianRelationship,
        make_primary: bool,
        receives_communications: bool,
        expected_student_updated_at: datetime,
    ) -> StudentGuardianMutation:
        with self._lock:
            student = self._require_student_version(student_id, expected_student_updated_at)
            if (guardian is None) == (existing_guardian_id is None):
                raise ValueError("A origem do responsável é ambígua.")

            selected: Guardian
            if guardian is not None:
                if guardian.id in self._guardians:
                    raise GuardianAlreadyLinkedError
                selected = deepcopy(guardian)
                self._guardians[selected.id] = selected
                self._guardian_versions[selected.id] = datetime.now(UTC)
            else:
                assert existing_guardian_id is not None
                stored_guardian = self._guardians.get(existing_guardian_id)
                if stored_guardian is None:
                    raise GuardianNotFoundError
                selected = deepcopy(stored_guardian)

            key = (student_id, selected.id)
            previous = self._guardian_links.get(key)
            if previous is not None and previous.active:
                raise GuardianAlreadyLinkedError

            if make_primary:
                self._demote_primary(student_id)
            linked_at = previous.linked_at if previous is not None else datetime.now(UTC)
            link = StudentGuardian(
                student_id=student_id,
                guardian=selected,
                relationship=relationship,
                is_primary=make_primary,
                receives_communications=receives_communications,
                active=True,
                linked_at=linked_at,
                guardian_updated_at=self._guardian_versions[selected.id],
            )
            self._guardian_links[key] = link
            if make_primary:
                student.guardian = deepcopy(selected)
            student_updated_at = self._touch_student(student)
            return StudentGuardianMutation(
                snapshot=self._snapshot(self._students[student_id], link, student_updated_at),
                changed=True,
            )

    async def update_guardian(
        self,
        student_id: UUID,
        guardian: Guardian,
        *,
        relationship: GuardianRelationship,
        receives_communications: bool,
        expected_student_updated_at: datetime,
        expected_guardian_updated_at: datetime,
    ) -> StudentGuardianMutation:
        with self._lock:
            student = self._require_student_version(student_id, expected_student_updated_at)
            link = self._require_active_link(student_id, guardian.id)
            current_guardian = self._guardians[guardian.id]
            current_guardian_version = self._guardian_versions[guardian.id]
            if current_guardian_version != expected_guardian_updated_at:
                raise GuardianVersionConflictError

            guardian_changed = current_guardian != guardian
            link_changed = (
                link.relationship is not relationship
                or link.receives_communications is not receives_communications
            )
            if not guardian_changed and not link_changed:
                return StudentGuardianMutation(
                    snapshot=self._snapshot(student, link),
                    changed=False,
                )

            if guardian_changed:
                self._guardians[guardian.id] = deepcopy(guardian)
                self._guardian_versions[guardian.id] = _next_version(current_guardian_version)
            updated_link = StudentGuardian(
                student_id=student_id,
                guardian=deepcopy(self._guardians[guardian.id]),
                relationship=relationship,
                is_primary=link.is_primary,
                receives_communications=receives_communications,
                active=True,
                linked_at=link.linked_at,
                guardian_updated_at=self._guardian_versions[guardian.id],
            )
            self._guardian_links[(student_id, guardian.id)] = updated_link
            if updated_link.is_primary:
                student.guardian = deepcopy(updated_link.guardian)
            student_updated_at = self._touch_student(student)
            return StudentGuardianMutation(
                snapshot=self._snapshot(
                    self._students[student_id], updated_link, student_updated_at
                ),
                changed=True,
            )

    async def set_primary_guardian(
        self,
        student_id: UUID,
        guardian_id: UUID,
        *,
        expected_student_updated_at: datetime,
    ) -> StudentGuardianMutation:
        with self._lock:
            student = self._require_student_version(student_id, expected_student_updated_at)
            link = self._require_active_link(student_id, guardian_id)
            if link.is_primary:
                return StudentGuardianMutation(
                    snapshot=self._snapshot(student, link),
                    changed=False,
                )

            self._demote_primary(student_id)
            promoted = StudentGuardian(
                student_id=student_id,
                guardian=deepcopy(self._guardians[guardian_id]),
                relationship=link.relationship,
                is_primary=True,
                receives_communications=link.receives_communications,
                active=True,
                linked_at=link.linked_at,
                guardian_updated_at=self._guardian_versions[guardian_id],
            )
            self._guardian_links[(student_id, guardian_id)] = promoted
            student.guardian = deepcopy(promoted.guardian)
            student_updated_at = self._touch_student(student)
            return StudentGuardianMutation(
                snapshot=self._snapshot(self._students[student_id], promoted, student_updated_at),
                changed=True,
            )

    async def unlink_guardian(
        self,
        student_id: UUID,
        guardian_id: UUID,
        *,
        reason: GuardianUnlinkReason,
        expected_student_updated_at: datetime,
    ) -> StudentGuardianUnlinkResult:
        with self._lock:
            student = self._require_student_version(student_id, expected_student_updated_at)
            link = self._require_active_link(student_id, guardian_id)
            if link.is_primary:
                raise PrimaryGuardianRequiredError

            self._guardian_links[(student_id, guardian_id)] = StudentGuardian(
                student_id=student_id,
                guardian=deepcopy(self._guardians[guardian_id]),
                relationship=link.relationship,
                is_primary=False,
                receives_communications=False,
                active=False,
                linked_at=link.linked_at,
                guardian_updated_at=self._guardian_versions[guardian_id],
            )
            self._guardian_unlink_reasons.append((student_id, guardian_id, reason.value))
            student_updated_at = self._touch_student(student)
            return StudentGuardianUnlinkResult(
                student_id=student_id,
                guardian_id=guardian_id,
                student_updated_at=student_updated_at,
                changed=True,
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

    def _require_student(self, student_id: UUID) -> Student:
        student = self._students.get(student_id)
        if student is None:
            raise StudentNotFoundError
        return student

    def _require_student_version(self, student_id: UUID, expected: datetime) -> Student:
        student = self._require_student(student_id)
        if student.updated_at != expected:
            raise StudentVersionConflictError
        return deepcopy(student)

    def _require_active_link(self, student_id: UUID, guardian_id: UUID) -> StudentGuardian:
        link = self._guardian_links.get((student_id, guardian_id))
        if link is None or not link.active:
            raise GuardianNotFoundError
        return self._current_link(link)

    def _current_link(self, link: StudentGuardian) -> StudentGuardian:
        guardian = self._guardians.get(link.guardian.id)
        version = self._guardian_versions.get(link.guardian.id)
        if guardian is None or version is None:
            raise GuardianNotFoundError
        return StudentGuardian(
            student_id=link.student_id,
            guardian=deepcopy(guardian),
            relationship=link.relationship,
            is_primary=link.is_primary,
            receives_communications=link.receives_communications,
            active=link.active,
            linked_at=link.linked_at,
            guardian_updated_at=version,
        )

    def _snapshot(
        self,
        student: Student,
        link: StudentGuardian,
        student_updated_at: datetime | None = None,
    ) -> StudentGuardianSnapshot:
        return StudentGuardianSnapshot(
            student_updated_at=student_updated_at or student.updated_at,
            link=self._current_link(link),
        )

    def _demote_primary(self, student_id: UUID) -> None:
        for key, link in tuple(self._guardian_links.items()):
            if key[0] != student_id or not link.active or not link.is_primary:
                continue
            self._guardian_links[key] = StudentGuardian(
                student_id=link.student_id,
                guardian=deepcopy(self._guardians[link.guardian.id]),
                relationship=link.relationship,
                is_primary=False,
                receives_communications=link.receives_communications,
                active=True,
                linked_at=link.linked_at,
                guardian_updated_at=self._guardian_versions[link.guardian.id],
            )

    def _touch_student(self, student: Student) -> datetime:
        current = self._students[student.id]
        updated_at = _next_version(current.updated_at)
        student.mark_persisted(updated_at)
        self._students[student.id] = _persistent_snapshot(student)
        return updated_at

    def _hydrate_primary_guardian(self, student: Student) -> Student:
        hydrated = deepcopy(student)
        primary = next(
            (
                link
                for (student_id, _), link in self._guardian_links.items()
                if student_id == student.id and link.active and link.is_primary
            ),
            None,
        )
        if primary is None:
            raise PrimaryGuardianRequiredError
        hydrated.guardian = deepcopy(self._guardians[primary.guardian.id])
        return hydrated
