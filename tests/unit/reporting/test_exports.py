"""Testes de exportação sem arquivos temporários."""

from backend.app.modules.reporting.application.exports import to_csv, to_pdf


def test_exports_keep_report_in_memory() -> None:
    rows = [{"Estudante": "Ana", "Frequência": "92.00%"}]
    assert b"Estudante" in to_csv(rows)
    assert to_pdf("Relatório de aluno", rows).startswith(b"%PDF-1.4")
