"""Relatórios exportáveis do acompanhamento individual."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from backend.app.core.container import ApplicationContainer
from backend.app.modules.identity.presentation.dependencies import require_request_context
from backend.app.modules.reporting.application.exports import to_csv, to_pdf
from backend.app.shared.application.request_context import RequestContext


def build_reporting_router(container: ApplicationContainer) -> APIRouter:
    router = APIRouter(prefix="/reports", tags=["Relatórios"])

    @router.get("/students/{student_id}")
    async def student_report(
        student_id: UUID,
        file_format: Annotated[Literal["csv", "pdf"], Query(alias="format")] = "pdf",
        context: Annotated[RequestContext, Depends(require_request_context)] = None,  # type: ignore[assignment]
    ) -> Response:
        evaluations = await container.evaluations_for(context).list.execute(student_id, context)
        rows = [
            {
                "student_id": str(student_id),
                "period_start": item.period_start.isoformat(),
                "period_end": item.period_end.isoformat(),
                "performance": item.performance_score,
                "evolution": item.evolution_score,
                "interaction": item.interaction_score,
                "participation": item.participation_score,
                "autonomy": item.autonomy_score,
                "wellbeing": item.wellbeing_score,
                "support_level": item.support_level,
                "observations": item.observations,
                "next_objective": item.next_objective,
            }
            for item in evaluations
        ]
        if file_format == "csv":
            return Response(
                content=to_csv(rows),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="relatorio-{student_id}.csv"'
                },
            )
        return Response(
            content=to_pdf("Relatório individual do estudante", rows),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="relatorio-{student_id}.pdf"'},
        )

    return router
