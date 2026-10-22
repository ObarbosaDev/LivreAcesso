"""Persistência de alunos por funções RPC protegidas do Supabase."""

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
    StudentListItem,
    StudentSearchCriteria,
    StudentSearchResult,
)
from backend.app.modules.students.domain.entities import Guardian, Student, StudentStatus
from backend.app.modules.students.domain.exceptions import (
    DuplicateCPFError,
    StudentNotFoundError,
    StudentVersionConflictError,
)
from backend.app.modules.students.domain.repositories import (
    PersistedStudentVersion,
)
from backend.app.modules.students.domain.value_objects import CPF, Phone, StatusChangeReason
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


_STUDENT_SEARCH_RESPONSE = TypeAdapter(_StudentSearchResponse)
_STUDENT_DETAIL_RESPONSE = TypeAdapter(_StudentDetailRow)
_CREATED_RESPONSE = TypeAdapter(_CreatedResponse)
_MUTATION_RESPONSE = TypeAdapter(_MutationResponse)


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
            "update_student_with_guardian",
            {
                "p_student_id": str(student.id),
                "p_request_id": str(self._context.request_id),
                "p_expected_updated_at": expected_updated_at.isoformat(),
                "p_full_name": student.full_name,
                "p_birth_date": student.birth_date.isoformat(),
                "p_guardian_full_name": student.guardian.full_name,
                "p_guardian_phone": student.guardian.phone.value,
                "p_guardian_email": student.guardian.email,
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
            if (
                error.status_code == 409
                or error.database_code == "23505"
                or error.message_code == "duplicate_cpf"
            ):
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
