"""Rotas HTTP do contexto de alunos."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from backend.app.core.container import ApplicationContainer
from backend.app.modules.identity.presentation.dependencies import require_request_context
from backend.app.modules.students.application.dtos import (
    RegisterStudentInput,
    StudentOutput,
    StudentPageOutput,
)
from backend.app.modules.students.domain.entities import StudentStatus
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.presentation.problem_details import ProblemDetail


def build_students_router(container: ApplicationContainer) -> APIRouter:
    router = APIRouter(prefix="/students", tags=["Alunos"])

    @router.post(
        "",
        response_model=StudentOutput,
        status_code=status.HTTP_201_CREATED,
        summary="Cadastrar um aluno",
        description=(
            "Cria o cadastro pessoal do aluno e do responsável principal. "
            "A matrícula em uma turma será realizada por um endpoint próprio."
        ),
        responses={
            status.HTTP_409_CONFLICT: {
                "model": ProblemDetail,
                "description": "CPF já cadastrado",
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "model": ProblemDetail,
                "description": "Dados inválidos ou campos não aceitos",
            },
        },
    )
    async def register_student(
        payload: RegisterStudentInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> StudentOutput:
        """Valida e cadastra um aluno sem expor seus dados pessoais na resposta."""
        services = container.students_for(context)
        return await services.register_student.execute(payload)

    @router.get(
        "",
        response_model=StudentPageOutput,
        summary="Pesquisar alunos",
        description=(
            "Pesquisa nomes sem diferenciar maiúsculas ou acentos e devolve "
            "no máximo 100 registros por página."
        ),
    )
    async def list_students(
        context: Annotated[RequestContext, Depends(require_request_context)],
        student_status: Annotated[StudentStatus | None, Query(alias="status")] = None,
        query: Annotated[
            str | None,
            Query(
                min_length=2,
                max_length=120,
                description="Trecho do nome; CPF e telefone não são pesquisados por esta rota.",
            ),
        ] = None,
        page: Annotated[int, Query(ge=1, description="Página iniciada em 1.")] = 1,
        page_size: Annotated[
            int,
            Query(ge=1, le=100, description="Quantidade de registros por página."),
        ] = 25,
    ) -> StudentPageOutput:
        """Lista somente os campos seguros necessários para identificação visual."""
        services = container.students_for(context)
        return await services.list_students.execute(
            status=student_status,
            query=query,
            page=page,
            page_size=page_size,
        )

    return router
