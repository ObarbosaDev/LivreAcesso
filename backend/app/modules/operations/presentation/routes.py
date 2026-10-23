"""Liveness e readiness para pessoas, plataforma e monitoramento."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from backend.app.core.config import Settings
from backend.app.modules.operations.application.health import ReadinessProbe
from backend.app.shared.application.exceptions import ServiceNotReadyError


class HealthOutput(BaseModel):
    """Resposta estável sem informação sensível da infraestrutura."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["alive", "ready"]
    service: str
    version: str


class ReadinessOutput(HealthOutput):
    persistence: Literal["up"]


def build_operations_router(settings: Settings, probe: ReadinessProbe) -> APIRouter:
    router = APIRouter(tags=["Operacional"])

    def live_response() -> HealthOutput:
        return HealthOutput(
            status="alive",
            service=settings.app_name,
            version=settings.version,
        )

    @router.get(
        "/health/live",
        response_model=HealthOutput,
        summary="Verificar se o processo está vivo",
    )
    def liveness() -> HealthOutput:
        """Não acessa rede ou banco; deve responder mesmo durante falha externa."""

        return live_response()

    @router.get(
        "/health",
        response_model=HealthOutput,
        include_in_schema=False,
    )
    def legacy_health() -> HealthOutput:
        """Preserva o endpoint anterior enquanto clientes migram para `/health/live`."""

        return live_response()

    @router.get(
        "/health/ready",
        response_model=ReadinessOutput,
        summary="Verificar se dependências estão prontas",
    )
    async def readiness() -> ReadinessOutput:
        """Consulta apenas a RPC constante de saúde, sem acessar dados de negócio."""

        result = await probe.check()
        if not result.persistence_available:
            # Implementações futuras podem retornar estado em vez de exceção.
            # Falhar fechado mantém 200 reservado a uma dependência utilizável.
            raise ServiceNotReadyError
        return ReadinessOutput(
            status="ready",
            service=settings.app_name,
            version=settings.version,
            persistence="up",
        )

    return router
