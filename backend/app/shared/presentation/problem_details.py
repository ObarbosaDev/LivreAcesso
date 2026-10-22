"""Respostas de erro previsíveis, seguras e compreensíveis para clientes da API."""

import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from backend.app.modules.identity.application.authentication import (
    AuthenticationError,
    AuthenticationUnavailableError,
)
from backend.app.modules.students.domain.exceptions import (
    DuplicateCPFError,
    InvalidCPFError,
    InvalidPhoneError,
    StudentDomainError,
)
from backend.app.shared.application.exceptions import (
    ApplicationError,
    PermissionDeniedError,
    PersistenceRejectedError,
    PersistenceUnavailableError,
)

logger = logging.getLogger("livre_acesso.api")


class FieldProblem(BaseModel):
    """Erro associado a um campo para que a interface direcione o foco corretamente."""

    model_config = ConfigDict(frozen=True)

    field: str = Field(description="Caminho estável do campo que precisa de correção.")
    code: str = Field(description="Código estável, independente da mensagem traduzida.")
    message: str = Field(description="Orientação curta e compreensível para a pessoa usuária.")


class ProblemDetail(BaseModel):
    """Contrato inspirado em Problem Details, acrescido de código e erros por campo."""

    model_config = ConfigDict(frozen=True)

    type: str
    title: str
    status: int
    detail: str
    code: str
    request_id: UUID
    errors: list[FieldProblem] = Field(default_factory=list)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Atribui um UUID rastreável sem aceitar texto arbitrário vindo do cliente."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = _read_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = str(request_id)
        return response


def _read_request_id(raw_request_id: str | None) -> UUID:
    if raw_request_id is None:
        return uuid4()

    try:
        # Somente UUID é ecoado. Essa validação evita injeção de texto livre em
        # cabeçalhos e logs quando o identificador vem de um sistema externo.
        return UUID(raw_request_id)
    except ValueError:
        return uuid4()


def _request_id(request: Request) -> UUID:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, UUID) else uuid4()


