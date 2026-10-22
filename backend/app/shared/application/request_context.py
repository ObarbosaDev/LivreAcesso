"""Contexto mínimo e efêmero compartilhado durante uma requisição."""

from dataclasses import dataclass
from uuid import UUID

from backend.app.modules.identity.application.authentication import AuthenticatedUser


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Agrupa identidade verificada e correlação sem carregar dados do aluno."""

    request_id: UUID
    user: AuthenticatedUser
