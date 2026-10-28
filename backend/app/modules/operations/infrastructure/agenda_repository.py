"""Adaptador remoto da agenda por RPCs Supabase."""

from datetime import datetime
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from backend.app.modules.operations.application.agenda import (
    AgendaEventInput,
    AgendaEventOutput,
    AgendaRepository,
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


class SupabaseAgendaRepository(AgendaRepository):
    def __init__(self, gateway: SupabaseRPCGateway) -> None:
        self.gateway = gateway

    async def list(
        self,
        starts_at: datetime,
        ends_at: datetime,
        event_type: str | None,
        assigned_to: UUID | None,
        context: RequestContext,
    ) -> list[AgendaEventOutput]:
        result = await self._call(
            "list_agenda_events",
            {
                "p_starts_at": starts_at.isoformat(),
                "p_ends_at": ends_at.isoformat(),
                "p_event_type": event_type,
                "p_assigned_to": str(assigned_to) if assigned_to else None,
            },
            context,
        )
        try:
            return TypeAdapter(list[AgendaEventOutput]).validate_python(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    async def create(self, payload: AgendaEventInput, context: RequestContext) -> AgendaEventOutput:
        body = payload.model_dump(mode="json")
        body.update({"p_request_id": str(context.request_id)})
        result = await self._call("create_agenda_event", body, context)
        try:
            return AgendaEventOutput.model_validate(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    async def _call(self, name: str, payload: dict[str, object], context: RequestContext) -> object:
        try:
            return await self.gateway.call(name, payload, context)
        except SupabaseTransportError as error:
            raise PersistenceUnavailableError from error
        except SupabaseRPCError as error:
            if error.status_code == 403 or error.message_code == "forbidden":
                raise PermissionDeniedError from error
            if error.status_code >= 500:
                raise PersistenceUnavailableError from error
            raise PersistenceRejectedError from error
