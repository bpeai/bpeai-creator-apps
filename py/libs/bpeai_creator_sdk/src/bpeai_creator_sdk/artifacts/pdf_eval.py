"""Build a PDF evaluation report from datasheet_markdown (custom-GPT PDF parity)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping


NAVY = (23, 50, 77)
TEAL = (0, 163, 152)
BODY = (31, 41, 55)
GRAY = (107, 114, 128)


def build_evaluation_pdf(
    result: Mapping[str, Any],
    *,
    output_path: Path | str,
    title: str | None = None,
) -> Path:
    """Render ``datasheet_markdown`` (or synthesized fields) to a styled PDF."""
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        HRFlowable,
        KeepTogether,
    )
    from reportlab.lib.colors import Color

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    markdown = (result.get("datasheet_markdown") or "").strip()
    if not markdown:
        markdown = _synthesize_markdown(result)

    system = str(title or result.get("system_name") or result.get("equipment_name") or "Mixing evaluation")
    dir_code = str(result.get("dir_code") or "")

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="EITitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=Color(*[c / 255 for c in NAVY]),
            spaceAfter=6,
            leading=22,
        )
    )
    styles.add(
        ParagraphStyle(
            name="EIH1",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=Color(*[c / 255 for c in NAVY]),
            spaceBefore=14,
            spaceAfter=6,
            leading=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="EIH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=Color(*[c / 255 for c in TEAL]),
            spaceBefore=10,
            spaceAfter=4,
            leading=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="EIBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            textColor=Color(*[c / 255 for c in BODY]),
            leading=13,
            spaceAfter=4,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="EIBullet",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            textColor=Color(*[c / 255 for c in BODY]),
            leading=12.5,
            leftIndent=14,
            bulletIndent=2,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="EIMeta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=Color(*[c / 255 for c in GRAY]),
            spaceAfter=8,
        )
    )

    story = []
    story.append(Paragraph(_escape(system), styles["EITitle"]))
    meta = "Mixing technology evaluation"
    if dir_code:
        meta += f"  ·  Validated DIR: {dir_code}"
    story.append(Paragraph(_escape(meta), styles["EIMeta"]))
    story.append(
        HRFlowable(width="100%", thickness=1.5, color=Color(*[c / 255 for c in TEAL]), spaceAfter=10)
    )

    for block in _markdown_to_flowables(markdown, styles):
        story.append(block)

    def _footer(canvas, doc):  # noqa: ARG001
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(Color(*[c / 255 for c in GRAY]))
        canvas.drawString(0.75 * inch, 0.5 * inch, "BPEAI equipment evaluation · project-team summary")
        canvas.drawRightString(7.75 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(out),
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.75 * inch,
        title=system,
    )
    try:
        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return out
    except PermissionError:
        from datetime import datetime

        stamped = out.with_name(f"{out.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{out.suffix}")
        doc.filename = str(stamped)
        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return stamped


def _escape(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _inline_md(text: str) -> str:
    """Minimal markdown inline → reportlab XML."""
    s = _escape(text)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"<font face='Courier'>\1</font>", s)
    # Autolink bare URLs for readability
    s = re.sub(
        r"(https?://[^\s<]+)",
        r'<link href="\1" color="teal"><u>\1</u></link>',
        s,
    )
    return s


def _markdown_to_flowables(markdown: str, styles):
    from reportlab.platypus import Paragraph, Spacer

    flow = []
    for raw_line in (markdown or "").splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            flow.append(Spacer(1, 4))
            continue
        if line.startswith("---"):
            continue
        if line.startswith("# "):
            flow.append(Paragraph(_inline_md(line[2:].strip()), styles["EIH1"]))
            continue
        if line.startswith("## "):
            flow.append(Paragraph(_inline_md(line[3:].strip()), styles["EIH2"]))
            continue
        if line.startswith("### "):
            flow.append(Paragraph(_inline_md(line[4:].strip()), styles["EIH2"]))
            continue
        bullet = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if bullet:
            flow.append(Paragraph("• " + _inline_md(bullet.group(3)), styles["EIBullet"]))
            continue
        flow.append(Paragraph(_inline_md(line), styles["EIBody"]))
    return flow


def _synthesize_markdown(result: Mapping[str, Any]) -> str:
    parts = [
        f"# {result.get('system_name') or result.get('equipment_name') or 'Evaluation'}",
        f"**DIR:** {result.get('dir_code') or 'n/a'}",
        "",
        "## Recommended basis of design",
        str(result.get("recommended_basis") or result.get("selected_model") or ""),
        "",
        "## Design basis",
        str(result.get("design_basis") or result.get("dir_summary") or ""),
        "",
        "## Rationale",
        str(result.get("rationale") or ""),
    ]
    return "\n".join(parts)
