"""Contratos do acompanhamento individual do estudante."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StudentEvaluationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_start: date
    period_end: date
    performance_score: int = Field(ge=1, le=10)
    evolution_score: int = Field(ge=1, le=10)
    interaction_score: int = Field(ge=1, le=10)
    participation_score: int = Field(ge=1, le=10)
    autonomy_score: int = Field(ge=1, le=10)
    wellbeing_score: int = Field(ge=1, le=10)
    support_level: str = Field(min_length=1, max_length=30)
    observations: str = Field(min_length=10, max_length=4000)
    effective_strategies: str = Field(min_length=10, max_length=4000)
    next_objective: str = Field(min_length=10, max_length=2000)


class StudentEvaluationOutput(StudentEvaluationInput):
    id: UUID
    student_id: UUID
    evaluator_id: UUID
    created_at: datetime
    updated_at: datetime


class StudentEvaluationListOutput(BaseModel):
    items: list[StudentEvaluationOutput]
