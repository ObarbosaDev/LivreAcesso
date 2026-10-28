"""Contratos da operação de alertas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from backend.app.modules.alerts.domain.entities import AlertType


class AlertOutput(BaseModel):
    id: UUID
    student_id: UUID
    class_id: UUID | None
    alert_type: AlertType
    title: str
    detail: str
    threshold: int
    status: str
    created_at: datetime
    resolved_at: datetime | None


class AlertInput(BaseModel):
    student_id: UUID
    class_id: UUID | None = None
    alert_type: AlertType
    title: str
    detail: str
    threshold: int
