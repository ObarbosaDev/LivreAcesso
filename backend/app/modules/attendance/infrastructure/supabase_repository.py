"""Adaptador de frequência para as RPCs protegidas do Supabase."""

from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from backend.app.modules.attendance.application.dtos import (
    AttendanceMarkInput,
    AttendanceSessionOutput,
    AttendanceSessionPageOutput,
    AttendanceSummaryPageOutput,
    OpenAttendanceInput,
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

_marks_adapter = TypeAdapter(tuple[AttendanceMarkInput, ...])


class SupabaseAttendanceRepository:
    """Chama somente as RPCs de frequência e valida cada resposta externa."""

    def __init__(self, gateway: SupabaseRPCGateway, context: RequestContext | None = None) -> None:
        self._gateway = gateway
        self._context = context

    async def open(self, payload: OpenAttendanceInput) -> AttendanceSessionOutput:
        result = await self._call(
            "open_attendance_session",
            {
                "p_class_id": str(payload.class_id),
                "p_session_date": payload.session_date.isoformat(),
            },
        )
        return self._parse(result)

    async def record(
        self, session_id: UUID, marks: tuple[AttendanceMarkInput, ...]
    ) -> AttendanceSessionOutput:
        result = await self._call(
            "record_attendance",
            {
                "p_session_id": str(session_id),
                "p_marks": [mark.model_dump(mode="json") for mark in marks],
            },
        )
        return self._parse(result)

    async def close(self, session_id: UUID) -> AttendanceSessionOutput:
        result = await self._call(
            "close_attendance_session",
            {"p_session_id": str(session_id)},
        )
        return self._parse(result)

    async def list_sessions(
        self, class_id: UUID, *, limit: int, offset: int
    ) -> AttendanceSessionPageOutput:
        result = await self._call(
            "list_attendance_sessions",
            {"p_class_id": str(class_id), "p_limit": limit, "p_offset": offset},
        )
        try:
            return AttendanceSessionPageOutput.model_validate(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    async def summary(self, class_id: UUID) -> AttendanceSummaryPageOutput:
        result = await self._call("list_attendance_summary", {"p_class_id": str(class_id)})
        try:
            return AttendanceSummaryPageOutput.model_validate(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    async def session_marks(self, session_id: UUID) -> tuple[AttendanceMarkInput, ...]:
        result = await self._call("list_attendance_marks", {"p_session_id": str(session_id)})
        try:
            return _marks_adapter.validate_python(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    async def archive_old_sessions(self) -> int:
        result = await self._gateway.call_service("archive_old_attendance_sessions", {})
        try:
            return int(result)
        except (TypeError, ValueError) as error:
            raise PersistenceUnavailableError from error

    async def _call(self, name: str, payload: dict[str, object]) -> object:
        if self._context is None:
            raise RuntimeError("Esta chamada exige um contexto de requisição autenticado.")
        try:
            return await self._gateway.call(name, payload, self._context)
        except SupabaseTransportError as error:
            raise PersistenceUnavailableError from error
        except SupabaseRPCError as error:
            if error.status_code == 403 or error.message_code == "attendance_forbidden":
                raise PermissionDeniedError from error
            if error.status_code >= 500:
                raise PersistenceUnavailableError from error
            raise PersistenceRejectedError from error

    @staticmethod
    def _parse(result: object) -> AttendanceSessionOutput:
        try:
            return AttendanceSessionOutput.model_validate(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error
