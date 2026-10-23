"""Objetos de valor usados nas mudanças de acesso."""

from dataclasses import dataclass

from backend.app.modules.identity.domain.exceptions import InvalidAccessChangeReasonError


@dataclass(frozen=True, slots=True)
class AccessChangeReason:
    """Justificativa protegida de uma alteração de papel ou bloqueio."""

    value: str

    def __post_init__(self) -> None:
        normalized = " ".join(self.value.split())
        if not 10 <= len(normalized) <= 500:
            raise InvalidAccessChangeReasonError
        object.__setattr__(self, "value", normalized)
