"""Validação local dos JWTs assimétricos emitidos pelo Supabase Auth."""

import asyncio
from collections.abc import Mapping
from time import monotonic
from typing import Any, cast
from urllib.parse import urlparse
from uuid import UUID

import httpx2
import jwt
from jwt.types import JWKDict

from backend.app.modules.identity.application.authentication import (
    AccessToken,
    AuthenticatedUser,
    AuthenticationUnavailableError,
    InvalidAccessTokenError,
)

_ALLOWED_ALGORITHMS = frozenset({"ES256", "RS256"})
_MAX_JWKS_BYTES = 64 * 1024


class SupabaseJWTVerifier:
    """Verifica assinatura e claims usando chaves públicas cacheadas do projeto."""

    def __init__(
        self,
        project_url: str,
        *,
        http_client: httpx2.AsyncClient | None = None,
        cache_ttl_seconds: int = 600,
    ) -> None:
        normalized_url = project_url.strip().rstrip("/")
        parsed_url = urlparse(normalized_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError("SUPABASE_URL deve ser uma URL HTTPS válida.")
        if cache_ttl_seconds < 60:
            raise ValueError("O cache de JWKS deve durar pelo menos 60 segundos.")

        self._issuer = f"{normalized_url}/auth/v1"
        self._jwks_url = f"{self._issuer}/.well-known/jwks.json"
        self._http_client = http_client
        self._cache_ttl_seconds = cache_ttl_seconds
        self._keys_by_id: dict[str, JWKDict] = {}
        self._cache_expires_at = 0.0
        self._refresh_lock = asyncio.Lock()

    async def verify(self, raw_access_token: str) -> AuthenticatedUser:
        """Valida o token por completo antes de confiar em qualquer claim."""

        if not raw_access_token or len(raw_access_token) > 16_384:
            raise InvalidAccessTokenError

        try:
            header = jwt.get_unverified_header(raw_access_token)
        except jwt.PyJWTError as error:
            raise InvalidAccessTokenError from error

        algorithm = header.get("alg")
        key_id = header.get("kid")
        if algorithm not in _ALLOWED_ALGORITHMS or not isinstance(key_id, str) or not key_id:
            # A lista explícita impede ataques de troca de algoritmo e recusa os
            # tokens simétricos que exigiriam manter o segredo JWT no backend.
            raise InvalidAccessTokenError

        signing_key = await self._signing_key(key_id, cast(str, algorithm))

        try:
            claims = jwt.decode(
                raw_access_token,
                key=signing_key,
                algorithms=[cast(str, algorithm)],
                audience="authenticated",
                issuer=self._issuer,
                options={
                    "require": [
                        "iss",
                        "aud",
                        "exp",
                        "iat",
                        "sub",
                        "role",
                        "aal",
                        "is_anonymous",
                    ]
                },
            )
        except jwt.PyJWTError as error:
            # A causa é encadeada apenas em memória; nenhum handler devolve ou
            # registra a mensagem interna, que poderia conter parte do token.
            raise InvalidAccessTokenError from error

        if claims.get("role") != "authenticated" or claims.get("is_anonymous") is not False:
            # Contas anônimas e tokens administrativos não representam pessoas
            # operacionais autorizadas a acessar os cadastros do instituto.
            raise InvalidAccessTokenError

        user_id = self._read_uuid_claim(claims, "sub", required=True)
        if user_id is None:
            # A guarda explicita a invariável para o type checker e protege o
            # construtor caso a leitura de claims seja alterada no futuro.
            raise InvalidAccessTokenError
        session_id = self._read_uuid_claim(claims, "session_id", required=False)
        assurance_level = claims.get("aal")
        if assurance_level not in {"aal1", "aal2"}:
            raise InvalidAccessTokenError

        return AuthenticatedUser(
            user_id=user_id,
            access_token=AccessToken(raw_access_token),
            session_id=session_id,
            assurance_level=cast(str, assurance_level),
        )

    async def _signing_key(self, key_id: str, algorithm: str) -> jwt.PyJWK:
        await self._refresh_keys(force=False)
        raw_key = self._keys_by_id.get(key_id)

        if raw_key is None:
            # Uma rotação pode apresentar um kid novo antes do TTL terminar.
            # Recarregamos uma vez; continuar sem chave significa token inválido.
            await self._refresh_keys(force=True)
            raw_key = self._keys_by_id.get(key_id)
        if raw_key is None:
            raise InvalidAccessTokenError

        declared_algorithm = raw_key.get("alg")
        if declared_algorithm is not None and declared_algorithm != algorithm:
            raise InvalidAccessTokenError

        try:
            return jwt.PyJWK.from_dict(raw_key, algorithm=algorithm)
        except (jwt.PyJWTError, ValueError, TypeError) as error:
            raise InvalidAccessTokenError from error

    async def _refresh_keys(self, *, force: bool) -> None:
        if not force and self._keys_by_id and monotonic() < self._cache_expires_at:
            return

        async with self._refresh_lock:
            if not force and self._keys_by_id and monotonic() < self._cache_expires_at:
                return

            payload = await self._download_jwks()
            raw_keys = payload.get("keys")
            if not isinstance(raw_keys, list):
                raise AuthenticationUnavailableError

            parsed_keys: dict[str, JWKDict] = {}
            for candidate in raw_keys:
                if not isinstance(candidate, Mapping):
                    continue
                key = dict(candidate)
                key_id = key.get("kid")
                algorithm = key.get("alg")
                if (
                    isinstance(key_id, str)
                    and key_id
                    and (algorithm is None or algorithm in _ALLOWED_ALGORITHMS)
                ):
                    parsed_keys[key_id] = cast(JWKDict, key)

            if not parsed_keys:
                raise AuthenticationUnavailableError

            self._keys_by_id = parsed_keys
            self._cache_expires_at = monotonic() + self._cache_ttl_seconds

    async def _download_jwks(self) -> dict[str, Any]:
        try:
            if self._http_client is not None:
                response = await self._http_client.get(
                    self._jwks_url,
                    headers={"Accept": "application/json"},
                )
            else:
                # O cliente existe somente durante a atualização das chaves.
                # Como o resultado fica em cache, isso evita manter recursos de
                # rede globais sem lifecycle confiável em funções serverless.
                async with httpx2.AsyncClient(
                    timeout=5.0,
                    follow_redirects=False,
                ) as client:
                    response = await client.get(
                        self._jwks_url,
                        headers={"Accept": "application/json"},
                    )
        except httpx2.HTTPError as error:
            raise AuthenticationUnavailableError from error

        if response.status_code != 200 or len(response.content) > _MAX_JWKS_BYTES:
            raise AuthenticationUnavailableError

        try:
            payload = response.json()
        except ValueError as error:
            raise AuthenticationUnavailableError from error
        if not isinstance(payload, dict):
            raise AuthenticationUnavailableError
        return cast(dict[str, Any], payload)

    @staticmethod
    def _read_uuid_claim(
        claims: Mapping[str, Any],
        name: str,
        *,
        required: bool,
    ) -> UUID | None:
        value = claims.get(name)
        if value is None and not required:
            return None
        if not isinstance(value, str):
            raise InvalidAccessTokenError
        try:
            return UUID(value)
        except ValueError as error:
            raise InvalidAccessTokenError from error
