"""Adaptador das RPCs protegidas da lista de espera."""

from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from backend.app.modules.waiting_list.application.dtos import (
    WaitingListInput,
    WaitingListOutput,
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


class SupabaseWaitingListRepository:
    def __init__(self, gateway: SupabaseRPCGateway, context: RequestContext) -> None:
        self._gateway = gateway
        self._context = context

    async def join(self, payload: WaitingListInput) -> WaitingListOutput:
        result = await self._call(
            "join_waiting_list",
            {"p_student_id": str(payload.student_id), "p_class_id": str(payload.class_id)},
        )
        return self._parse(result)

    async def offer(self, entry_id: UUID) -> WaitingListOutput:
        result = await self._call(
            "offer_waiting_list_entry",
            {"p_entry_id": str(entry_id)},
        )
        return self._parse(result)

    async def accept(self, entry_id: UUID) -> WaitingListOutput:
        result = await self._call(
            "accept_waiting_list_entry",
            {"p_entry_id": str(entry_id)},
        )
        return self._parse(result)

    async def withdraw(self, entry_id: UUID) -> WaitingListOutput:
        result = await self._call(
            "withdraw_waiting_list_entry",
            {"p_entry_id": str(entry_id)},
        )
        return self._parse(result)

    async def list(self, class_id: UUID) -> tuple[WaitingListOutput, ...]:
        result = await self._call("list_waiting_list", {"p_class_id": str(class_id)})
        try:
            return tuple(TypeAdapter(list[WaitingListOutput]).validate_python(result))
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    async def _call(self, name: str, payload: dict[str, object]) -> object:
        try:
            return await self._gateway.call(name, payload, self._context)
        except SupabaseTransportError as error:
            raise PersistenceUnavailableError from error
        except SupabaseRPCError as error:
            if error.status_code == 403 or error.message_code == "waiting_list_forbidden":
                raise PermissionDeniedError from error
            if error.status_code >= 500:
                raise PersistenceUnavailableError from error
            raise PersistenceRejectedError from error

    @staticmethod
    def _parse(result: object) -> WaitingListOutput:
        try:
            return WaitingListOutput.model_validate(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error
