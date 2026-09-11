"""Build a PDF evaluation report from datasheet_markdown (custom-GPT PDF parity).

Fonts and table formatting match the agitator URS writer (DejaVu Sans). The
section structure stays an evaluation report — not the URS outline.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Sequence


NAVY = (23, 50, 77)
TEAL = (0, 163, 152)
BODY = (31, 41, 55)
GRAY = (107, 114, 128)
HEADER_BG = (31, 78, 121)
GRID = (197, 205, 212)

_FONT = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_FONT_REG = False


def _register_fonts() -> tuple[str, str]:
    global _FONT, _FONT_BOLD, _FONT_REG
    if _FONT_REG:
        return _FONT, _FONT_BOLD
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    here = Path(__file__).resolve().parent / "fonts"
    dejavu = here / "DejaVuSans.ttf"
    dejavu_b = here / "DejaVuSans-Bold.ttf"
    calibri = Path(r"C:\Windows\Fonts\calibri.ttf")
    calibri_b = Path(r"C:\Windows\Fonts\calibrib.ttf")
    try:
        if dejavu.is_file() and dejavu_b.is_file():
            pdfmetrics.registerFont(TTFont("EISans", str(dejavu)))
            pdfmetrics.registerFont(TTFont("EISans-Bold", str(dejavu_b)))
            _FONT, _FONT_BOLD = "EISans", "EISans-Bold"
        elif calibri.is_file() and calibri_b.is_file():
            pdfmetrics.registerFont(TTFont("EISans", str(calibri)))
            pdfmetrics.registerFont(TTFont("EISans-Bold", str(calibri_b)))
            _FONT, _FONT_BOLD = "EISans", "EISans-Bold"
    except Exception:
        _FONT, _FONT_BOLD = "Helvetica", "Helvetica-Bold"
    _FONT_REG = True
    return _FONT, _FONT_BOLD


def _color(rgb: tuple[int, int, int]):
    from reportlab.lib.colors import Color

    return Color(*[c / 255 for c in rgb])


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
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

    font, font_bold = _register_fonts()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    markdown = (result.get("datasheet_markdown") or "").strip()
    if not markdown:
        markdown = _synthesize_markdown(result)

    system = str(title or result.get("system_name") or result.get("equipment_name") or "Equipment evaluation")
    dir_code = str(result.get("dir_code") or "")
    schema = str(result.get("schema_version") or "")
    meta = (
        "Equipment sizing"
        if schema == "equipment_sizing_v1"
        else "Equipment technology evaluation"
    )
    if dir_code:
        meta += f"  ·  Validated DIR: {dir_code}"

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="EITitle",
            parent=styles["Heading1"],
            fontName=font_bold,
            fontSize=18,
            textColor=_color(NAVY),
            spaceAfter=6,
            leading=22,
        )
    )
    styles.add(
        ParagraphStyle(
            name="EIH1",
            parent=styles["Heading1"],
            fontName=font_bold,
            fontSize=13,
            textColor=_color(NAVY),
            spaceBefore=14,
            spaceAfter=6,
            leading=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="EIH2",
            parent=styles["Heading2"],
            fontName=font_bold,
            fontSize=11,
            textColor=_color(TEAL),
            spaceBefore=10,
            spaceAfter=4,
            leading=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="EIBody",
            parent=styles["BodyText"],
            fontName=font,
            fontSize=9.5,
            textColor=_color(BODY),
            leading=13,
            spaceAfter=4,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="EIBullet",
            parent=styles["BodyText"],
            fontName=font,
            fontSize=9.5,
            textColor=_color(BODY),
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
            fontName=font,
            fontSize=9,
            textColor=_color(GRAY),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="EITH",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=8,
            leading=10,
            textColor=_color((255, 255, 255)),
        )
    )
    styles.add(
        ParagraphStyle(
            name="EITD",
            parent=styles["Normal"],
            fontName=font,
            fontSize=8,
            leading=10.5,
            textColor=_color(BODY),
        )
    )

    story = []
    story.append(Paragraph(_escape(system), styles["EITitle"]))
    story.append(Paragraph(_escape(meta), styles["EIMeta"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_color(TEAL), spaceAfter=10))
    story.extend(_markdown_to_flowables(markdown, styles, font=font, font_bold=font_bold))

    def _footer(canvas, doc):  # noqa: ARG001
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(_color(GRAY))
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
    s = re.sub(
        r"(https?://[^\s<]+)",
        r'<link href="\1" color="teal"><u>\1</u></link>',
        s,
    )
    return s


def _split_table_row(line: str) -> list[str]:
    raw = line.strip().strip("|")
    return [cell.strip() for cell in raw.split("|")]


def _is_table_divider(line: str) -> bool:
    cells = _split_table_row(line)
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells if cell)


def _make_table(headers: Sequence[str], rows: Sequence[Sequence[str]], styles, *, font: str, font_bold: str):
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, Table, TableStyle

    usable = 6.5 * inch
    n = max(1, len(headers))
    widths = [usable / n] * n
    data = [[Paragraph(_inline_md(h), styles["EITH"]) for h in headers]]
    for row in rows:
        padded = list(row) + [""] * n
        data.append([Paragraph(_inline_md(padded[i]), styles["EITD"]) for i in range(n)])
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _color(HEADER_BG)),
                ("FONTNAME", (0, 0), (-1, 0), font_bold),
                ("FONTNAME", (0, 1), (-1, -1), font),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, _color(GRID)),
            ]
        )
    )
    return table


def _markdown_to_flowables(markdown: str, styles, *, font: str, font_bold: str):
    from reportlab.platypus import Paragraph, Spacer

    flow = []
    lines = (markdown or "").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            flow.append(Spacer(1, 4))
            i += 1
            continue
        if line.startswith("---") and not line.strip().startswith("|"):
            i += 1
            continue
        if (
            line.strip().startswith("|")
            and i + 1 < len(lines)
            and _is_table_divider(lines[i + 1])
        ):
            headers = _split_table_row(line)
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not _is_table_divider(lines[i]):
                    rows.append(_split_table_row(lines[i]))
                i += 1
            flow.append(_make_table(headers, rows, styles, font=font, font_bold=font_bold))
            flow.append(Spacer(1, 8))
            continue
        if line.startswith("# "):
            flow.append(Paragraph(_inline_md(line[2:].strip()), styles["EIH1"]))
            i += 1
            continue
        if line.startswith("## "):
            flow.append(Paragraph(_inline_md(line[3:].strip()), styles["EIH2"]))
            i += 1
            continue
        if line.startswith("### "):
            flow.append(Paragraph(_inline_md(line[4:].strip()), styles["EIH2"]))
            i += 1
            continue
        bullet = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if bullet:
            flow.append(Paragraph("• " + _inline_md(bullet.group(3)), styles["EIBullet"]))
            i += 1
            continue
        flow.append(Paragraph(_inline_md(line), styles["EIBody"]))
        i += 1
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
