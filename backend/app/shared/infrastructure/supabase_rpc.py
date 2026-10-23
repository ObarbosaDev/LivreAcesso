"""Cliente HTTP mínimo para funções RPC do PostgREST/Supabase."""

import re
from typing import Any
from urllib.parse import urlparse

import httpx2

from backend.app.modules.identity.application.authentication import AccessToken
from backend.app.shared.application.request_context import RequestContext

_FUNCTION_NAME = re.compile(r"^[a-z][a-z0-9_]{1,99}$")
_SAFE_ERROR_CODE = re.compile(r"^[A-Za-z0-9_]{1,80}$")
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class SupabaseRPCError(Exception):
    """Falha sanitizada; nunca guarda corpo da resposta, token ou chave."""

    def __init__(
        self,
        *,
        status_code: int,
        database_code: str | None,
        message_code: str | None,
    ) -> None:
        super().__init__("A função Supabase não pôde ser concluída.")
        self.status_code = status_code
        self.database_code = database_code
        self.message_code = message_code


class SupabaseTransportError(Exception):
    """Indica indisponibilidade de rede sem propagar detalhes do cliente HTTP."""


class SupabaseRPCGateway:
    """Executa somente RPCs explícitas, autenticadas ou públicas e sem logs de payload."""

    def __init__(
        self,
        project_url: str,
        publishable_key: str,
        *,
        http_client: httpx2.AsyncClient | None = None,
    ) -> None:
        normalized_url = project_url.strip().rstrip("/")
        parsed_url = urlparse(normalized_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError("SUPABASE_URL deve ser uma URL HTTPS válida.")
        if not publishable_key or len(publishable_key) > 4096:
            raise ValueError("SUPABASE_PUBLISHABLE_KEY é inválida.")

        self._rpc_base_url = f"{normalized_url}/rest/v1/rpc"
        # A chave publicável identifica o projeto, mas não concede acesso sozinha.
        # Mantemos repr implícito sem campos e nunca a incluímos em exceções/logs.
        self._publishable_key = publishable_key
        self._http_client = http_client or httpx2.AsyncClient(
            timeout=10.0,
            follow_redirects=False,
            limits=httpx2.Limits(max_connections=20, max_keepalive_connections=10),
        )
        self._owns_http_client = http_client is None

    async def call(
        self,
        function_name: str,
        payload: dict[str, Any],
        context: RequestContext,
    ) -> Any:
        """Chama uma RPC protegida usando o JWT efêmero da requisição."""

        access_token: AccessToken = context.user.access_token
        headers = self._base_headers()
        headers.update(
            {
                "Authorization": f"Bearer {access_token.reveal_for_authorization()}",
                "X-Request-ID": str(context.request_id),
            }
        )
        return await self._post(function_name, payload, headers)

    async def call_public(self, function_name: str, payload: dict[str, Any]) -> Any:
        """Chama RPC explicitamente pública sem inventar identidade de usuário."""

        # Atualmente este caminho existe somente para health_check. Funções de
        # negócio continuam exigindo RequestContext e falham pela permissão SQL.
        return await self._post(function_name, payload, self._base_headers())

    def _base_headers(self) -> dict[str, str]:
        return {
            "apikey": self._publishable_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Profile": "public",
            "Content-Profile": "public",
        }

    async def _post(
        self,
        function_name: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> Any:
        if _FUNCTION_NAME.fullmatch(function_name) is None:
            raise ValueError("Nome de função Supabase inválido.")

        try:
            response = await self._http_client.post(
                f"{self._rpc_base_url}/{function_name}",
                headers=headers,
                json=payload,
            )
        except httpx2.HTTPError as error:
            # A exceção original pode conter URL ou cabeçalhos de diagnóstico.
            # Ela fica encadeada em memória, mas nunca é registrada pelo handler.
            raise SupabaseTransportError from error

        if not 200 <= response.status_code < 300:
            raise self._safe_rpc_error(response)
        if len(response.content) > _MAX_RESPONSE_BYTES:
            raise SupabaseTransportError
        if not response.content:
            return None

        try:
            return response.json()
        except ValueError as error:
            raise SupabaseTransportError from error

    async def close(self) -> None:
        """Libera conexões somente quando o próprio gateway criou o cliente."""

        if self._owns_http_client:
            await self._http_client.aclose()

    @staticmethod
    def _safe_rpc_error(response: httpx2.Response) -> SupabaseRPCError:
        database_code: str | None = None
        message_code: str | None = None

        # Limitamos antes de decodificar para não manter respostas externas
        # inesperadamente grandes em memória durante uma falha.
        if len(response.content) <= _MAX_RESPONSE_BYTES:
            try:
                body = response.json()
            except ValueError:
                body = None
            if isinstance(body, dict):
                database_code = _safe_code(body.get("code"))
                message_code = _safe_code(body.get("message"))

        return SupabaseRPCError(
            status_code=response.status_code,
            database_code=database_code,
            message_code=message_code,
        )


def _safe_code(value: object) -> str | None:
    if not isinstance(value, str) or _SAFE_ERROR_CODE.fullmatch(value) is None:
        return None
    return value
