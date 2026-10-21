"""Barramento síncrono de eventos usado dentro do monólito modular."""

from collections import defaultdict
from typing import Protocol, TypeVar, cast

from backend.app.shared.domain.events import DomainEvent

EventT = TypeVar("EventT", bound=DomainEvent)
EventTContravariant = TypeVar(
    "EventTContravariant",
    bound=DomainEvent,
    contravariant=True,
)


class EventHandler(Protocol[EventTContravariant]):
    def __call__(self, event: EventTContravariant, /) -> None: ...


class EventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None: ...


class EventBus:
    """Publica eventos em memória para listeners registrados no processo."""

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler[DomainEvent]]] = defaultdict(list)

    def subscribe(
        self,
        event_type: type[EventT],
        handler: EventHandler[EventT],
    ) -> None:
        registered_handler = cast(EventHandler[DomainEvent], handler)
        self._handlers[event_type].append(registered_handler)

    def publish(self, event: DomainEvent) -> None:
        # A cópia imutável permite que um handler registre outro listener sem
        # alterar a coleção que está sendo percorrida nesta publicação.
        for handler in tuple(self._handlers[type(event)]):
            handler(event)
