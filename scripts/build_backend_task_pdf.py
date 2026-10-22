"""Gera o PDF versionável do plano de tarefas a partir do Markdown."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import markdown

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "docs" / "backend-task-plan.md"
OUTPUT = PROJECT_ROOT / "docs" / "LivreAcesso-Plano-Tarefas-Backend.pdf"
CACHE_DIR = PROJECT_ROOT / ".cache" / "pdf"


_STYLES = """
@page {
  size: A4;
  margin: 17mm 15mm 19mm;
}

:root {
  --navy: #11162b;
  --navy-soft: #202844;
  --orange: #ff5a3c;
  --blue: #4f7cff;
  --purple: #9b67f0;
  --gold: #f6b91a;
  --ink: #1a2134;
  --muted: #5b6478;
  --line: #d9deea;
  --paper: #ffffff;
  --soft: #f5f7fb;
}

* { box-sizing: border-box; }
html { font-size: 10.2pt; }
body {
  margin: 0;
  color: var(--ink);
  background: var(--paper);
  font-family: "Segoe UI", Arial, sans-serif;
  line-height: 1.48;
  print-color-adjust: exact;
  -webkit-print-color-adjust: exact;
}

.cover {
  height: 261mm;
  min-height: 261mm;
  margin: 0;
  padding: 36mm 24mm;
  color: #fff;
  background:
    radial-gradient(circle at 88% 12%, rgba(255,90,60,.35), transparent 31%),
    radial-gradient(circle at 10% 92%, rgba(79,124,255,.32), transparent 34%),
    linear-gradient(145deg, #12172d 0%, #0d1122 72%, #20152a 100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.cover h1 {
  margin: 0 0 10mm;
  color: #fff;
  font-size: 40pt;
  letter-spacing: -.8pt;
  border: 0;
}
.cover h2 {
  max-width: 150mm;
  margin: 0 0 4mm;
  padding: 0;
  color: #fff;
  font-size: 25pt;
  border: 0;
}
.cover h3 {
  margin: 0 0 24mm;
  padding: 0;
  color: #ff8068;
  background: none;
  border: 0;
  font-size: 14pt;
  box-shadow: none;
}
.cover p {
  max-width: 140mm;
  color: #cfd5e8;
  font-size: 11.5pt;
}
.cover strong { color: #fff; }

.page-break { break-before: page; height: 0; }

h1, h2, h3 { break-after: avoid; }
h1 {
  color: var(--navy);
  font-size: 27pt;
  line-height: 1.1;
}
h2 {
  margin: 8mm 0 4mm;
  padding-bottom: 2.5mm;
  color: var(--navy);
  border-bottom: .8mm solid var(--orange);
  font-size: 19pt;
  line-height: 1.15;
}
h3 {
  margin: 6mm 0 2.5mm;
  padding: 3.5mm 4mm;
  color: var(--navy);
  background: linear-gradient(90deg, #f1f4fb, #fafbfe);
  border-left: 1.2mm solid var(--blue);
  border-radius: 1.5mm;
  font-size: 12.5pt;
  line-height: 1.25;
}
h4 { color: var(--navy-soft); }

p { margin: 0 0 3mm; }
ul, ol { margin: 1.5mm 0 4mm; padding-left: 6mm; }
li { margin: 1.1mm 0; }
strong { color: #11182b; }
code {
  padding: .25mm 1mm;
  color: #c4321b;
  background: #f3f5fa;
  border-radius: 1mm;
  font-family: Consolas, monospace;
  font-size: 8.8pt;
}
pre {
  padding: 4mm;
  color: #e7ebf7;
  background: var(--navy);
  border-radius: 2mm;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  break-inside: avoid;
}
pre code { padding: 0; color: inherit; background: transparent; }
blockquote {
  margin: 0 0 3mm;
  padding: 2.5mm 4mm;
  color: #303951;
  background: #fff7ed;
  border-left: 1mm solid var(--gold);
  break-inside: avoid;
}
blockquote p { margin: 0; }

table {
  width: 100%;
  margin: 3mm 0 6mm;
  border-collapse: collapse;
  font-size: 8.8pt;
}
thead { display: table-header-group; }
th {
  padding: 2.4mm;
  color: #fff;
  background: var(--navy-soft);
  border: .25mm solid var(--navy-soft);
  text-align: left;
}
td {
  padding: 2.2mm;
  border: .25mm solid var(--line);
  vertical-align: top;
}
tr:nth-child(even) td { background: var(--soft); }
tr { break-inside: avoid; }

.toc {
  columns: 2;
  column-gap: 12mm;
  font-size: 8.6pt;
}
.toc ul { margin: 0; padding-left: 4mm; }
.toc li { break-inside: avoid; margin: .7mm 0; }
.toc a { color: var(--navy-soft); text-decoration: none; }

h3 + blockquote + ul,
h3 + blockquote { break-before: avoid; }
.task {
  break-inside: avoid;
  page-break-inside: avoid;
  margin: 0 0 2mm;
}
.task-grid {
  column-count: 2;
  column-gap: 7mm;
}
.task-grid .task {
  display: inline-block;
  width: 100%;
  margin: 0 0 3mm;
}
.task-grid h3 {
  margin-top: 0;
  padding: 2.5mm 3mm;
  font-size: 10.3pt;
}
.task-grid blockquote {
  padding: 2mm 3mm;
  font-size: 8.2pt;
}
.task-grid ul {
  padding-left: 5mm;
  font-size: 8.1pt;
  line-height: 1.35;
}
.task-grid li { margin: .7mm 0; }
.team-grid {
  columns: 2;
  column-gap: 8mm;
  font-size: 8.5pt;
}
.team-grid li { margin: .5mm 0; break-inside: avoid; }
@media print {
  a { color: inherit; text-decoration: none; }
  p, li { orphans: 3; widows: 3; }
}
"""


def _find_chrome() -> Path:
    candidates = (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate

    executable = shutil.which("chrome") or shutil.which("google-chrome")
    if executable:
        return Path(executable)
    raise RuntimeError("Google Chrome não foi encontrado para gerar o PDF.")


def _render_html() -> str:
    source = SOURCE.read_text(encoding="utf-8")
    body = markdown.markdown(
        source,
        extensions=("extra", "toc", "sane_lists"),
        output_format="html",
    )
    # Cada task precisa viajar como um bloco indivisível no PDF. O Markdown
    # produz h3 + metadados + lista; agrupamos até o próximo título ou seção.
    body = re.sub(
        r"(<h3\b[^>]*>\s*BL-\d{2}.*?</h3>.*?)(?=<h[23]\b|</div>|<div class=\"page-break\"|$)",
        r'<section class="task">\1</section>',
        body,
        flags=re.DOTALL,
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Plano de tarefas — Backend Livre Acesso</title>
<style>{_STYLES}</style>
</head>
<body>
{body}
</body>
</html>
"""


def build_pdf() -> Path:
    if not SOURCE.exists():
        raise RuntimeError(f"Documento-fonte não encontrado: {SOURCE}")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    chrome = _find_chrome()
    OUTPUT.unlink(missing_ok=True)

    with tempfile.TemporaryDirectory(prefix="chrome-", dir=CACHE_DIR) as profile_directory:
        html_path = CACHE_DIR / "backend-task-plan.html"
        html_path.write_text(_render_html(), encoding="utf-8")
        try:
            command = (
                str(chrome),
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-extensions",
                "--allow-file-access-from-files",
                "--no-pdf-header-footer",
                f"--user-data-dir={profile_directory}",
                f"--print-to-pdf={OUTPUT}",
                html_path.as_uri(),
            )
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise RuntimeError("O Chrome não conseguiu renderizar o documento.")
        finally:
            html_path.unlink(missing_ok=True)

    if not OUTPUT.exists() or OUTPUT.stat().st_size < 20_000:
        raise RuntimeError("O PDF gerado está ausente ou incompleto.")
    if not OUTPUT.read_bytes().startswith(b"%PDF-"):
        raise RuntimeError("O arquivo gerado não possui assinatura PDF válida.")
    return OUTPUT


def main() -> int:
    output = build_pdf()
    print(f"PDF gerado: {output}")
    print(f"Tamanho: {output.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
