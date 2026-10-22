"""Persistência de alunos por funções RPC protegidas do Supabase."""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from backend.app.modules.identity.application.authentication import InvalidAccessTokenError
from backend.app.modules.students.application.queries import (
    StudentListItem,
    StudentSearchCriteria,
    StudentSearchResult,
)
from backend.app.modules.students.domain.entities import Student, StudentStatus
from backend.app.modules.students.domain.exceptions import DuplicateCPFError
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
    created_at: datetime


class _StudentSearchResponse(BaseModel):
    """Envelope que preserva o total mesmo quando a página está vazia."""

    model_config = ConfigDict(extra="forbid")

    items: list[_StudentListRow]
    total: int = Field(ge=0)


_STUDENT_SEARCH_RESPONSE = TypeAdapter(_StudentSearchResponse)


class SupabaseStudentRepository:
    """Implementa escrita e consulta usando o JWT da requisição atual."""

    def __init__(self, gateway: SupabaseRPCGateway, context: RequestContext) -> None:
        self._gateway = gateway
        self._context = context

    async def add(self, student: Student) -> None:
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
        result = await self._call("register_student_with_guardian", payload)

        # A aplicação gera o UUID antes da transação para que evento, auditoria
        # e resposta apontem para o mesmo agregado sem mutação após persistência.
        if result != str(student.id):
            raise PersistenceUnavailableError

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
            if error.status_code >= 500:
                raise PersistenceUnavailableError from error
            raise PersistenceRejectedError from error

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
        )
