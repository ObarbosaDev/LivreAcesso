"""Erros de negócio dos perfis e papéis operacionais."""


class ProfileDomainError(Exception):
    """Violação esperada das regras do perfil operacional."""

    code = "profile_domain_error"


class InvalidProfileDataError(ProfileDomainError):
    code = "invalid_profile_data"


class InvalidAccessChangeReasonError(ProfileDomainError):
    code = "invalid_access_change_reason"

    def __init__(self) -> None:
        super().__init__("Informe um motivo entre 10 e 500 caracteres.")


class InvalidProfileRoleError(ProfileDomainError):
    code = "invalid_profile_role"

    def __init__(self) -> None:
        super().__init__("Escolha um papel operacional válido.")


class ProfileNotFoundError(ProfileDomainError):
    code = "profile_not_found"

    def __init__(self) -> None:
        super().__init__("O perfil operacional não foi encontrado.")


class ProfileVersionConflictError(ProfileDomainError):
    code = "profile_version_conflict"

    def __init__(self) -> None:
        super().__init__(
            "O perfil foi alterado por outra pessoa. Atualize os dados e tente novamente."
        )


class LastActiveCoordinatorError(ProfileDomainError):
    code = "last_active_coordinator"

    def __init__(self) -> None:
        super().__init__("O último coordenador ativo não pode perder acesso.")


class ProfileRoleRequiredError(ProfileDomainError):
    code = "profile_role_required"

    def __init__(self) -> None:
        super().__init__("Defina um papel operacional antes de ativar o perfil.")
