"""Homologa Supabase Auth, JWT, FastAPI e RPC sem persistir credenciais."""

import getpass
import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import httpx2
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.core.config import Settings
from backend.app.main import create_app

_MISSING_STUDENT_ID = "00000000-0000-4000-8000-000000000099"


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
    deployment_verified: bool
    guardians_verified: bool
    student_count: int
    profile_role: str


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


def _assert_guardian_probe(response: httpx2.Response) -> None:
    """Confirma a nova RPC por um 404 controlado, sem criar dado sintético."""

    if response.status_code != 404:
        raise VerificationError(
            f"A rota de responsáveis retornou estado inesperado ({response.status_code})."
        )
    try:
        if response.json().get("code") != "student_not_found":
            raise VerificationError("A rota de responsáveis publicou um contrato inesperado.")
    except (ValueError, AttributeError) as error:
        raise VerificationError("A rota de responsáveis retornou JSON inválido.") from error


def _verify_full_path(
    project_url: str,
    publishable_key: str,
    access_token: str,
) -> tuple[int, str]:
    """Percorre FastAPI, JWKS, perfil e RPCs usando o JWT real."""

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
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_response = client.get("/api/v1/me", headers=headers)
        response = client.get(
            "/api/v1/students?page=1&page_size=1",
            headers=headers,
        )
        guardian_response = client.get(
            f"/api/v1/students/{_MISSING_STUDENT_ID}/guardians",
            headers=headers,
        )

    if profile_response.status_code != 200:
        raise VerificationError(
            f"A API recusou o perfil autenticado ({profile_response.status_code})."
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
    _assert_guardian_probe(guardian_response)

    try:
        body = response.json()
        total = body["total"]
        profile_body = profile_response.json()
        profile_role = profile_body["role"]
        profile_active = profile_body["active"]
    except (ValueError, KeyError, TypeError) as error:
        raise VerificationError("A API retornou um contrato inesperado.") from error
    if not isinstance(total, int) or total < 0:
        raise VerificationError("A listagem retornou uma contagem inválida.")
    if not isinstance(profile_role, str) or profile_active is not True:
        raise VerificationError("O perfil autenticado não está ativo ou possui papel inválido.")
    return total, profile_role


def _verify_deployed_path(
    backend_url: str,
    access_token: str,
    *,
    http_client: httpx2.Client | None = None,
) -> None:
    """Executa smoke read-only no backend publicado sem revelar o JWT."""

    normalized_url = backend_url.strip().rstrip("/")
    parsed_url = urlparse(normalized_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise VerificationError("A URL publicada do backend precisa usar HTTPS.")

    client = http_client or httpx2.Client(timeout=10.0, follow_redirects=False)
    owns_client = http_client is None
    try:
        live = client.get(f"{normalized_url}/health/live")
        ready = client.get(f"{normalized_url}/health/ready")
        students = client.get(
            f"{normalized_url}/api/v1/students?page=1&page_size=1",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        profile = client.get(
            f"{normalized_url}/api/v1/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        guardians = client.get(
            f"{normalized_url}/api/v1/students/{_MISSING_STUDENT_ID}/guardians",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    except httpx2.HTTPError as error:
        raise VerificationError("Não foi possível alcançar o backend publicado.") from error
    finally:
        if owns_client:
            client.close()

    responses = (
        ("liveness", live),
        ("readiness", ready),
        ("listagem", students),
        ("perfil", profile),
    )
    for name, response in responses:
        if response.status_code != 200:
            raise VerificationError(f"Smoke de {name} falhou ({response.status_code}).")
        try:
            UUID(response.headers["X-Request-ID"])
        except (KeyError, ValueError) as error:
            raise VerificationError(f"Smoke de {name} não retornou request ID válido.") from error

    _assert_guardian_probe(guardians)
    try:
        UUID(guardians.headers["X-Request-ID"])
    except (KeyError, ValueError) as error:
        raise VerificationError("Smoke de responsáveis não retornou request ID válido.") from error

    try:
        if live.json().get("status") != "alive":
            raise VerificationError("Liveness publicou um contrato inesperado.")
        if ready.json().get("status") != "ready":
            raise VerificationError("Readiness publicou um contrato inesperado.")
        if not isinstance(students.json().get("total"), int):
            raise VerificationError("Listagem publicada retornou um contrato inesperado.")
        profile_body = profile.json()
        if profile_body.get("role") != "coordenador" or profile_body.get("active") is not True:
            raise VerificationError("Perfil publicado não corresponde à coordenação ativa.")
    except (ValueError, AttributeError) as error:
        raise VerificationError("O backend publicado retornou JSON inválido.") from error


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
    student_count, profile_role = _verify_full_path(project_url, publishable_key, access_token)

    backend_url = os.getenv("BACKEND_BASE_URL", "").strip()
    if not backend_url:
        backend_url = input("URL do backend publicado (Enter para pular): ").strip()
    if backend_url:
        _verify_deployed_path(backend_url, access_token)

    return VerificationResult(
        authenticated=True,
        jwt_verified=True,
        rpc_authorized=True,
        deployment_verified=bool(backend_url),
        guardians_verified=True,
        student_count=student_count,
        profile_role=profile_role,
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
    print(f"Perfil: {result.profile_role} ativo")
    print("Responsáveis: rota protegida OK")
    print("Deploy: OK" if result.deployment_verified else "Deploy: não testado")
    print(f"Alunos encontrados: {result.student_count}")
    print("Nenhuma credencial foi gravada ou exibida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
