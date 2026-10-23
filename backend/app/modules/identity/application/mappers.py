"""Conversões entre perfis, projeções e contratos HTTP."""

from backend.app.modules.identity.application.dtos import ProfileOutput
from backend.app.modules.identity.application.queries import ProfileListItem
from backend.app.modules.identity.domain.entities import UserProfile, capabilities_for_role


class ProfileMapper:
    @staticmethod
    def to_output(profile: UserProfile) -> ProfileOutput:
        return ProfileOutput(
            id=profile.id,
            full_name=profile.full_name,
            role=profile.role,
            active=profile.active,
            capabilities=list(profile.capabilities),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    @staticmethod
    def list_item_to_output(item: ProfileListItem) -> ProfileOutput:
        # Perfil inativo não recebe capacidades, mesmo que preserve seu papel
        # para histórico e eventual reativação pela coordenação.
        capabilities = list(capabilities_for_role(item.role)) if item.active else []
        return ProfileOutput(
            id=item.id,
            full_name=item.full_name,
            role=item.role,
            active=item.active,
            capabilities=capabilities,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
