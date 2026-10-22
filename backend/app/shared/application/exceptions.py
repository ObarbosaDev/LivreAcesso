"""Erros esperados da aplicação que não pertencem a um domínio específico."""


class ApplicationError(Exception):
    """Falha conhecida que pode ser traduzida sem expor detalhes internos."""

    code = "application_error"


class PermissionDeniedError(ApplicationError):
    code = "permission_denied"

    def __init__(self) -> None:
        super().__init__("Seu perfil não possui permissão para esta operação.")


class PersistenceUnavailableError(ApplicationError):
    code = "persistence_unavailable"

    def __init__(self) -> None:
        super().__init__("Os dados estão temporariamente indisponíveis.")


class PersistenceRejectedError(ApplicationError):
    code = "persistence_rejected"

    def __init__(self) -> None:
        super().__init__("Os dados não puderam ser aceitos pelo armazenamento.")
