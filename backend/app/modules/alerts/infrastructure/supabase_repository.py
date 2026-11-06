"""Adaptador das operações de alertas no Supabase."""

from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from backend.app.modules.alerts.application.dtos import AlertInput, AlertOutput
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


class SupabaseAlertRepository:
    def __init__(self, gateway: SupabaseRPCGateway, context: RequestContext) -> None:
        self.gateway = gateway
        self.context = context

    async def list_open(self) -> tuple[AlertOutput, ...]:
        result = await self._call("list_open_attendance_alerts", {})
        try:
            return tuple(TypeAdapter(list[AlertOutput]).validate_python(result))
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    async def upsert(self, payload: AlertInput) -> AlertOutput:
        result = await self._call(
            "upsert_attendance_alert",
            {
                "p_student_id": str(payload.student_id),
                "p_class_id": str(payload.class_id) if payload.class_id else None,
                "p_alert_type": payload.alert_type.value,
                "p_title": payload.title,
                "p_detail": payload.detail,
                "p_threshold": payload.threshold,
            },
        )
        return self._parse(result)

    async def resolve(self, alert_id: UUID) -> AlertOutput:
        result = await self._call(
            "resolve_attendance_alert",
            {"p_alert_id": str(alert_id)},
        )
        return self._parse(result)

    async def _call(self, name: str, payload: dict[str, object]) -> object:
        try:
            return await self.gateway.call(name, payload, self.context)
        except SupabaseTransportError as error:
            raise PersistenceUnavailableError from error
        except SupabaseRPCError as error:
            if error.status_code == 403 or error.message_code == "alert_forbidden":
                raise PermissionDeniedError from error
            if error.status_code >= 500:
                raise PersistenceUnavailableError from error
            raise PersistenceRejectedError from error

    @staticmethod
    def _parse(result: object) -> AlertOutput:
        try:
            return AlertOutput.model_validate(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error
