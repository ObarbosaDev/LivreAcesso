"""Mensagem sanitizada e idempotente para provedores externos."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class CommunicationChannel(StrEnum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"


@dataclass(frozen=True, slots=True)
class OutboundMessage:
    idempotency_key: UUID
    recipient: str
    channel: CommunicationChannel
    subject: str
    body: str
