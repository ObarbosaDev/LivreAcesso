"""Contratos da lista de espera."""

from uuid import UUID

from pydantic import BaseModel

from backend.app.modules.waiting_list.domain.entities import WaitingListStatus


class WaitingListInput(BaseModel):
    student_id: UUID
    class_id: UUID


class WaitingListOutput(BaseModel):
    id: UUID
    student_id: UUID
    class_id: UUID
    position: int
    status: WaitingListStatus


class WaitingListPageOutput(BaseModel):
    items: tuple[WaitingListOutput, ...]
