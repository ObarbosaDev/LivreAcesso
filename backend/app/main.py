"""Fábrica e instância ASGI da API Livre Acesso."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import Settings, get_settings
from backend.app.core.container import ApplicationContainer, build_container
from backend.app.modules.identity.application.authentication import (
    TokenVerifier,
    UnavailableTokenVerifier,
)
from backend.app.modules.identity.infrastructure.supabase_jwt import SupabaseJWTVerifier
from backend.app.modules.operations.presentation.routes import build_operations_router
from backend.app.modules.students.presentation.routes import build_students_router
from backend.app.shared.presentation.problem_details import (
    RequestIdMiddleware,
    install_problem_handlers,
)


def create_app(
    *,
    settings: Settings | None = None,
    container: ApplicationContainer | None = None,
    token_verifier: TokenVerifier | None = None,
) -> FastAPI:
    """Compõe adaptadores e políticas sem esconder dependências em módulos globais."""

    current_settings = settings or get_settings()
    current_container = container or build_container(current_settings)
    current_token_verifier = token_verifier or (
        SupabaseJWTVerifier(current_settings.supabase_url)
        if current_settings.supabase_url
        else UnavailableTokenVerifier()
    )

    # Logs operacionais usam estrutura mínima nesta fase. Nenhum endpoint deve
    # incluir corpo de requisição, token ou dado pessoal em mensagens de log.
    logging.basicConfig(
        level=logging.DEBUG if current_settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
        yield
        # O gateway mantém conexões entre requisições de uma instância quente.
        # O lifecycle fecha o pool quando ASGI encerra a instância ou um teste.
        await current_container.close()

    application = FastAPI(
        title=current_settings.app_name,
        version=current_settings.version,
        description="API para gestão de alunos, responsáveis, turmas e frequência.",
        debug=current_settings.debug,
        lifespan=lifespan,
    )
    application.state.container = current_container
    application.state.token_verifier = current_token_verifier

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(current_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    # O middleware é adicionado por último para envolver também respostas CORS
    # e garantir um identificador rastreável em qualquer resultado HTTP.
    application.add_middleware(RequestIdMiddleware)
    install_problem_handlers(application)

    @application.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        """Aponta para a documentação sem expor detalhes internos do runtime."""

        return {
            "name": current_settings.app_name,
            "version": current_settings.version,
            "documentation": "/docs",
        }

    application.include_router(
        build_operations_router(current_settings, current_container.readiness_probe)
    )
    application.include_router(
        build_students_router(current_container),
        prefix=current_settings.api_prefix,
    )
    return application


app = create_app()
