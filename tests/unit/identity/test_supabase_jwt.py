"""Testes da validação local de tokens do Supabase Auth."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx2
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from jwt.types import JWKDict

from backend.app.modules.identity.application.authentication import (
    AuthenticationUnavailableError,
    InvalidAccessTokenError,
)
from backend.app.modules.identity.infrastructure.supabase_jwt import SupabaseJWTVerifier

_PROJECT_URL = "https://project-ref.supabase.co"
_KEY_ID = "test-signing-key"


def create_signing_material() -> tuple[rsa.RSAPrivateKey, JWKDict]:
    private_key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    raw_jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    assert isinstance(raw_jwk, dict)
    jwk: JWKDict = raw_jwk | {"kid": _KEY_ID, "alg": "RS256", "use": "sig"}
    return private_key, jwk


def create_token(
    private_key: rsa.RSAPrivateKey,
    *,
    overrides: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "iss": f"{_PROJECT_URL}/auth/v1",
        "aud": "authenticated",
        "exp": now + timedelta(minutes=5),
        "iat": now,
        "sub": str(uuid4()),
        "role": "authenticated",
        "aal": "aal1",
        "is_anonymous": False,
        "session_id": str(uuid4()),
    }
    claims.update(overrides or {})
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": _KEY_ID},
    )


def create_client(jwk: JWKDict, requests: list[str]) -> httpx2.AsyncClient:
    def respond(request: httpx2.Request) -> httpx2.Response:
        requests.append(str(request.url))
        return httpx2.Response(200, json={"keys": [jwk]})

    return httpx2.AsyncClient(transport=httpx2.MockTransport(respond))


def test_valid_token_returns_minimum_authenticated_context() -> None:
    private_key, jwk = create_signing_material()
    user_id = uuid4()
    session_id = uuid4()
    token = create_token(
        private_key,
        overrides={"sub": str(user_id), "session_id": str(session_id)},
    )
    requests: list[str] = []

    async def verify() -> None:
        async with create_client(jwk, requests) as client:
            verifier = SupabaseJWTVerifier(_PROJECT_URL, http_client=client)
            user = await verifier.verify(token)

        assert user.user_id == user_id
        assert user.session_id == session_id
        assert user.assurance_level == "aal1"
        assert token not in repr(user)

    asyncio.run(verify())
    assert requests == [f"{_PROJECT_URL}/auth/v1/.well-known/jwks.json"]


def test_jwks_is_reused_while_cache_is_valid() -> None:
    private_key, jwk = create_signing_material()
    token = create_token(private_key)
    requests: list[str] = []

    async def verify_twice() -> None:
        async with create_client(jwk, requests) as client:
            verifier = SupabaseJWTVerifier(_PROJECT_URL, http_client=client)
            await verifier.verify(token)
            await verifier.verify(token)

    asyncio.run(verify_twice())
    assert len(requests) == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "anon"},
        {"role": "service_role"},
        {"is_anonymous": True},
        {"aal": "unknown"},
        {"sub": "not-a-uuid"},
    ],
)
def test_untrusted_claims_are_rejected(overrides: dict[str, Any]) -> None:
    private_key, jwk = create_signing_material()
    token = create_token(private_key, overrides=overrides)

    async def verify() -> None:
        async with create_client(jwk, []) as client:
            verifier = SupabaseJWTVerifier(_PROJECT_URL, http_client=client)
            with pytest.raises(InvalidAccessTokenError):
                await verifier.verify(token)

    asyncio.run(verify())


def test_token_signed_by_another_key_is_rejected() -> None:
    trusted_private_key, trusted_jwk = create_signing_material()
    del trusted_private_key
    untrusted_private_key = rsa.generate_private_key(public_exponent=65_537, key_size=2048)
    token = create_token(untrusted_private_key)

    async def verify() -> None:
        async with create_client(trusted_jwk, []) as client:
            verifier = SupabaseJWTVerifier(_PROJECT_URL, http_client=client)
            with pytest.raises(InvalidAccessTokenError):
                await verifier.verify(token)

    asyncio.run(verify())


def test_jwks_failure_is_reported_as_temporary_unavailability() -> None:
    def fail(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(503, json={"message": "upstream detail must stay private"})

    # Um token estruturalmente válido alcança o provedor e permite verificar
    # que a falha externa vira indisponibilidade, nunca credencial inválida.
    private_key, _jwk = create_signing_material()
    token = create_token(private_key)

    async def verify_provider_failure() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(fail)) as client:
            verifier = SupabaseJWTVerifier(_PROJECT_URL, http_client=client)
            with pytest.raises(AuthenticationUnavailableError):
                await verifier.verify(token)

    asyncio.run(verify_provider_failure())


def test_project_url_must_use_https() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        SupabaseJWTVerifier("http://project-ref.supabase.co")


def test_user_without_session_id_is_still_valid() -> None:
    private_key, jwk = create_signing_material()
    token = create_token(private_key, overrides={"session_id": None})

    async def verify() -> None:
        async with create_client(jwk, []) as client:
            user = await SupabaseJWTVerifier(_PROJECT_URL, http_client=client).verify(token)
        assert user.session_id is None
        assert isinstance(user.user_id, UUID)

    asyncio.run(verify())
