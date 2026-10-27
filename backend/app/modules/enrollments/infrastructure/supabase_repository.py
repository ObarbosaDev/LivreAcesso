"""Persistência remota de matrículas por RPCs protegidas."""

from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict

from backend.app.modules.enrollments.domain.entities import Enrollment, EnrollmentStatus
from backend.app.modules.enrollments.domain.exceptions import (
    ClassCapacityReachedError,
    DuplicateEnrollmentError,
    EnrollmentNotFoundError,
    EnrollmentVersionConflictError,
)
from backend.app.modules.enrollments.domain.repositories import EnrollmentRepository
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


class _EnrollmentRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    student_id: UUID
    class_id: UUID
    status: EnrollmentStatus
    created_at: AwareDatetime
    updated_at: AwareDatetime


class SupabaseEnrollmentRepository(EnrollmentRepository):
    """Traduz o agregado para RPCs; tabelas nunca são acessadas diretamente."""

    def __init__(self, gateway: SupabaseRPCGateway, context: RequestContext) -> None:
        self._gateway = gateway
        self._context = context

    async def add(self, enrollment: Enrollment) -> Enrollment:
        # O UUID nasce na aplicação para que eventos e auditoria usem a mesma
        # identidade antes e depois da persistência. Timestamps, porém, vêm do
        # PostgreSQL para manter a concorrência otimista autoritativa.
        result = await self._call(
            "register_enrollment",
            {
                "p_enrollment_id": str(enrollment.id),
                "p_student_id": str(enrollment.student_id),
                "p_class_id": str(enrollment.class_id),
                "p_request_id": str(self._context.request_id),
            },
        )
        return self._to_domain(result)

    async def get(self, enrollment_id: UUID) -> Enrollment | None:
        try:
            return self._to_domain(
                await self._call("get_enrollment", {"p_enrollment_id": str(enrollment_id)})
            )
        except EnrollmentNotFoundError:
            return None

    async def find_active(self, student_id: UUID, class_id: UUID) -> Enrollment | None:
        # Esta consulta existe como RPC própria para manter a tabela protegida
        # e permitir que a aplicação valide duplicidade com o mesmo contrato
        # usado pelo PostgREST em produção.
        result = await self._call(
            "get_active_enrollment",
            {"p_student_id": str(student_id), "p_class_id": str(class_id)},
        )
        return self._to_domain(result) if result is not None else None

    async def update(self, enrollment: Enrollment, *, expected_updated_at: datetime) -> Enrollment:
        result = await self._call(
            "change_enrollment_status",
            {
                "p_enrollment_id": str(enrollment.id),
                "p_target_status": enrollment.status.value,
                "p_expected_updated_at": expected_updated_at.isoformat(),
                "p_reason": "Alteração de status solicitada pela coordenação.",
                "p_request_id": str(self._context.request_id),
            },
        )
        return self._to_domain(result)

    async def list(
        self,
        *,
        student_id: UUID | None,
        class_id: UUID | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Enrollment], int]:
        # A RPC devolve items e total no mesmo contrato, evitando uma segunda
        # consulta e preservando paginação correta quando a página está vazia.
        result = await self._call(
            "list_enrollments",
            {
                "p_student_id": str(student_id) if student_id else None,
                "p_class_id": str(class_id) if class_id else None,
                "p_status": status,
                "p_limit": limit,
                "p_offset": offset,
            },
        )
        if (
            not isinstance(result, dict)
            or not isinstance(result.get("items"), list)
            or not isinstance(result.get("total"), int)
        ):
            raise PersistenceUnavailableError
        return [self._to_domain(item) for item in result["items"]], result["total"]

    @staticmethod
    def _to_domain(result: object) -> Enrollment:
        try:
            row = _EnrollmentRow.model_validate(result)
        except ValueError as error:
            raise PersistenceUnavailableError from error
        return Enrollment(
            id=row.id,
            student_id=row.student_id,
            class_id=row.class_id,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _call(self, function_name: str, payload: dict[str, object]) -> object:
        try:
            return await self._gateway.call(function_name, payload, self._context)
        except SupabaseTransportError as error:
            raise PersistenceUnavailableError from error
        except SupabaseRPCError as error:
            if error.status_code == 403 or error.message_code == "forbidden":
                raise PermissionDeniedError from error
            mapping = {
                "duplicate_enrollment": DuplicateEnrollmentError,
                "class_capacity_reached": ClassCapacityReachedError,
                "enrollment_not_found": EnrollmentNotFoundError,
                "enrollment_version_conflict": EnrollmentVersionConflictError,
            }
            mapped = mapping.get(error.message_code or "")
            if mapped is not None:
                raise mapped from error
            if error.status_code >= 500:
                raise PersistenceUnavailableError from error
            raise PersistenceRejectedError from error
