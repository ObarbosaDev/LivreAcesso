"""Testes dos tipos seguros do contexto de autenticação."""

import asyncio

import pytest

from backend.app.modules.identity.application.authentication import (
    AccessToken,
    AuthenticationUnavailableError,
    InvalidAccessTokenError,
    UnavailableTokenVerifier,
)


def test_access_token_never_appears_in_text_or_repr() -> None:
    raw_token = "segredo-que-nao-pode-vazar"
    token = AccessToken(raw_token)

    assert raw_token not in str(token)
    assert raw_token not in repr(token)
    assert token.reveal_for_authorization() == raw_token


@pytest.mark.parametrize("raw_token", ["", "x" * 16_385])
def test_access_token_rejects_invalid_size(raw_token: str) -> None:
    with pytest.raises(InvalidAccessTokenError):
        AccessToken(raw_token)


def test_unavailable_verifier_fails_closed() -> None:
    verifier = UnavailableTokenVerifier()

    with pytest.raises(AuthenticationUnavailableError):
        asyncio.run(verifier.verify("token-ignorado"))
