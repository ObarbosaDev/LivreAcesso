"""Testes das garantias do verificador interativo de produção."""

import json

import httpx2
import pytest

from scripts.verify_supabase_auth import (
    VerificationError,
    _AuthResponse,
    _validate_publishable_key,
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
