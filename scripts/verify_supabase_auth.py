"""Homologa Supabase Auth, JWT, FastAPI e RPC sem persistir credenciais."""

import getpass
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx2
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.core.config import Settings
from backend.app.main import create_app


class VerificationError(Exception):
    """Erro sanitizado que não carrega resposta externa nem credencial."""


def _validate_publishable_key(project_url: str, publishable_key: str) -> None:
    """Confirma a chave do projeto antes de solicitar a senha da conta."""

    if not publishable_key.startswith("sb_publishable_"):
        raise VerificationError(
            "Use a Publishable key iniciada por 'sb_publishable_', não Secret/JWT key."
        )

    try:
        with httpx2.Client(timeout=10.0, follow_redirects=False) as client:
            response = client.get(
                f"{project_url}/auth/v1/settings",
                headers={"apikey": publishable_key},
            )
    except httpx2.HTTPError as error:
        raise VerificationError("Não foi possível validar a chave publicável.") from error

    if response.status_code in {401, 403}:
        raise VerificationError(
            "Chave publicável recusada. Copie novamente em Project Settings → API Keys."
        )
    if response.status_code != 200:
        raise VerificationError(
            f"Não foi possível validar a chave publicável ({response.status_code})."
        )


class _AuthResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    access_token: str = Field(min_length=20, max_length=16_384, repr=False)


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Resultado seguro que contém apenas estado e quantidade de registros."""

    authenticated: bool
    jwt_verified: bool
    rpc_authorized: bool
    student_count: int


def _prompt_value(environment_name: str, label: str, *, secret: bool = False) -> str:
    value = os.getenv(environment_name, "").strip()
    if not value:
        value = getpass.getpass(f"{label}: ") if secret else input(f"{label}: ").strip()
    if not value:
        raise VerificationError(f"{label} não foi informado.")
    return value


def _authenticate(
    project_url: str,
    publishable_key: str,
    email: str,
    password: str,
) -> str:
    """Troca credenciais sintéticas por JWT sem registrar nenhum dos valores."""

    try:
        with httpx2.Client(timeout=10.0, follow_redirects=False) as client:
            response = client.post(
                f"{project_url}/auth/v1/token?grant_type=password",
                headers={
                    "apikey": publishable_key,
                    "Content-Type": "application/json",
                },
                json={"email": email, "password": password},
            )
    except httpx2.HTTPError as error:
        raise VerificationError("Não foi possível alcançar o Supabase Auth.") from error

    if response.status_code in {400, 401}:
        raise VerificationError("E-mail ou senha da conta sintética não conferem.")
    if response.status_code != 200 or len(response.content) > 256 * 1024:
        # O corpo do Auth pode trazer detalhes sobre a conta. Exibimos somente
        # o status para evitar enumeração e vazamento no terminal compartilhado.
        raise VerificationError(f"Supabase Auth recusou a autenticação ({response.status_code}).")

    try:
        return _AuthResponse.model_validate(response.json()).access_token
    except (ValueError, ValidationError) as error:
        raise VerificationError("Supabase Auth retornou um contrato inesperado.") from error


def _verify_full_path(project_url: str, publishable_key: str, access_token: str) -> int:
    """Percorre FastAPI, verificação JWKS e listagem RPC usando o JWT real."""

    settings = Settings(
        app_name="Livre Acesso Production Verification",
        version="verification",
        environment="test",
        host="127.0.0.1",
        port=8000,
        debug=False,
        api_prefix="/api/v1",
        cors_origins=(),
        supabase_url=project_url,
        supabase_publishable_key=publishable_key,
    )

    with TestClient(create_app(settings=settings)) as client:
        response = client.get(
            "/api/v1/students?page=1&page_size=1",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if response.status_code != 200:
        error_code = "unknown_error"
        try:
            payload: Any = response.json()
            if isinstance(payload, dict) and isinstance(payload.get("code"), str):
                error_code = payload["code"]
        except ValueError:
            pass
        raise VerificationError(
            f"A API recusou o fluxo autenticado ({response.status_code}, {error_code})."
        )

    try:
        body = response.json()
        total = body["total"]
    except (ValueError, KeyError, TypeError) as error:
        raise VerificationError("A listagem retornou um contrato inesperado.") from error
    if not isinstance(total, int) or total < 0:
        raise VerificationError("A listagem retornou uma contagem inválida.")
    return total


def verify() -> VerificationResult:
    project_url = _prompt_value("SUPABASE_URL", "URL do projeto").rstrip("/")
    publishable_key = _prompt_value(
        "SUPABASE_PUBLISHABLE_KEY",
        "Chave publicável",
        secret=True,
    )
    _validate_publishable_key(project_url, publishable_key)
    email = _prompt_value("SUPABASE_TEST_EMAIL", "E-mail da conta sintética")
    # Senha sempre vem do prompt oculto; não aceitamos variável para reduzir a
    # chance de ela permanecer no ambiente de outro processo ou captura de CI.
    password = getpass.getpass("Senha da conta sintética: ")
    if not password:
        raise VerificationError("Senha da conta sintética não foi informada.")

    access_token = _authenticate(project_url, publishable_key, email, password)
    student_count = _verify_full_path(project_url, publishable_key, access_token)
    return VerificationResult(
        authenticated=True,
        jwt_verified=True,
        rpc_authorized=True,
        student_count=student_count,
    )


def main() -> int:
    # O cliente HTTP pode registrar URL/status em INFO. A homologação exibe
    # apenas seu resumo sanitizado, evitando ruído em terminais compartilhados.
    logging.getLogger("httpx2").setLevel(logging.WARNING)
    print("Homologando Supabase sem armazenar credenciais...")
    try:
        result = verify()
    except VerificationError as error:
        print(f"FALHA: {error}")
        return 1

    print("Auth: OK")
    print("JWT/JWKS: OK")
    print("FastAPI → RPC: OK")
    print(f"Alunos encontrados: {result.student_count}")
    print("Nenhuma credencial foi gravada ou exibida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
