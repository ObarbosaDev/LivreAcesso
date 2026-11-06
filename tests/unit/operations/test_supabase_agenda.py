"""Testes do adaptador Supabase da agenda institucional."""

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from backend.app.modules.identity.application.authentication import AccessToken, AuthenticatedUser
from backend.app.modules.operations.application.agenda import AgendaEventInput
from backend.app.modules.operations.infrastructure.agenda_repository import (
    SupabaseAgendaRepository,
)
from backend.app.shared.application.request_context import RequestContext


class StubGateway:
    """Grava o payload enviado em vez de bater numa rede de verdade."""

    def __init__(self, response: Any) -> None:
        self.response = response
        self.captured_name: str | None = None
        self.captured_payload: dict[str, object] | None = None

    async def call(self, function_name: str, payload: dict[str, object], _context: object) -> Any:
        self.captured_name = function_name
        self.captured_payload = payload
        return self.response


def context() -> RequestContext:
    return RequestContext(
        request_id=UUID("00000000-0000-4000-8000-000000000001"),
        user=AuthenticatedUser(
            user_id=UUID("00000000-0000-4000-8000-000000000002"),
            access_token=AccessToken("jwt-sintetico"),
            session_id=None,
            assurance_level="aal1",
        ),
    )


def agenda_input() -> AgendaEventInput:
    return AgendaEventInput(
        title="Reunião de equipe",
        event_type="reuniao",
        starts_at=datetime(2026, 11, 10, 9, 0, tzinfo=UTC),
        ends_at=datetime(2026, 11, 10, 10, 0, tzinfo=UTC),
    )


def output_row() -> dict[str, object]:
    return {
        "id": "00000000-0000-4000-8000-000000000010",
        "title": "Reunião de equipe",
        "description": None,
        "event_type": "reuniao",
        "status": "agendado",
        "starts_at": "2026-11-10T09:00:00+00:00",
        "ends_at": "2026-11-10T10:00:00+00:00",
        "all_day": False,
        "location": None,
        "class_id": None,
        "assigned_to": None,
        "created_by": "00000000-0000-4000-8000-000000000002",
        "created_at": "2026-11-10T08:00:00+00:00",
        "updated_at": "2026-11-10T08:00:00+00:00",
    }


def test_create_sends_rpc_parameter_names_with_p_prefix() -> None:
    gateway = StubGateway(output_row())
    repository = SupabaseAgendaRepository(gateway)  # type: ignore[arg-type]

    asyncio.run(repository.create(agenda_input(), context()))

    assert gateway.captured_name == "create_agenda_event"
    assert gateway.captured_payload is not None
    assert gateway.captured_payload["p_title"] == "Reunião de equipe"
    assert gateway.captured_payload["p_event_type"] == "reuniao"
    assert gateway.captured_payload["p_starts_at"] == "2026-11-10T09:00:00Z"
    assert gateway.captured_payload["p_request_id"] == str(context().request_id)
    # Nenhuma chave sem o prefixo p_ pode sobrar: o PostgREST rejeita parâmetro
    # que não bate com a assinatura de nenhuma função.
    assert all(key.startswith("p_") for key in gateway.captured_payload)


def test_update_sends_rpc_parameter_names_with_p_prefix() -> None:
    gateway = StubGateway(output_row())
    repository = SupabaseAgendaRepository(gateway)  # type: ignore[arg-type]
    event_id = UUID("00000000-0000-4000-8000-000000000010")
    expected_updated_at = datetime(2026, 11, 10, 8, 0, tzinfo=UTC)

    asyncio.run(repository.update(event_id, expected_updated_at, agenda_input(), context()))

    assert gateway.captured_name == "update_agenda_event"
    assert gateway.captured_payload is not None
    assert gateway.captured_payload["p_event_id"] == str(event_id)
    assert gateway.captured_payload["p_expected_updated_at"] == "2026-11-10T08:00:00+00:00"
    assert gateway.captured_payload["p_title"] == "Reunião de equipe"
    assert all(key.startswith("p_") for key in gateway.captured_payload)
