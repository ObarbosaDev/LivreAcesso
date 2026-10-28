"""Adaptador das operações de alertas no Supabase."""

from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from backend.app.modules.alerts.application.dtos import AlertInput, AlertOutput
from backend.app.shared.application.exceptions import PersistenceUnavailableError
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway


class SupabaseAlertRepository:
    def __init__(self, gateway: SupabaseRPCGateway, context: RequestContext) -> None:
        self.gateway = gateway
        self.context = context

    async def list_open(self) -> tuple[AlertOutput, ...]:
        result = await self.gateway.call("list_open_attendance_alerts", {}, self.context)
        try:
            return tuple(TypeAdapter(list[AlertOutput]).validate_python(result))
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    async def upsert(self, payload: AlertInput) -> AlertOutput:
        result = await self.gateway.call(
            "upsert_attendance_alert",
            {
                "p_student_id": str(payload.student_id),
                "p_class_id": str(payload.class_id) if payload.class_id else None,
                "p_alert_type": payload.alert_type.value,
                "p_title": payload.title,
                "p_detail": payload.detail,
                "p_threshold": payload.threshold,
            },
            self.context,
        )
        try:
            return AlertOutput.model_validate(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    async def resolve(self, alert_id: UUID) -> AlertOutput:
        result = await self.gateway.call(
            "resolve_attendance_alert",
            {"p_alert_id": str(alert_id)},
            self.context,
        )
        try:
            return AlertOutput.model_validate(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error
