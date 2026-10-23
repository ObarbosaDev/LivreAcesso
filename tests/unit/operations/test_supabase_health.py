"""Testes da sonda de prontidão do Supabase."""

import asyncio
from typing import Any

import pytest

from backend.app.modules.operations.infrastructure.supabase_health import (
    SupabaseReadinessProbe,
)
from backend.app.shared.application.exceptions import ServiceNotReadyError
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCError, SupabaseTransportError


class StubGateway:
    """Double mínimo que nunca carrega configuração ou credencial real."""

    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_public(self, function_name: str, payload: dict[str, Any]) -> Any:
        self.calls.append((function_name, payload))
        if self.error is not None:
            raise self.error
        return self.response


def test_ready_when_health_rpc_returns_exact_contract() -> None:
    gateway = StubGateway(response={"status": "ok"})
    probe = SupabaseReadinessProbe(gateway)

    result = asyncio.run(probe.check())

    assert result.persistence_available is True
    assert gateway.calls == [("health_check", {})]


@pytest.mark.parametrize(
    "response",
    [None, {}, {"status": "degraded"}, {"status": "ok", "internal": "detail"}],
)
def test_unexpected_health_contract_fails_closed(response: object) -> None:
    probe = SupabaseReadinessProbe(StubGateway(response=response))

    with pytest.raises(ServiceNotReadyError):
        asyncio.run(probe.check())


@pytest.mark.parametrize(
    "error",
    [
        SupabaseTransportError(),
        SupabaseRPCError(status_code=503, database_code=None, message_code=None),
    ],
)
def test_external_failure_becomes_sanitized_not_ready(error: Exception) -> None:
    probe = SupabaseReadinessProbe(StubGateway(error=error))

    with pytest.raises(ServiceNotReadyError) as captured:
        asyncio.run(probe.check())

    assert "Supabase" not in str(captured.value)
