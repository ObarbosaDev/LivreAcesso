"""Entidades da fila: posição rastreável e vaga nunca concedida automaticamente."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class WaitingListStatus(StrEnum):
    WAITING = "aguardando"
    OFFERED = "vaga_ofertada"
    ACCEPTED = "aceita"
    WITHDRAWN = "retirada"
    EXPIRED = "expirada"


@dataclass(slots=True)
class WaitingListEntry:
    student_id: UUID
    class_id: UUID
    position: int
    status: WaitingListStatus = WaitingListStatus.WAITING
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    offered_at: datetime | None = None
    decided_at: datetime | None = None

    def offer(self, *, offered_at: datetime | None = None) -> None:
        if self.status is not WaitingListStatus.WAITING:
            raise ValueError("Somente uma pessoa aguardando pode receber oferta.")
        self.status = WaitingListStatus.OFFERED
        self.offered_at = offered_at or datetime.now(UTC)

    def accept(self, *, decided_at: datetime | None = None) -> None:
        if self.status is not WaitingListStatus.OFFERED:
            raise ValueError("A vaga precisa ser ofertada antes da confirmação.")
        self.status = WaitingListStatus.ACCEPTED
        self.decided_at = decided_at or datetime.now(UTC)

    def withdraw(self, *, decided_at: datetime | None = None) -> None:
        if self.status in {WaitingListStatus.ACCEPTED, WaitingListStatus.WITHDRAWN}:
            raise ValueError("Esta entrada não pode ser retirada neste estado.")
        self.status = WaitingListStatus.WITHDRAWN
        self.decided_at = decided_at or datetime.now(UTC)