def _problem_response(
    request: Request,
    *,
    response_status: int,
    title: str,
    detail: str,
    code: str,
    errors: list[FieldProblem] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    problem = ProblemDetail(
        type=f"urn:livre-acesso:problem:{code.replace('_', '-')}",
        title=title,
        status=response_status,
        detail=detail,
        code=code,
        request_id=_request_id(request),
        errors=errors or [],
    )
    return JSONResponse(
        status_code=response_status,
        content=problem.model_dump(mode="json"),
        media_type="application/problem+json",
        headers=headers,
    )


def _field_path(error: dict[str, Any]) -> str:
    location = error.get("loc", ())
    protocol_markers = {"body", "path", "query", "header"}
    parts = [str(part) for part in location if str(part) not in protocol_markers]
    return ".".join(parts) or "request"


def _validation_problem(error: dict[str, Any]) -> FieldProblem:
    error_type = str(error.get("type", "invalid_value"))
    field = _field_path(error)

    if error_type == "missing":
        return FieldProblem(field=field, code="required", message="Este campo é obrigatório.")
    if error_type == "extra_forbidden":
        return FieldProblem(
            field=field,
            code="field_not_allowed",
            message="Este campo não é aceito nesta operação.",
        )
    if "date" in error_type:
        return FieldProblem(
            field=field,
            code="invalid_date",
            message="Informe uma data válida no formato AAAA-MM-DD.",
        )
    if "too_short" in error_type or "too_long" in error_type:
        return FieldProblem(
            field=field,
            code="invalid_length",
            message="Revise a quantidade de caracteres deste campo.",
        )

    # A mensagem interna pode carregar contexto técnico ou o valor recebido.
    # A resposta pública usa texto estável e nunca replica esse conteúdo.
    return FieldProblem(
        field=field,
        code="invalid_value",
        message="O valor informado não é válido para este campo.",
    )


def install_problem_handlers(application: FastAPI) -> None:
    """Registra tradutores de exceção sem acoplar o domínio ao protocolo HTTP."""

    @application.exception_handler(AuthenticationError)
    async def handle_authentication_error(
        request: Request,
        exception: AuthenticationError,
    ) -> JSONResponse:
        if isinstance(exception, AuthenticationUnavailableError):
            return _problem_response(
                request,
                response_status=status.HTTP_503_SERVICE_UNAVAILABLE,
                title="Autenticação indisponível",
                detail="Tente novamente em alguns instantes.",
                code=exception.code,
                headers={"Retry-After": "30"},
            )

        # O desafio Bearer permite que clientes entendam como renovar a sessão
        # sem depender do texto visível da mensagem de erro.
        return _problem_response(
            request,
            response_status=status.HTTP_401_UNAUTHORIZED,
            title="Entre novamente para continuar",
            detail=str(exception),
            code=exception.code,
            headers={"WWW-Authenticate": "Bearer"},
        )

    @application.exception_handler(ApplicationError)
    async def handle_application_error(
        request: Request,
        exception: ApplicationError,
    ) -> JSONResponse:
        if isinstance(exception, PermissionDeniedError):
            response_status = status.HTTP_403_FORBIDDEN
            title = "Operação não permitida"
            headers = None
        elif isinstance(exception, PersistenceUnavailableError):
            response_status = status.HTTP_503_SERVICE_UNAVAILABLE
            title = "Dados temporariamente indisponíveis"
            headers = {"Retry-After": "30"}
        elif isinstance(exception, PersistenceRejectedError):
            response_status = status.HTTP_422_UNPROCESSABLE_CONTENT
            title = "Os dados não puderam ser processados"
            headers = None
        else:
            response_status = status.HTTP_400_BAD_REQUEST
            title = "Não foi possível concluir a operação"
            headers = None

        return _problem_response(
            request,
            response_status=response_status,
            title=title,
            detail=str(exception),
            code=exception.code,
            headers=headers,
        )

    @application.exception_handler(StudentDomainError)
    async def handle_student_domain_error(
        request: Request,
        exception: StudentDomainError,
    ) -> JSONResponse:
        if isinstance(exception, DuplicateCPFError):
            return _problem_response(
                request,
                response_status=status.HTTP_409_CONFLICT,
                title="CPF já cadastrado",
                detail="Confira o cadastro existente antes de continuar.",
                code=exception.code,
                errors=[
                    FieldProblem(
                        field="cpf",
                        code=exception.code,
                        message="Este CPF já pertence a um cadastro.",
                    )
                ],
            )

        if isinstance(exception, InvalidCPFError):
            field = "cpf"
        elif isinstance(exception, InvalidPhoneError):
            field = "guardian.phone"
        else:
            field = "request"

        return _problem_response(
            request,
            response_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
            title="Dados inválidos",
            detail=str(exception),
            code=exception.code,
            errors=[
                FieldProblem(
                    field=field,
                    code=exception.code,
                    message=str(exception),
                )
            ],
        )

    @application.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exception: RequestValidationError,
    ) -> JSONResponse:
        # Ordenar por campo produz uma resposta determinística e facilita tanto
        # testes quanto a apresentação sequencial dos erros em tecnologia assistiva.
        errors = sorted(
            (_validation_problem(error) for error in exception.errors()),
            key=lambda error: error.field,
        )
        return _problem_response(
            request,
            response_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
            title="Revise os campos informados",
            detail="Um ou mais campos precisam ser corrigidos antes de continuar.",
            code="validation_error",
            errors=errors,
        )

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request,
        exception: StarletteHTTPException,
    ) -> JSONResponse:
        titles = {
            status.HTTP_401_UNAUTHORIZED: "Autenticação necessária",
            status.HTTP_403_FORBIDDEN: "Acesso não autorizado",
            status.HTTP_404_NOT_FOUND: "Recurso não encontrado",
            status.HTTP_405_METHOD_NOT_ALLOWED: "Método não permitido",
        }
        title = titles.get(
            exception.status_code,
            HTTPStatus(exception.status_code).phrase,
        )
        return _problem_response(
            request,
            response_status=exception.status_code,
            title=title,
            detail="A requisição não pôde ser concluída neste endereço.",
            code=f"http_{exception.status_code}",
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exception: Exception) -> JSONResponse:
        # Exceções de SDK ou banco podem carregar valores na própria mensagem.
        # Registramos somente tipo e request_id; nenhuma entrada do cliente é copiada.
        logger.error(
            "Falha inesperada na API",
            extra={
                "request_id": str(_request_id(request)),
                "exception_type": type(exception).__name__,
            },
        )
        return _problem_response(
            request,
            response_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Não foi possível concluir a operação",
            detail="Tente novamente. Se o problema continuar, informe o código da requisição.",
            code="internal_error",
        )
