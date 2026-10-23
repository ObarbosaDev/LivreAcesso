"""Rotas de modalidades e turmas com autorização por capacidade."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from backend.app.core.container import ApplicationContainer
from backend.app.modules.classes.application.dtos import (
    ChangeCatalogActivationInput,
    ClassOutput,
    ClassPageOutput,
    CreateClassInput,
    CreateModalityInput,
    ModalityOutput,
    ModalityPageOutput,
    UpdateClassInput,
    UpdateModalityInput,
)
from backend.app.modules.identity.presentation.dependencies import require_request_context
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.presentation.problem_details import ProblemDetail

_PROBLEM_RESPONSE: dict[str, Any] = {"model": ProblemDetail}
_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_403_FORBIDDEN: _PROBLEM_RESPONSE,
    status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE,
    status.HTTP_409_CONFLICT: _PROBLEM_RESPONSE,
    status.HTTP_422_UNPROCESSABLE_CONTENT: _PROBLEM_RESPONSE,
}


def build_classes_router(container: ApplicationContainer) -> APIRouter:
    root = APIRouter()
    modalities = APIRouter(prefix="/modalities", tags=["Modalidades"])
    classes = APIRouter(prefix="/classes", tags=["Turmas"])

    @modalities.get(
        "",
        response_model=ModalityPageOutput,
        summary="Listar modalidades",
        description="Pesquisa o catálogo sem misturar modalidade com oferta de turma.",
        responses={status.HTTP_403_FORBIDDEN: _PROBLEM_RESPONSE},
    )
    async def list_modalities(
        context: Annotated[RequestContext, Depends(require_request_context)],
        active: Annotated[bool | None, Query()] = None,
        query: Annotated[str | None, Query(min_length=2, max_length=80)] = None,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    ) -> ModalityPageOutput:
        return await container.classes_for(context).list_modalities.execute(
            active=active,
            query=query,
            page=page,
            page_size=page_size,
        )

    @modalities.post(
        "",
        response_model=ModalityOutput,
        status_code=status.HTTP_201_CREATED,
        summary="Criar modalidade",
        description="Cria um tipo de atividade ativo; somente coordenação administra o catálogo.",
        responses=_ERROR_RESPONSES,
    )
    async def create_modality(
        payload: CreateModalityInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ModalityOutput:
        return await container.classes_for(context).create_modality.execute(payload)

    @modalities.get(
        "/{modality_id}",
        response_model=ModalityOutput,
        summary="Consultar modalidade",
        responses={
            status.HTTP_403_FORBIDDEN: _PROBLEM_RESPONSE,
            status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE,
        },
    )
    async def get_modality(
        modality_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ModalityOutput:
        return await container.classes_for(context).get_modality.execute(modality_id)

    @modalities.put(
        "/{modality_id}",
        response_model=ModalityOutput,
        summary="Atualizar modalidade",
        responses=_ERROR_RESPONSES,
    )
    async def update_modality(
        modality_id: UUID,
        payload: UpdateModalityInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ModalityOutput:
        return await container.classes_for(context).update_modality.execute(
            modality_id,
            payload,
        )

    @modalities.post(
        "/{modality_id}/activate",
        response_model=ModalityOutput,
        summary="Ativar modalidade",
        responses=_ERROR_RESPONSES,
    )
    async def activate_modality(
        modality_id: UUID,
        payload: ChangeCatalogActivationInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ModalityOutput:
        return await container.classes_for(context).activate_modality.execute(
            modality_id,
            payload,
        )

    @modalities.post(
        "/{modality_id}/deactivate",
        response_model=ModalityOutput,
        summary="Desativar modalidade",
        description="Exige que todas as turmas da modalidade estejam inativas.",
        responses=_ERROR_RESPONSES,
    )
    async def deactivate_modality(
        modality_id: UUID,
        payload: ChangeCatalogActivationInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ModalityOutput:
        return await container.classes_for(context).deactivate_modality.execute(
            modality_id,
            payload,
        )

    @classes.get(
        "",
        response_model=ClassPageOutput,
        summary="Listar turmas",
        description=(
            "Coordenação, recepção e consulta veem o catálogo autorizado. "
            "Instrutores recebem somente as turmas às quais estão vinculados."
        ),
        responses={status.HTTP_403_FORBIDDEN: _PROBLEM_RESPONSE},
    )
    async def list_classes(
        context: Annotated[RequestContext, Depends(require_request_context)],
        active: Annotated[bool | None, Query()] = None,
        modality_id: Annotated[UUID | None, Query()] = None,
        query: Annotated[str | None, Query(min_length=2, max_length=120)] = None,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    ) -> ClassPageOutput:
        return await container.classes_for(context).list_classes.execute(
            active=active,
            modality_id=modality_id,
            query=query,
            page=page,
            page_size=page_size,
        )

    @classes.post(
        "",
        response_model=ClassOutput,
        status_code=status.HTTP_201_CREATED,
        summary="Criar turma",
        description=(
            "Cria uma oferta concreta com capacidade, faixa etária, local, "
            "horários e ao menos um instrutor ativo."
        ),
        responses=_ERROR_RESPONSES,
    )
    async def create_class(
        payload: CreateClassInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ClassOutput:
        return await container.classes_for(context).create_class.execute(payload)

    @classes.get(
        "/{class_id}",
        response_model=ClassOutput,
        summary="Consultar turma",
        responses={
            status.HTTP_403_FORBIDDEN: _PROBLEM_RESPONSE,
            status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE,
        },
    )
    async def get_class(
        class_id: UUID,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ClassOutput:
        return await container.classes_for(context).get_class.execute(class_id)

    @classes.put(
        "/{class_id}",
        response_model=ClassOutput,
        summary="Atualizar turma",
        description="Substitui configuração completa usando a versão consultada.",
        responses=_ERROR_RESPONSES,
    )
    async def update_class(
        class_id: UUID,
        payload: UpdateClassInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ClassOutput:
        return await container.classes_for(context).update_class.execute(class_id, payload)

    @classes.post(
        "/{class_id}/activate",
        response_model=ClassOutput,
        summary="Ativar turma",
        responses=_ERROR_RESPONSES,
    )
    async def activate_class(
        class_id: UUID,
        payload: ChangeCatalogActivationInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ClassOutput:
        return await container.classes_for(context).activate_class.execute(class_id, payload)

    @classes.post(
        "/{class_id}/deactivate",
        response_model=ClassOutput,
        summary="Desativar turma",
        description="Preserva horários e instrutores para histórico e reativação explícita.",
        responses=_ERROR_RESPONSES,
    )
    async def deactivate_class(
        class_id: UUID,
        payload: ChangeCatalogActivationInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ClassOutput:
        return await container.classes_for(context).deactivate_class.execute(class_id, payload)

    root.include_router(modalities)
    root.include_router(classes)
    return root
