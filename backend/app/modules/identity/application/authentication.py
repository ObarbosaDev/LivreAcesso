"""Contratos e tipos seguros usados na autenticação."""

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID


class AuthenticationError(Exception):
    """Falha esperada de autenticação que pode ser traduzida para HTTP."""

    code = "authentication_error"


class AuthenticationRequiredError(AuthenticationError):
    code = "authentication_required"

    def __init__(self) -> None:
        super().__init__("Envie um token de acesso válido para continuar.")


class InvalidAccessTokenError(AuthenticationError):
    code = "invalid_access_token"

    def __init__(self) -> None:
        super().__init__("A sessão é inválida ou expirou. Entre novamente.")


class AuthenticationUnavailableError(AuthenticationError):
    code = "authentication_unavailable"

    def __init__(self) -> None:
        super().__init__("A autenticação está temporariamente indisponível.")


@dataclass(frozen=True, slots=True)
class AccessToken:
    """Segredo efêmero cujo valor não aparece em repr, str ou logs acidentais."""

    _value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self._value or len(self._value) > 16_384:
            raise InvalidAccessTokenError

    def reveal_for_authorization(self) -> str:
        """Revela o token somente no ponto que monta o cabeçalho autorizado."""

        return self._value

    def __str__(self) -> str:
        return "**********"


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Identidade verificada transportada durante uma única requisição."""

    user_id: UUID
    access_token: AccessToken
    session_id: UUID | None
    assurance_level: str


class TokenVerifier(Protocol):
    async def verify(self, raw_access_token: str) -> AuthenticatedUser: ...


class UnavailableTokenVerifier:
    """Bloqueia rotas protegidas quando Supabase ainda não foi configurado."""

    async def verify(self, raw_access_token: str) -> AuthenticatedUser:
        # O token recebido não é inspecionado nem armazenado quando o provedor
        # não está configurado; falhar fechado evita um modo anônimo acidental.
        del raw_access_token
        raise AuthenticationUnavailableError
