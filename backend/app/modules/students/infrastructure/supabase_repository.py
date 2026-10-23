"""Persistência de alunos e responsáveis por funções RPC protegidas do Supabase."""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    TypeAdapter,
    ValidationError,
)

from backend.app.modules.identity.application.authentication import InvalidAccessTokenError
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
    StudentStatus,
)
from backend.app.modules.students.domain.exceptions import (
    DuplicateCPFError,
    GuardianAlreadyLinkedError,
    GuardianNotFoundError,
    GuardianVersionConflictError,
    InvalidGuardianUnlinkReasonError,
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
    CPF,
    GuardianUnlinkReason,
    Phone,
    StatusChangeReason,
)
from backend.app.shared.application.exceptions import (
    PermissionDeniedError,
    PersistenceRejectedError,
    PersistenceUnavailableError,
)
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import (
    SupabaseRPCError,
    SupabaseRPCGateway,
    SupabaseTransportError,
)


class _DatabaseStudentStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class _DatabaseGuardianRelationship(StrEnum):
    RESPONSIBLE_CONTACT = "responsible_contact"
    LEGAL_GUARDIAN = "legal_guardian"
    PARENT = "parent"
    EMERGENCY_CONTACT = "emergency_contact"
    SELF = "self"
    OTHER = "other"


_RELATIONSHIP_TO_DATABASE = {
    GuardianRelationship.RESPONSIBLE_CONTACT: _DatabaseGuardianRelationship.RESPONSIBLE_CONTACT,
    GuardianRelationship.LEGAL_GUARDIAN: _DatabaseGuardianRelationship.LEGAL_GUARDIAN,
    GuardianRelationship.PARENT: _DatabaseGuardianRelationship.PARENT,
    GuardianRelationship.EMERGENCY_CONTACT: _DatabaseGuardianRelationship.EMERGENCY_CONTACT,
    GuardianRelationship.SELF: _DatabaseGuardianRelationship.SELF,
    GuardianRelationship.OTHER: _DatabaseGuardianRelationship.OTHER,
}
_RELATIONSHIP_FROM_DATABASE = {value: key for key, value in _RELATIONSHIP_TO_DATABASE.items()}


class _StudentListRow(BaseModel):
    """Contrato privado da RPC; mudança silenciosa no SQL falha de modo seguro."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    full_name: str
    cpf_masked: str = Field(pattern=r"^\*{3}\.\*{3}\.\*{3}-\d{2}$")
    birth_date: date
    age: int = Field(ge=0, le=120)
    status: _DatabaseStudentStatus
    guardian_name: str | None
    guardian_phone_masked: str | None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class _StudentSearchResponse(BaseModel):
    """Envelope que preserva o total mesmo quando a página está vazia."""

    model_config = ConfigDict(extra="forbid")

    items: list[_StudentListRow]
    total: int = Field(ge=0)


class _GuardianDetailRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    full_name: str
    phone: str
    email: EmailStr | None


class _StudentDetailRow(BaseModel):
    """Contrato sensível retornado somente pela RPC auditada de detalhe."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    full_name: str
    cpf: str = Field(pattern=r"^\d{11}$")
    birth_date: date
    status: _DatabaseStudentStatus
    guardian: _GuardianDetailRow
    created_at: AwareDatetime
    updated_at: AwareDatetime


class _CreatedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    created_at: AwareDatetime
    updated_at: AwareDatetime


class _MutationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    updated_at: AwareDatetime


