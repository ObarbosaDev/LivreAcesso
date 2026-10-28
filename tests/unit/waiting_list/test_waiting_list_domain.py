"""Testes do ciclo humano da lista de espera."""

from uuid import uuid4

import pytest

from backend.app.modules.waiting_list.domain.entities import (
    WaitingListEntry,
    WaitingListStatus,
)


def test_entry_requires_human_offer_before_acceptance() -> None:
    entry = WaitingListEntry(student_id=uuid4(), class_id=uuid4(), position=1)

    with pytest.raises(ValueError):
        entry.accept()

    entry.offer()
    entry.accept()

    assert entry.status is WaitingListStatus.ACCEPTED
    assert entry.offered_at is not None
    assert entry.decided_at is not None


def test_waiting_entry_can_be_withdrawn_and_keeps_position_history() -> None:
    entry = WaitingListEntry(student_id=uuid4(), class_id=uuid4(), position=3)
    entry.withdraw()

    assert entry.status is WaitingListStatus.WITHDRAWN
    assert entry.position == 3
