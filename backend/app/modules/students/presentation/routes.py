"""Rotas HTTP do contexto de alunos."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from backend.app.core.container import ApplicationContainer
from backend.app.modules.identity.presentation.dependencies import require_request_context
from backend.app.modules.students.application.dtos import (
    ChangeStudentStatusInput,
    RegisterStudentInput,
    StudentDetailOutput,
    StudentOutput,
    StudentPageOutput,
    UpdateStudentInput,
)
from backend.app.modules.students.domain.entities import StudentStatus
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.presentation.problem_details import ProblemDetail

_PROBLEM_RESPONSE = {"model": ProblemDetail}


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
            status.HTTP_409_CONFLICT: _PROBLEM_RESPONSE,
            status.HTTP_422_UNPROCESSABLE_CONTENT: _PROBLEM_RESPONSE,
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

    @router.get(
        "/{student_id}",
        response_model=StudentDetailOutput,
        summary="Consultar os dados de um aluno",
        description=(
            "Retorna contato integral do responsável. No Supabase, esta leitura "
            "é autorizada e registrada na auditoria."
        ),
        responses={status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE},
    )
    async def get_student(
        student_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> StudentDetailOutput:
        """Obtém detalhe sensível sem liberar o CPF integral."""
        return await container.students_for(context).get_student.execute(student_id)

    @router.put(
        "/{student_id}",
        response_model=StudentDetailOutput,
        summary="Atualizar os dados de um aluno",
        description=(
            "Substitui os dados editáveis com concorrência otimista. CPF e status "
            "não podem ser alterados por esta operação."
        ),
        responses={
            status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE,
            status.HTTP_409_CONFLICT: _PROBLEM_RESPONSE,
            status.HTTP_422_UNPROCESSABLE_CONTENT: _PROBLEM_RESPONSE,
        },
    )
    async def update_student(
        student_id: UUID,
        payload: UpdateStudentInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> StudentDetailOutput:
        """Atualiza aluno e responsável sem sobrescrever uma edição concorrente."""
        return await container.students_for(context).update_student.execute(student_id, payload)

    @router.post(
        "/{student_id}/deactivate",
        response_model=StudentDetailOutput,
        summary="Desativar o cadastro de um aluno",
        description=(
            "Desativa sem excluir histórico. A RPC exige perfil de coordenação, "
            "motivo e versão atual do cadastro."
        ),
        responses={
            status.HTTP_403_FORBIDDEN: _PROBLEM_RESPONSE,
            status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE,
            status.HTTP_409_CONFLICT: _PROBLEM_RESPONSE,
            status.HTTP_422_UNPROCESSABLE_CONTENT: _PROBLEM_RESPONSE,
        },
    )
    async def deactivate_student(
        student_id: UUID,
        payload: ChangeStudentStatusInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> StudentDetailOutput:
        """Desativa o cadastro mantendo histórico, autoria e justificativa."""
        return await container.students_for(context).deactivate_student.execute(student_id, payload)

    @router.post(
        "/{student_id}/activate",
        response_model=StudentDetailOutput,
        summary="Reativar o cadastro de um aluno",
        description="Reativa um cadastro preservado, com os mesmos controles da desativação.",
        responses={
            status.HTTP_403_FORBIDDEN: _PROBLEM_RESPONSE,
            status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE,
            status.HTTP_409_CONFLICT: _PROBLEM_RESPONSE,
            status.HTTP_422_UNPROCESSABLE_CONTENT: _PROBLEM_RESPONSE,
        },
    )
    async def activate_student(
        student_id: UUID,
        payload: ChangeStudentStatusInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> StudentDetailOutput:
        """Reativa o cadastro sem recriar a pessoa ou perder seu histórico."""
        return await container.students_for(context).activate_student.execute(student_id, payload)

    return router