class _StudentGuardianListRow(BaseModel):
    """Contrato mascarado da listagem de responsáveis."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    full_name: str
    phone_masked: str = Field(pattern=r"^\(\d{2}\) \*{5}-\d{4}$")
    email_masked: str | None
    relationship: _DatabaseGuardianRelationship
    is_primary: bool
    receives_communications: bool
    linked_at: AwareDatetime
    guardian_updated_at: AwareDatetime


class _StudentGuardianListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: UUID
    student_updated_at: AwareDatetime
    items: list[_StudentGuardianListRow]


class _StudentGuardianDetailRow(BaseModel):
    """Contrato integral liberado somente por leitura ou escrita auditada."""

    model_config = ConfigDict(extra="forbid")

    student_id: UUID
    student_updated_at: AwareDatetime
    id: UUID
    full_name: str
    phone: str
    email: EmailStr | None
    relationship: _DatabaseGuardianRelationship
    is_primary: bool
    receives_communications: bool
    active: bool
    linked_at: AwareDatetime
    guardian_updated_at: AwareDatetime


class _StudentGuardianMutationRow(_StudentGuardianDetailRow):
    changed: bool


class _StudentGuardianUnlinkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: UUID
    guardian_id: UUID
    student_updated_at: AwareDatetime
    changed: bool


_STUDENT_SEARCH_RESPONSE = TypeAdapter(_StudentSearchResponse)
_STUDENT_DETAIL_RESPONSE = TypeAdapter(_StudentDetailRow)
_CREATED_RESPONSE = TypeAdapter(_CreatedResponse)
_MUTATION_RESPONSE = TypeAdapter(_MutationResponse)
_GUARDIAN_LIST_RESPONSE = TypeAdapter(_StudentGuardianListResponse)
_GUARDIAN_DETAIL_RESPONSE = TypeAdapter(_StudentGuardianDetailRow)
_GUARDIAN_MUTATION_RESPONSE = TypeAdapter(_StudentGuardianMutationRow)
_GUARDIAN_UNLINK_RESPONSE = TypeAdapter(_StudentGuardianUnlinkResponse)


class SupabaseStudentRepository:
    """Implementa escrita, detalhe e consulta usando o JWT da requisição atual."""

    def __init__(self, gateway: SupabaseRPCGateway, context: RequestContext) -> None:
        self._gateway = gateway
        self._context = context

    async def add(self, student: Student) -> PersistedStudentVersion:
        payload: dict[str, object] = {
            "p_student_id": str(student.id),
            "p_guardian_id": str(student.guardian.id),
            "p_request_id": str(self._context.request_id),
            "p_full_name": student.full_name,
            "p_cpf": student.cpf.value,
            "p_birth_date": student.birth_date.isoformat(),
            "p_guardian_full_name": student.guardian.full_name,
            "p_guardian_phone": student.guardian.phone.value,
            "p_guardian_email": student.guardian.email,
            # "Contato responsável" é neutro. Declarar parentesco ou guarda
            # legal sem confirmação produziria um dado potencialmente falso.
            "p_relationship": "responsible_contact",
        }
        result = await self._call("register_student_with_guardian_v2", payload)

        try:
            created = _CREATED_RESPONSE.validate_python(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error
        if created.id != student.id:
            raise PersistenceUnavailableError

        # O PostgreSQL é a autoridade temporal. Esses valores voltam ao caso de
        # uso para que a primeira edição compare exatamente a versão persistida.
        return PersistedStudentVersion(
            created_at=created.created_at,
            updated_at=created.updated_at,
        )

    async def get_by_id(self, student_id: UUID) -> Student | None:
        try:
            result = await self._call(
                "get_student_detail",
                {
                    "p_student_id": str(student_id),
                    "p_request_id": str(self._context.request_id),
                },
            )
        except StudentNotFoundError:
            return None

        try:
            row = _STUDENT_DETAIL_RESPONSE.validate_python(result)
            return self._to_domain(row)
        except (ValidationError, ValueError) as error:
            # CPF e telefone são validados novamente ao reidratar o agregado.
            # Qualquer divergência do banco vira indisponibilidade, não dado parcial.
            raise PersistenceUnavailableError from error

    async def update(
        self,
        student: Student,
        *,
        expected_updated_at: datetime,
    ) -> datetime:
        result = await self._call(
            "update_student",
            {
                "p_student_id": str(student.id),
                "p_request_id": str(self._context.request_id),
                "p_expected_updated_at": expected_updated_at.isoformat(),
                "p_full_name": student.full_name,
                "p_birth_date": student.birth_date.isoformat(),
            },
        )
        return self._mutation_timestamp(result)

    async def change_status(
        self,
        student: Student,
        *,
        reason: StatusChangeReason,
        expected_updated_at: datetime,
    ) -> datetime:
        database_status = (
            _DatabaseStudentStatus.ACTIVE
            if student.status is StudentStatus.ACTIVE
            else _DatabaseStudentStatus.INACTIVE
        )
        result = await self._call(
            "change_student_status",
            {
                "p_student_id": str(student.id),
                "p_request_id": str(self._context.request_id),
                "p_expected_updated_at": expected_updated_at.isoformat(),
                "p_target_status": database_status.value,
                # O motivo é PII potencial e só segue para a função transacional;
                # o gateway não registra payload e o evento não replica o texto.
                "p_reason": reason.value,
            },
        )
        return self._mutation_timestamp(result)

    async def search(self, criteria: StudentSearchCriteria) -> StudentSearchResult:
        database_status = (
            _DatabaseStudentStatus.ACTIVE
            if criteria.status is StudentStatus.ACTIVE
            else _DatabaseStudentStatus.INACTIVE
            if criteria.status is StudentStatus.INACTIVE
            else None
        )
        payload: dict[str, object] = {
            "p_status": database_status.value if database_status else None,
            "p_query": criteria.query,
            "p_limit": criteria.limit,
            "p_offset": criteria.offset,
        }
        result = await self._call("list_students", payload)

        try:
            response = _STUDENT_SEARCH_RESPONSE.validate_python(result)
        except ValidationError as error:
            # Divergência entre migration e adaptador é falha operacional. Os
            # detalhes do payload externo não seguem para log nem resposta.
            raise PersistenceUnavailableError from error

        return StudentSearchResult(
            items=tuple(self._to_list_item(row) for row in response.items),
            total=response.total,
        )

    async def list_guardians(self, student_id: UUID) -> StudentGuardianListResult:
        result = await self._call(
            "list_student_guardians",
            {"p_student_id": str(student_id)},
        )
        try:
            response = _GUARDIAN_LIST_RESPONSE.validate_python(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error
        return StudentGuardianListResult(
            student_id=response.student_id,
            student_updated_at=response.student_updated_at,
            items=tuple(self._to_guardian_list_item(item) for item in response.items),
        )

    async def get_guardian(
        self,
        student_id: UUID,
        guardian_id: UUID,
    ) -> StudentGuardianSnapshot:
        result = await self._call(
            "get_student_guardian_detail",
            {
                "p_student_id": str(student_id),
                "p_guardian_id": str(guardian_id),
                "p_request_id": str(self._context.request_id),
            },
        )
        try:
            row = _GUARDIAN_DETAIL_RESPONSE.validate_python(result)
            return self._to_guardian_snapshot(row)
        except (ValidationError, ValueError) as error:
            raise PersistenceUnavailableError from error

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
        if (guardian is None) == (existing_guardian_id is None):
            raise ValueError("A origem do responsável é ambígua.")
        guardian_id = guardian.id if guardian is not None else existing_guardian_id
        assert guardian_id is not None
        result = await self._call(
            "add_student_guardian",
            {
                "p_student_id": str(student_id),
                "p_guardian_id": str(guardian_id),
                "p_request_id": str(self._context.request_id),
                "p_expected_student_updated_at": expected_student_updated_at.isoformat(),
                "p_create_guardian": guardian is not None,
                "p_guardian_full_name": guardian.full_name if guardian is not None else None,
                "p_guardian_phone": guardian.phone.value if guardian is not None else None,
                "p_guardian_email": guardian.email if guardian is not None else None,
                "p_relationship": _RELATIONSHIP_TO_DATABASE[relationship].value,
                "p_make_primary": make_primary,
                "p_receives_communications": receives_communications,
            },
        )
        return self._guardian_mutation(result)

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
        result = await self._call(
            "update_student_guardian",
            {
                "p_student_id": str(student_id),
                "p_guardian_id": str(guardian.id),
                "p_request_id": str(self._context.request_id),
                "p_expected_student_updated_at": expected_student_updated_at.isoformat(),
                "p_expected_guardian_updated_at": expected_guardian_updated_at.isoformat(),
                "p_guardian_full_name": guardian.full_name,
                "p_guardian_phone": guardian.phone.value,
                "p_guardian_email": guardian.email,
                "p_relationship": _RELATIONSHIP_TO_DATABASE[relationship].value,
                "p_receives_communications": receives_communications,
            },
        )
        return self._guardian_mutation(result)

    async def set_primary_guardian(
        self,
        student_id: UUID,
        guardian_id: UUID,
        *,
        expected_student_updated_at: datetime,
    ) -> StudentGuardianMutation:
        result = await self._call(
            "set_primary_student_guardian",
            {
                "p_student_id": str(student_id),
                "p_guardian_id": str(guardian_id),
                "p_request_id": str(self._context.request_id),
                "p_expected_student_updated_at": expected_student_updated_at.isoformat(),
            },
        )
        return self._guardian_mutation(result)

    async def unlink_guardian(
        self,
        student_id: UUID,
        guardian_id: UUID,
        *,
        reason: GuardianUnlinkReason,
        expected_student_updated_at: datetime,
    ) -> StudentGuardianUnlinkResult:
        result = await self._call(
            "unlink_student_guardian",
            {
                "p_student_id": str(student_id),
                "p_guardian_id": str(guardian_id),
                "p_request_id": str(self._context.request_id),
                "p_expected_student_updated_at": expected_student_updated_at.isoformat(),
                # A justificativa segue apenas no corpo HTTPS até a tabela privada.
                "p_reason": reason.value,
            },
        )
        try:
            response = _GUARDIAN_UNLINK_RESPONSE.validate_python(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error
        return StudentGuardianUnlinkResult(
            student_id=response.student_id,
            guardian_id=response.guardian_id,
            student_updated_at=response.student_updated_at,
            changed=response.changed,
        )

    async def _call(self, function_name: str, payload: dict[str, object]) -> object:
        try:
            return await self._gateway.call(function_name, payload, self._context)
        except SupabaseTransportError as error:
            raise PersistenceUnavailableError from error
        except SupabaseRPCError as error:
            if error.status_code == 401:
                raise InvalidAccessTokenError from error
            if (
                error.status_code == 403
                or error.database_code == "42501"
                or error.message_code == "forbidden"
            ):
                raise PermissionDeniedError from error
            if error.message_code == "guardian_already_linked":
                raise GuardianAlreadyLinkedError from error
            if error.message_code in {"guardian_not_found", "guardian_link_not_found"}:
                raise GuardianNotFoundError from error
            if error.message_code == "primary_guardian_required":
                raise PrimaryGuardianRequiredError from error
            if error.message_code == "guardian_version_conflict":
                raise GuardianVersionConflictError from error
            if error.message_code == "invalid_guardian_unlink_reason":
                raise InvalidGuardianUnlinkReasonError from error
            if error.database_code == "23505" or error.message_code == "duplicate_cpf":
                raise DuplicateCPFError from error
            if error.message_code == "student_not_found":
                raise StudentNotFoundError from error
            if error.message_code == "student_version_conflict":
                raise StudentVersionConflictError from error
            if error.status_code == 404 or error.status_code >= 500:
                raise PersistenceUnavailableError from error
            raise PersistenceRejectedError from error

    @staticmethod
    def _mutation_timestamp(result: object) -> datetime:
        try:
            response = _MUTATION_RESPONSE.validate_python(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error
        return response.updated_at

    @staticmethod
    def _guardian_mutation(result: object) -> StudentGuardianMutation:
        try:
            response = _GUARDIAN_MUTATION_RESPONSE.validate_python(result)
            snapshot = SupabaseStudentRepository._to_guardian_snapshot(response)
        except (ValidationError, ValueError) as error:
            raise PersistenceUnavailableError from error
        return StudentGuardianMutation(snapshot=snapshot, changed=response.changed)

    @staticmethod
    def _to_domain(row: _StudentDetailRow) -> Student:
        status = (
            StudentStatus.ACTIVE
            if row.status is _DatabaseStudentStatus.ACTIVE
            else StudentStatus.INACTIVE
        )
        return Student(
            id=row.id,
            full_name=row.full_name,
            cpf=CPF(row.cpf),
            birth_date=row.birth_date,
            guardian=Guardian(
                id=row.guardian.id,
                full_name=row.guardian.full_name,
                phone=Phone(row.guardian.phone),
                email=str(row.guardian.email) if row.guardian.email else None,
            ),
            status=status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_list_item(row: _StudentListRow) -> StudentListItem:
        status = (
            StudentStatus.ACTIVE
            if row.status is _DatabaseStudentStatus.ACTIVE
            else StudentStatus.INACTIVE
        )
        return StudentListItem(
            id=row.id,
            full_name=row.full_name,
            cpf_masked=row.cpf_masked,
            birth_date=row.birth_date,
            age=row.age,
            status=status,
            guardian_name=row.guardian_name,
            guardian_phone_masked=row.guardian_phone_masked,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_guardian_list_item(row: _StudentGuardianListRow) -> StudentGuardianListItem:
        return StudentGuardianListItem(
            id=row.id,
            full_name=row.full_name,
            phone_masked=row.phone_masked,
            email_masked=row.email_masked,
            relationship=_RELATIONSHIP_FROM_DATABASE[row.relationship],
            is_primary=row.is_primary,
            receives_communications=row.receives_communications,
            linked_at=row.linked_at,
            guardian_updated_at=row.guardian_updated_at,
        )

    @staticmethod
    def _to_guardian_snapshot(row: _StudentGuardianDetailRow) -> StudentGuardianSnapshot:
        return StudentGuardianSnapshot(
            student_updated_at=row.student_updated_at,
            link=StudentGuardian(
                student_id=row.student_id,
                guardian=Guardian(
                    id=row.id,
                    full_name=row.full_name,
                    phone=Phone(row.phone),
                    email=str(row.email) if row.email else None,
                ),
                relationship=_RELATIONSHIP_FROM_DATABASE[row.relationship],
                is_primary=row.is_primary,
                receives_communications=row.receives_communications,
                active=row.active,
                linked_at=row.linked_at,
                guardian_updated_at=row.guardian_updated_at,
            ),
        )
