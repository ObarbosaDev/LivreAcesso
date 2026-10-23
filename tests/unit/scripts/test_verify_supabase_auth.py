"""Testes das garantias do verificador interativo de produção."""

import json
from uuid import uuid4

import httpx2
import pytest

from scripts.verify_supabase_auth import (
    VerificationError,
    _AuthResponse,
    _validate_publishable_key,
    _verify_deployed_path,
)


def test_auth_response_hides_access_token_from_repr() -> None:
    token = "token-sintetico-com-tamanho-valido"
    response = _AuthResponse(access_token=token)

    assert token not in repr(response)


def test_auth_response_rejects_short_token() -> None:
    with pytest.raises(ValueError):
        _AuthResponse(access_token="short")


def test_serialized_payload_fixture_contains_no_real_credentials() -> None:
    fixture = json.dumps(
        {
            "email": "coordenacao@livreacesso.test",
            "password": "senha-sintetica",
        }
    )

    assert "supabase.co" not in fixture
    assert "sb_secret_" not in fixture


def test_verification_error_never_requires_http_response_body() -> None:
    request = httpx2.Request("POST", "https://example.test/auth/v1/token")
    error = httpx2.ConnectError("detalhe externo", request=request)
    sanitized = VerificationError("Não foi possível alcançar o Supabase Auth.")

    assert str(error) not in str(sanitized)


def test_verifier_rejects_non_publishable_key_before_network() -> None:
    with pytest.raises(VerificationError, match="Publishable key"):
        _validate_publishable_key("https://example.supabase.co", "wrong-key-type")


def test_deployed_smoke_checks_live_ready_and_authenticated_list() -> None:
    paths: list[str] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        paths.append(request.url.path)
        headers = {"X-Request-ID": str(uuid4())}
        if request.url.path == "/health/live":
            return httpx2.Response(200, headers=headers, json={"status": "alive"})
        if request.url.path == "/health/ready":
            return httpx2.Response(200, headers=headers, json={"status": "ready"})
        assert request.headers["Authorization"] == "Bearer token-sintetico"
        if request.url.path == "/api/v1/me":
            return httpx2.Response(
                200,
                headers=headers,
                json={"role": "coordenador", "active": True},
            )
        return httpx2.Response(200, headers=headers, json={"total": 0})

    with httpx2.Client(transport=httpx2.MockTransport(respond)) as client:
        _verify_deployed_path(
            "https://api.example.test",
            "token-sintetico",
            http_client=client,
        )

    assert paths == [
        "/health/live",
        "/health/ready",
        "/api/v1/students",
        "/api/v1/me",
    ]


def test_deployed_smoke_requires_https() -> None:
    with pytest.raises(VerificationError, match="HTTPS"):
        _verify_deployed_path("http://api.example.test", "token-sintetico")


def test_deployed_smoke_rejects_missing_request_id() -> None:
    def respond(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"status": "alive", "total": 0})

    with (
        httpx2.Client(transport=httpx2.MockTransport(respond)) as client,
        pytest.raises(VerificationError, match="request ID"),
    ):
        _verify_deployed_path(
            "https://api.example.test",
            "token-sintetico",
            http_client=client,
        )
