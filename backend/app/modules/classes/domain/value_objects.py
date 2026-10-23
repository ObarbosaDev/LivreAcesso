"""Objetos de valor do catálogo operacional."""

from dataclasses import dataclass

from backend.app.modules.classes.domain.exceptions import InvalidClassChangeReasonError


@dataclass(frozen=True, slots=True)
class ClassChangeReason:
    """Justificativa privada para ativar ou desativar item do catálogo."""

    value: str

    def __post_init__(self) -> None:
        normalized = " ".join(self.value.split())
        if not 10 <= len(normalized) <= 500:
            raise InvalidClassChangeReasonError
        object.__setattr__(self, "value", normalized)
