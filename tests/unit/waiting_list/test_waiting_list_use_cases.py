"""Testes dos casos de uso da fila."""

import asyncio
from uuid import uuid4

import pytest

from backend.app.modules.waiting_list.application.dtos import WaitingListInput
from backend.app.modules.waiting_list.application.use_cases import (
    AcceptWaitingListEntry,
    JoinWaitingList,
    OfferWaitingListEntry,
)
from backend.app.modules.waiting_list.infrastructure.repositories import (
    InMemoryWaitingListRepository,
)


def test_waiting_list_requires_offer_before_acceptance_and_keeps_order() -> None:
    async def scenario() -> None:
        repository = InMemoryWaitingListRepository()
        first = await JoinWaitingList(repository).execute(
            WaitingListInput(student_id=uuid4(), class_id=uuid4())
        )
        second = await JoinWaitingList(repository).execute(
            WaitingListInput(student_id=uuid4(), class_id=first.class_id)
        )
        with pytest.raises(ValueError):
            await AcceptWaitingListEntry(repository).execute(first.id)
        await OfferWaitingListEntry(repository).execute(first.id)
        accepted = await AcceptWaitingListEntry(repository).execute(first.id)

        assert first.position == 1
        assert second.position == 2
        assert accepted.status == "aceita"

    asyncio.run(scenario())
