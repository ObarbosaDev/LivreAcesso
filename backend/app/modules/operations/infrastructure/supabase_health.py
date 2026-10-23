"""Sonda leve de prontidão do PostgreSQL exposto pelo Supabase."""

from typing import Any, Protocol

from backend.app.modules.operations.application.health import ReadinessResult
from backend.app.shared.application.exceptions import ServiceNotReadyError
from backend.app.shared.infrastructure.supabase_rpc import (
    SupabaseRPCError,
    SupabaseTransportError,
)


class PublicRPCGateway(Protocol):
    async def call_public(self, function_name: str, payload: dict[str, Any]) -> Any: ...


class SupabaseReadinessProbe:
    """Confirma Data API e PostgreSQL sem consultar dados pessoais."""

    def __init__(self, gateway: PublicRPCGateway) -> None:
        self._gateway = gateway

    async def check(self) -> ReadinessResult:
        try:
            response = await self._gateway.call_public("health_check", {})
        except (SupabaseRPCError, SupabaseTransportError) as error:
            # O erro externo pode conter infraestrutura ou IDs internos. A rota
            # recebe somente um estado genérico e um request ID para suporte.
            raise ServiceNotReadyError from error

        if response != {"status": "ok"}:
            raise ServiceNotReadyError
        return ReadinessResult(persistence_available=True)
