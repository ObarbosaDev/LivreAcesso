"""Rotas HTTP do contexto de alunos."""

from fastapi import APIRouter, Query, status

from backend.app.core.container import ApplicationContainer
from backend.app.modules.students.application.dtos import RegisterStudentInput, StudentOutput
from backend.app.modules.students.domain.entities import Modality, StudentStatus


def build_students_router(container: ApplicationContainer) -> APIRouter:
    router = APIRouter(prefix="/students", tags=["Alunos"])

    @router.post(
        "",
        response_model=StudentOutput,
        status_code=status.HTTP_201_CREATED,
        summary="Cadastrar um aluno",
        responses={
            status.HTTP_409_CONFLICT: {"description": "CPF já cadastrado"},
            status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Dados inválidos"},
        },
    )
    def register_student(payload: RegisterStudentInput) -> StudentOutput:
        return container.register_student.execute(payload)

    @router.get(
        "",
        response_model=list[StudentOutput],
        summary="Listar alunos",
    )
    def list_students(
        modality: Modality | None = Query(default=None),
        student_status: StudentStatus | None = Query(default=None, alias="status"),
    ) -> tuple[StudentOutput, ...]:
        return container.list_students.execute(modality=modality, status=student_status)

    return router
