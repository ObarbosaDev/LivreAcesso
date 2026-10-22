"""Dependências HTTP que extraem e verificam a identidade da requisição."""

from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.modules.identity.application.authentication import (
    AuthenticatedUser,
    AuthenticationRequiredError,
    TokenVerifier,
)
from backend.app.shared.application.request_context import RequestContext

_bearer = HTTPBearer(
    auto_error=False,
    description="Token de acesso emitido pelo Supabase Auth.",
)


async def require_authenticated_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthenticatedUser:
    """Exige Bearer válido e disponibiliza identidade mínima para a requisição."""

    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise AuthenticationRequiredError

    verifier = cast(TokenVerifier, request.app.state.token_verifier)
    user = await verifier.verify(credentials.credentials)

    # O contexto vive somente durante a requisição. O token não é colocado em
    # logs, domínio, DTO ou estado global, mas poderá autenticar a RPC Supabase.
    request.state.authenticated_user = user
    return user


async def require_request_context(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> RequestContext:
    """Combina autenticação e correlação para os casos de uso desta requisição."""

    request_id = request.state.request_id
    if not isinstance(request_id, UUID):
        # O middleware normalmente garante UUID. Falhar fechado aqui evita que
        # um contexto sem rastreabilidade alcance auditoria ou persistência.
        raise AuthenticationRequiredError
    return RequestContext(request_id=request_id, user=user)
