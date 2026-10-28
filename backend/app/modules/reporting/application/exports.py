"""Exportadores leves, gerados em memória para CSV e PDF."""

import csv
import io
from collections.abc import Iterable


def to_csv(rows: Iterable[dict[str, object]]) -> bytes:
    items = list(rows)
    if not items:
        return b""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(items[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(items)
    return output.getvalue().encode("utf-8-sig")


def to_pdf(title: str, rows: Iterable[dict[str, object]]) -> bytes:
    lines = [title, *(" | ".join(f"{key}: {value}" for key, value in row.items()) for row in rows)]
    escaped = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines]
    content = (
        "BT /F1 10 Tf 50 760 Td " + " ".join(f"({line}) Tj 0 -16 Td" for line in escaped) + " ET"
    )
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        (
            f"<< /Length {len(content.encode('latin-1', errors='replace'))} >>"
            f"\\nstream\\n{content}\\nendstream"
        ),
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\\n{obj}\\nendobj\\n".encode("latin-1", errors="replace"))
    startxref = len(pdf)
    pdf.extend(f"xref\\n0 {len(objects) + 1}\\n0000000000 65535 f \\n".encode())
    pdf.extend("".join(f"{offset:010d} 00000 n \\n" for offset in offsets[1:]).encode())
    trailer = (
        f"trailer\\n<< /Size {len(objects) + 1} /Root 1 0 R >>\\nstartxref\\n{startxref}\\n%%EOF"
    )
    pdf.extend(trailer.encode())
    return bytes(pdf)
