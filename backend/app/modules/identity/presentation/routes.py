"""Rotas do perfil atual e da administração de acessos."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from backend.app.core.container import ApplicationContainer
from backend.app.modules.identity.application.dtos import (
    ChangeProfileActivationInput,
    ChangeProfileRoleInput,
    InviteProfileInput,
    InviteProfileOutput,
    ProfileOutput,
    ProfilePageOutput,
    UpdateMyProfileInput,
)
from backend.app.modules.identity.domain.entities import UserRole
from backend.app.modules.identity.presentation.dependencies import require_request_context
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.presentation.problem_details import ProblemDetail

_PROBLEM_RESPONSE = {"model": ProblemDetail}


def build_identity_router(container: ApplicationContainer) -> APIRouter:
    router = APIRouter(tags=["Perfis e acessos"])

    @router.get(
        "/me",
        response_model=ProfileOutput,
        summary="Consultar meu perfil",
        responses={status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE},
    )
    async def get_my_profile(
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ProfileOutput:
        """Retorna identidade operacional e capacidades sem dados internos do Auth."""

        return await container.identity_for(context).get_my_profile.execute()

    @router.put(
        "/me",
        response_model=ProfileOutput,
        summary="Atualizar meu nome de exibição",
        responses={
            status.HTTP_409_CONFLICT: _PROBLEM_RESPONSE,
            status.HTTP_422_UNPROCESSABLE_CONTENT: _PROBLEM_RESPONSE,
        },
    )
    async def update_my_profile(
        payload: UpdateMyProfileInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ProfileOutput:
        """Permite corrigir o nome sem alterar papel, ativação ou identidade Auth."""

        return await container.identity_for(context).update_my_profile.execute(payload)

    @router.get(
        "/profiles",
        response_model=ProfilePageOutput,
        summary="Pesquisar perfis operacionais",
        description="Disponível somente para coordenação ativa.",
        responses={status.HTTP_403_FORBIDDEN: _PROBLEM_RESPONSE},
    )
    async def list_profiles(
        context: Annotated[RequestContext, Depends(require_request_context)],
        role: Annotated[UserRole | None, Query()] = None,
        active: Annotated[bool | None, Query()] = None,
        query: Annotated[str | None, Query(min_length=2, max_length=120)] = None,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    ) -> ProfilePageOutput:
        """Lista apenas nome, papel, estado, capacidades e versão."""

        return await container.identity_for(context).list_profiles.execute(
            role=role,
            active=active,
            query=query,
            page=page,
            page_size=page_size,
        )

    @router.post(
        "/profiles/{profile_id}/role",
        response_model=ProfileOutput,
        summary="Alterar papel operacional",
        responses={
            status.HTTP_403_FORBIDDEN: _PROBLEM_RESPONSE,
            status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE,
            status.HTTP_409_CONFLICT: _PROBLEM_RESPONSE,
            status.HTTP_422_UNPROCESSABLE_CONTENT: _PROBLEM_RESPONSE,
        },
    )
    async def change_profile_role(
        profile_id: UUID,
        payload: ChangeProfileRoleInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ProfileOutput:
        """Exige coordenação, motivo e versão sem aceitar o papel pendente."""

        return await container.identity_for(context).change_profile_role.execute(
            profile_id,
            payload,
        )

    @router.post(
        "/profiles/invite",
        response_model=InviteProfileOutput,
        status_code=status.HTTP_202_ACCEPTED,
        summary="Convidar membro da equipe",
        responses={status.HTTP_403_FORBIDDEN: _PROBLEM_RESPONSE},
    )
    async def invite_profile(
        payload: InviteProfileInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> InviteProfileOutput:
        service = container.identity_for(context).invite_profile
        if service is None:
            raise RuntimeError("Convites não estão configurados neste ambiente.")
        return await service.execute(payload)

    @router.post(
        "/profiles/invite-link",
        response_model=InviteProfileOutput,
        status_code=status.HTTP_201_CREATED,
        summary="Gerar link de convite",
        responses={status.HTTP_403_FORBIDDEN: _PROBLEM_RESPONSE},
    )
    async def generate_invite_link(
        payload: InviteProfileInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> InviteProfileOutput:
        service = container.identity_for(context).invite_profile
        if service is None:
            raise RuntimeError("Convites não estão configurados neste ambiente.")
        return await service.generate_link(payload)

    @router.post(
        "/profiles/{profile_id}/activate",
        response_model=ProfileOutput,
        summary="Ativar perfil operacional",
        responses={
            status.HTTP_403_FORBIDDEN: _PROBLEM_RESPONSE,
            status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE,
            status.HTTP_409_CONFLICT: _PROBLEM_RESPONSE,
            status.HTTP_422_UNPROCESSABLE_CONTENT: _PROBLEM_RESPONSE,
        },
    )
    async def activate_profile(
        profile_id: UUID,
        payload: ChangeProfileActivationInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ProfileOutput:
        """Ativa somente perfil com papel definido e preserva histórico."""

        return await container.identity_for(context).activate_profile.execute(profile_id, payload)

    @router.post(
        "/profiles/{profile_id}/deactivate",
        response_model=ProfileOutput,
        summary="Desativar perfil operacional",
        responses={
            status.HTTP_403_FORBIDDEN: _PROBLEM_RESPONSE,
            status.HTTP_404_NOT_FOUND: _PROBLEM_RESPONSE,
            status.HTTP_409_CONFLICT: _PROBLEM_RESPONSE,
            status.HTTP_422_UNPROCESSABLE_CONTENT: _PROBLEM_RESPONSE,
        },
    )
    async def deactivate_profile(
        profile_id: UUID,
        payload: ChangeProfileActivationInput,
        context: Annotated[RequestContext, Depends(require_request_context)],
    ) -> ProfileOutput:
        """Bloqueia acesso sem excluir conta, auditoria ou histórico."""

        return await container.identity_for(context).deactivate_profile.execute(profile_id, payload)

    return router
