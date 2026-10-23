"""Contratos e serviços mínimos de prontidão da aplicação."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    """Resultado interno sem URL, chave ou detalhes da dependência."""

    persistence_available: bool


class ReadinessProbe(Protocol):
    async def check(self) -> ReadinessResult: ...


class LocalReadinessProbe:
    """Declara pronto o armazenamento transitório de desenvolvimento/testes."""

    async def check(self) -> ReadinessResult:
        return ReadinessResult(persistence_available=True)
