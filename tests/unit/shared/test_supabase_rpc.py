"""Testes do gateway HTTP mínimo usado nas RPCs Supabase."""

import asyncio
import json
from uuid import UUID

import httpx2
import pytest

from backend.app.modules.identity.application.authentication import AccessToken, AuthenticatedUser
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import (
    SupabaseRPCError,
    SupabaseRPCGateway,
    SupabaseTransportError,
)

_PROJECT_URL = "https://project-ref.supabase.co"
_PUBLISHABLE_KEY = "sb_publishable_test"
_ACCESS_TOKEN = "jwt-sintetico-de-teste"
_REQUEST_ID = UUID("00000000-0000-4000-8000-000000000001")


def request_context() -> RequestContext:
    return RequestContext(
        request_id=_REQUEST_ID,
        user=AuthenticatedUser(
            user_id=UUID("00000000-0000-4000-8000-000000000002"),
            access_token=AccessToken(_ACCESS_TOKEN),
            session_id=UUID("00000000-0000-4000-8000-000000000003"),
            assurance_level="aal1",
        ),
    )


def test_call_sends_project_key_user_jwt_and_request_id() -> None:
    captured: dict[str, object] = {}

    def respond(request: httpx2.Request) -> httpx2.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["apikey"] = request.headers["apikey"]
        captured["request_id"] = request.headers["X-Request-ID"]
        captured["payload"] = json.loads(request.content)
        return httpx2.Response(200, json={"result": "ok"})

    async def call() -> object:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(
                _PROJECT_URL,
                _PUBLISHABLE_KEY,
                http_client=client,
            )
            return await gateway.call("safe_function", {"value": 1}, request_context())

    result = asyncio.run(call())

    assert result == {"result": "ok"}
    assert captured == {
        "url": f"{_PROJECT_URL}/rest/v1/rpc/safe_function",
        "authorization": f"Bearer {_ACCESS_TOKEN}",
        "apikey": _PUBLISHABLE_KEY,
        "request_id": str(_REQUEST_ID),
        "payload": {"value": 1},
    }


def test_rpc_error_keeps_only_allowlisted_codes() -> None:
    sensitive_text = "CPF 52998224725 não pode aparecer"

    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            403,
            json={
                "code": "42501",
                "message": "forbidden",
                "details": sensitive_text,
            },
        )

    async def call() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(
                _PROJECT_URL,
                _PUBLISHABLE_KEY,
                http_client=client,
            )
            with pytest.raises(SupabaseRPCError) as captured:
                await gateway.call("safe_function", {}, request_context())

        error = captured.value
        assert error.status_code == 403
        assert error.database_code == "42501"
        assert error.message_code == "forbidden"
        assert sensitive_text not in repr(error)

    asyncio.run(call())


def test_unsafe_error_message_is_discarded() -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(400, json={"message": "contains personal data"})

    async def call() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(
                _PROJECT_URL,
                _PUBLISHABLE_KEY,
                http_client=client,
            )
            with pytest.raises(SupabaseRPCError) as captured:
                await gateway.call("safe_function", {}, request_context())
        assert captured.value.message_code is None

    asyncio.run(call())


def test_network_failure_becomes_sanitized_transport_error() -> None:
    def fail(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("internal transport detail", request=request)

    async def call() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(fail)) as client:
            gateway = SupabaseRPCGateway(
                _PROJECT_URL,
                _PUBLISHABLE_KEY,
                http_client=client,
            )
            with pytest.raises(SupabaseTransportError) as captured:
                await gateway.call("safe_function", {}, request_context())
        assert "internal transport detail" not in str(captured.value)

    asyncio.run(call())


@pytest.mark.parametrize("function_name", ["", "UPPERCASE", "../table", "x" * 101])
def test_function_name_cannot_change_the_rpc_path(function_name: str) -> None:
    gateway = SupabaseRPCGateway(
        _PROJECT_URL,
        _PUBLISHABLE_KEY,
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(lambda _: None)),
    )

    with pytest.raises(ValueError, match="função Supabase"):
        asyncio.run(gateway.call(function_name, {}, request_context()))

    asyncio.run(gateway._http_client.aclose())


def test_response_size_is_limited() -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=b"x" * (2 * 1024 * 1024 + 1))

    async def call() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as client:
            gateway = SupabaseRPCGateway(
                _PROJECT_URL,
                _PUBLISHABLE_KEY,
                http_client=client,
            )
            with pytest.raises(SupabaseTransportError):
                await gateway.call("safe_function", {}, request_context())

    asyncio.run(call())
