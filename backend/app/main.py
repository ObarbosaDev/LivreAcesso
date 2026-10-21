"""Fábrica e instância ASGI da API Livre Acesso."""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import Settings, get_settings
from backend.app.core.container import ApplicationContainer, build_container
from backend.app.modules.students.domain.exceptions import (
    DuplicateCPFError,
    StudentDomainError,
)
from backend.app.modules.students.presentation.routes import build_students_router


def create_app(
    *,
    settings: Settings | None = None,
    container: ApplicationContainer | None = None,
) -> FastAPI:
    current_settings = settings or get_settings()
    current_container = container or build_container()

    logging.basicConfig(
        level=logging.DEBUG if current_settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    application = FastAPI(
        title=current_settings.app_name,
        version=current_settings.version,
        description="API para gestão de alunos, responsáveis, turmas e frequência.",
        debug=current_settings.debug,
    )
    application.state.container = current_container

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(current_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(StudentDomainError)
    async def handle_student_domain_error(
        _request: Request,
        exception: StudentDomainError,
    ) -> JSONResponse:
        response_status = (
            status.HTTP_409_CONFLICT
            if isinstance(exception, DuplicateCPFError)
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        return JSONResponse(
            status_code=response_status,
            content={
                "error": {
                    "code": exception.code,
                    "message": str(exception),
                }
            },
        )

    @application.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "name": current_settings.app_name,
            "version": current_settings.version,
            "documentation": "/docs",
        }

    @application.get("/health", tags=["Operacional"], summary="Verificar disponibilidade")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": current_settings.app_name,
            "version": current_settings.version,
            "environment": current_settings.environment,
        }

    application.include_router(
        build_students_router(current_container),
        prefix=current_settings.api_prefix,
    )
    return application


app = create_app()
