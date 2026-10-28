"""Falhas previsíveis das regras de frequência."""


class AttendanceDomainError(Exception):
    """Erro-base que pode ser traduzido sem expor detalhes internos."""


class InvalidAttendanceError(AttendanceDomainError):
    """A chamada não respeita uma regra de negócio."""


class AttendanceAlreadyClosedError(AttendanceDomainError):
    """Uma sessão fechada não aceita alterações comuns."""
