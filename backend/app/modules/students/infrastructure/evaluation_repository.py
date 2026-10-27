"""Adaptador das avaliações para as RPCs protegidas do Supabase."""

from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from backend.app.modules.students.application.evaluation_dtos import (
    StudentEvaluationInput,
    StudentEvaluationOutput,
)
from backend.app.modules.students.domain.evaluation_repositories import (
    StudentEvaluationRepository,
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


class SupabaseStudentEvaluationRepository(StudentEvaluationRepository):
    def __init__(self, gateway: SupabaseRPCGateway) -> None:
        self._gateway = gateway

    async def create(
        self, student_id: UUID, payload: StudentEvaluationInput, context: RequestContext
    ) -> StudentEvaluationOutput:
        body = payload.model_dump(mode="json")
        body.update({"p_student_id": str(student_id), "p_request_id": str(context.request_id)})
        result = await self._call("create_student_evaluation", body, context)
        return self._parse_one(result)

    async def list(
        self, student_id: UUID, context: RequestContext
    ) -> list[StudentEvaluationOutput]:
        result = await self._call(
            "list_student_evaluations",
            {"p_student_id": str(student_id)},
            context,
        )
        try:
            return TypeAdapter(list[StudentEvaluationOutput]).validate_python(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    @staticmethod
    def _parse_one(result: object) -> StudentEvaluationOutput:
        try:
            return StudentEvaluationOutput.model_validate(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    async def _call(self, name: str, payload: dict[str, object], context: RequestContext) -> object:
        try:
            return await self._gateway.call(name, payload, context)
        except SupabaseTransportError as error:
            raise PersistenceUnavailableError from error
        except SupabaseRPCError as error:
            if error.status_code == 403 or error.message_code == "forbidden":
                raise PermissionDeniedError from error
            if error.status_code >= 500:
                raise PersistenceUnavailableError from error
            raise PersistenceRejectedError from error
