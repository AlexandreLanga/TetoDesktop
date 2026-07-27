"""Geração do relatório PDF."""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image as PdfImage
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_pdf(target: Path, payload: dict, annotated_paths: list[Path]) -> None:
    """Gera um relatório em PDF usando o resultado e as imagens anotadas."""
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        str(target), pagesize=A4, rightMargin=1.5 * cm, leftMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    result = payload.get("result", {})
    condition = result.get("roof_condition", {})
    maintenance = result.get("maintenance", {})
    story = [Paragraph("Relatório de Análise de Telhado", styles["Title"]), Spacer(1, 0.35 * cm)]
    story.append(Paragraph(f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}", styles["Normal"]))
    story += [Spacer(1, 0.3 * cm), Paragraph("Condição geral", styles["Heading2"])]

    data = [
        ["Pontuação", str(condition.get("score", "—"))],
        ["Classificação", str(condition.get("classification", "—"))],
        ["Prioridade", str(maintenance.get("priority", "—"))],
        ["Risco de vazamento", str(maintenance.get("risk_of_leak", "—"))],
        ["Risco estrutural", str(maintenance.get("structural_risk", "—"))],
    ]
    table = Table(data, colWidths=[5 * cm, 10 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8eef5")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [
        table,
        Spacer(1, 0.3 * cm),
        Paragraph(escape(str(condition.get("summary", ""))), styles["BodyText"]),
        Spacer(1, 0.35 * cm),
        Paragraph("Problemas identificados", styles["Heading2"]),
    ]

    for number, issue in enumerate(result.get("issues", []), 1):
        story.append(Paragraph(
            f"{number}. {escape(str(issue.get('type', 'Problema')))} "
            f"({escape(str(issue.get('severity', '—')))})",
            styles["Heading3"],
        ))
        for label, key in [
            ("Local", "location"), ("Descrição", "description"),
            ("Possível causa", "possible_cause"),
            ("Possível consequência", "possible_consequence"),
            ("Recomendação", "recommendation"),
        ]:
            story.append(Paragraph(
                f"<b>{label}:</b> {escape(str(issue.get(key, '—')))}",
                styles["BodyText"],
            ))
        story.append(Spacer(1, 0.18 * cm))

    if result.get("limitations"):
        story += [Paragraph("Limitações", styles["Heading2"])]
        story.extend(
            Paragraph(f"• {escape(str(value))}", styles["BodyText"])
            for value in result["limitations"]
        )
    _append_annotated_images(story, styles, annotated_paths)
    doc.build(story)


def _append_annotated_images(story: list, styles: dict, annotated_paths: list[Path]) -> None:
    if not annotated_paths:
        return
    story += [
        PageBreak(),
        Paragraph("Imagens com áreas destacadas", styles["Heading2"]),
        Paragraph(
            "As áreas coloridas correspondem aos problemas listados neste relatório, "
            "na mesma ordem em que foram retornados pela análise.",
            styles["BodyText"],
        ),
        Spacer(1, 0.25 * cm),
    ]
    for index, path in enumerate(annotated_paths, 1):
        with Image.open(path) as image:
            ratio = min(16 * cm / image.width, 20 * cm / image.height)
            display_width = image.width * ratio
            display_height = image.height * ratio
        story += [
            Paragraph(f"Imagem {index} — áreas identificadas", styles["Heading3"]),
            Spacer(1, 0.12 * cm),
            PdfImage(str(path), width=display_width, height=display_height),
            Spacer(1, 0.35 * cm),
        ]
