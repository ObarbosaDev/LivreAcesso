"""Listeners dos eventos relacionados a alunos."""

import logging
from dataclasses import dataclass

from backend.app.modules.students.domain.events import StudentRegistered

logger = logging.getLogger("livre_acesso.audit")


@dataclass(slots=True)
class StudentRegisteredAuditListener:
    """Registra o fato sem expor CPF, nome, telefone ou e-mail."""

    def __call__(self, event: StudentRegistered) -> None:
        logger.info(
            "Aluno registrado",
            extra={
                "event_id": str(event.event_id),
                "student_id": str(event.student_id),
                "modality": event.modality,
                "occurred_at": event.occurred_at.isoformat(),
            },
        )
