"""Rotas HTTP do contexto de alunos."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from backend.app.core.container import ApplicationContainer
from backend.app.modules.identity.presentation.dependencies import require_request_context
from backend.app.modules.students.application.dtos import (
    AddStudentGuardianInput,
    ChangeStudentStatusInput,
    RegisterStudentInput,
    SetPrimaryGuardianInput,
    StudentDetailOutput,
    StudentGuardianDetailOutput,
    StudentGuardianListOutput,
    StudentGuardianUnlinkOutput,
    StudentOutput,
    StudentPageOutput,
    UnlinkStudentGuardianInput,
    UpdateStudentGuardianInput,
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
        "/{student_id}/guardians",
        response_model=StudentGuardianListOutput,
        summary="Listar responsáveis do aluno",
        description=(
            "Retorna somente contatos ativos com telefone e e-mail mascarados, "
            "ordenando o responsável principal primeiro."
        ),
        responses={status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE},
    )
    async def list_student_guardians(
        student_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> StudentGuardianListOutput:
        """Lista vínculos sem liberar contato integral ou histórico privado."""
        return await container.students_for(context).list_guardians.execute(student_id)

    @router.post(
        "/{student_id}/guardians",
        response_model=StudentGuardianDetailOutput,
        status_code=status.HTTP_201_CREATED,
        summary="Adicionar responsável ao aluno",
        description=(
            "Cria um contato ou reutiliza por UUID um responsável já cadastrado, "
            "permitindo que irmãos compartilhem a mesma pessoa sem duplicação."
        ),
        responses={
            status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE,
            status.HTTP_409_CONFLICT: _PROBLEM_RESPONSE,
            status.HTTP_422_UNPROCESSABLE_CONTENT: _PROBLEM_RESPONSE,
        },
    )
    async def add_student_guardian(
        student_id: UUID,
        payload: AddStudentGuardianInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> StudentGuardianDetailOutput:
        """Inclui ou revincula um contato com concorrência otimista."""
        return await container.students_for(context).add_guardian.execute(student_id, payload)

    @router.get(
        "/{student_id}/guardians/{guardian_id}",
        response_model=StudentGuardianDetailOutput,
        summary="Consultar responsável do aluno",
        description=(
            "Libera telefone e e-mail integrais para a rotina autorizada; "
            "a leitura é registrada na auditoria do Supabase."
        ),
        responses={status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE},
    )
    async def get_student_guardian(
        student_id: UUID,
        guardian_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> StudentGuardianDetailOutput:
        """Obtém um contato integral sem expor CPF ou dados de outros vínculos."""
        return await container.students_for(context).get_guardian.execute(
            student_id,
            guardian_id,
        )

    @router.put(
        "/{student_id}/guardians/{guardian_id}",
        response_model=StudentGuardianDetailOutput,
        summary="Atualizar responsável do aluno",
        description=(
            "Atualiza o contato compartilhado e este vínculo somente quando as "
            "versões do aluno e do responsável ainda são atuais."
        ),
        responses={
            status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE,
            status.HTTP_409_CONFLICT: _PROBLEM_RESPONSE,
            status.HTTP_422_UNPROCESSABLE_CONTENT: _PROBLEM_RESPONSE,
        },
    )
    async def update_student_guardian(
        student_id: UUID,
        guardian_id: UUID,
        payload: UpdateStudentGuardianInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> StudentGuardianDetailOutput:
        """Evita perda de edição tanto no agregado quanto no contato compartilhado."""
        return await container.students_for(context).update_guardian.execute(
            student_id,
            guardian_id,
            payload,
        )

    @router.post(
        "/{student_id}/guardians/{guardian_id}/primary",
        response_model=StudentGuardianDetailOutput,
        summary="Definir responsável principal",
        description="Promove um vínculo ativo e rebaixa o principal anterior na mesma transação.",
        responses={
            status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE,
            status.HTTP_409_CONFLICT: _PROBLEM_RESPONSE,
        },
    )
    async def set_primary_student_guardian(
        student_id: UUID,
        guardian_id: UUID,
        payload: SetPrimaryGuardianInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> StudentGuardianDetailOutput:
        """Mantém exatamente um contato principal para identificação rápida."""
        return await container.students_for(context).set_primary_guardian.execute(
            student_id,
            guardian_id,
            payload,
        )

    @router.post(
        "/{student_id}/guardians/{guardian_id}/unlink",
        response_model=StudentGuardianUnlinkOutput,
        summary="Desvincular responsável do aluno",
        description=(
            "Desativa um vínculo não principal com motivo obrigatório. "
            "Responsável e histórico não são excluídos fisicamente."
        ),
        responses={
            status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE,
            status.HTTP_409_CONFLICT: _PROBLEM_RESPONSE,
            status.HTTP_422_UNPROCESSABLE_CONTENT: _PROBLEM_RESPONSE,
        },
    )
    async def unlink_student_guardian(
        student_id: UUID,
        guardian_id: UUID,
        payload: UnlinkStudentGuardianInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> StudentGuardianUnlinkOutput:
        """Preserva rastreabilidade e impede remover o único principal."""
        return await container.students_for(context).unlink_guardian.execute(
            student_id,
            guardian_id,
            payload,
        )

    @router.get(
        "/{student_id}",
        response_model=StudentDetailOutput,
        summary="Consultar os dados de um aluno",
        description=(
            "Retorna contato integral do responsável principal. No Supabase, "
            "esta leitura é autorizada e registrada na auditoria."
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
            "Substitui nome e nascimento com concorrência otimista. CPF, status "
            "e responsáveis possuem operações próprias e não são alterados aqui."
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
        """Atualiza somente o aluno sem sobrescrever contato compartilhado."""
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
