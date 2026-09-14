"""Evaluation report PDF matching the agitator URS writer (DejaVu, navy tables).

Content stays ``datasheet_markdown`` from the evaluate LLM. Layout is Python —
the same split as ``vessel_agitator/urs_pdf.py``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Sequence


NAVY = (31 / 255, 78 / 255, 121 / 255)
BODY = (34 / 255, 34 / 255, 34 / 255)
MUTED = (91 / 255, 103 / 255, 112 / 255)
HEADER_BG = (31 / 255, 78 / 255, 121 / 255)
GRID = (197 / 255, 205 / 255, 212 / 255)
CALLOUT_BG = (232 / 255, 239 / 255, 247 / 255)

_FONT = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_FONT_REG = False

_MD_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$")
_NUM_HEADING_RE = re.compile(r"^(\d+)[.)]\s+(?!\d)(.{2,90})$")
_LABELED_RE = re.compile(
    r"^(?:[-*•]|\d+[.)])\s+(?:\*\*)?([^:*]{2,48})(?:\*\*)?\s*:\s+(.+)$"
)


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


def _color(rgb: tuple[float, float, float]):
    from reportlab.lib.colors import Color

    return Color(*rgb)


def _esc(text: Any) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _inline_md(text: str) -> str:
    s = _esc(text)
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


def _heading_text(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith("---") and not stripped.startswith("|"):
        return None
    if _labeled_bullet(stripped):
        return None
    md = _MD_HEADING_RE.match(stripped)
    if md:
        return (md.group(2) or "").strip() or None
    numbered = _NUM_HEADING_RE.match(stripped)
    if not numbered:
        return None
    title = (numbered.group(2) or "").strip()
    if not title or title.endswith((".", "?", "!")):
        return None
    if len(title.split()) > 12:
        return None
    if not re.match(r"^[A-Z*]", title):
        return None
    return title


def _labeled_bullet(line: str) -> tuple[str, str] | None:
    match = _LABELED_RE.match(line.strip())
    if not match:
        return None
    return match.group(1).strip(), match.group(2).strip()


def _extract_recommendation(result: Mapping[str, Any], markdown: str) -> str:
    rec = str(result.get("recommended_basis") or "").strip()
    if rec and len(rec) > 40:
        return rec
    lines = (markdown or "").splitlines()
    capture = False
    parts: list[str] = []
    for line in lines:
        heading = _heading_text(line)
        if heading:
            if re.search(r"recommend", heading, re.I):
                capture = True
                continue
            if capture:
                break
        if capture and line.strip() and not line.strip().startswith("|"):
            parts.append(line.strip())
            if len(" ".join(parts)) > 80:
                break
    text = " ".join(parts).strip()
    if text:
        return text
    return str(result.get("selected_model") or rec or "").strip()


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


def _table_widths(n: int, usable: float) -> list[float]:
    if n <= 1:
        return [usable]
    if n == 2:
        return [usable * 0.32, usable * 0.68]
    if n == 3:
        return [usable * 0.28, usable * 0.32, usable * 0.40]
    return [usable / n] * n


def write_evaluation_report_pdf(
    result: Mapping[str, Any],
    output_path: Path | str,
    *,
    title: str | None = None,
) -> Path:
    """Render evaluate markdown to a URS-style evaluation report PDF."""
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        KeepTogether,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    font, font_bold = _register_fonts()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    markdown = (result.get("datasheet_markdown") or "").strip()
    if not markdown:
        markdown = _synthesize_markdown(result)

    system = str(
        title or result.get("system_name") or result.get("equipment_name") or "Equipment evaluation"
    ).strip()
    dir_code = str(result.get("dir_code") or "").strip()
    application = str(result.get("application") or "").strip()
    selected = str(result.get("selected_model") or "").strip()
    schema = str(result.get("schema_version") or "")
    kind = (
        "sizing"
        if schema == "equipment_sizing_v1"
        else "technology evaluation"
    )
    subtitle = (
        f"Preliminary {kind} and recommended basis of design"
        + (f" | {application}" if application else "")
    )
    header_title = f"{system} evaluation" + (f" • DIR {dir_code}" if dir_code else "")
    recommendation = _extract_recommendation(result, markdown)

    styles = {
        "title": ParagraphStyle(
            "EITitle",
            fontName=font_bold,
            fontSize=18,
            leading=22,
            textColor=_color(NAVY),
            alignment=TA_CENTER,
            spaceAfter=3,
        ),
        "sub": ParagraphStyle(
            "EISub",
            fontName=font,
            fontSize=9,
            leading=12,
            textColor=_color(MUTED),
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "h": ParagraphStyle(
            "EIH",
            fontName=font_bold,
            fontSize=11,
            leading=14,
            textColor=_color(NAVY),
            spaceBefore=11,
            spaceAfter=4,
        ),
        "h2": ParagraphStyle(
            "EIH2",
            fontName=font_bold,
            fontSize=10,
            leading=13,
            textColor=_color(NAVY),
            spaceBefore=8,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "EIBody",
            fontName=font,
            fontSize=9,
            leading=12,
            textColor=_color(BODY),
            alignment=TA_JUSTIFY,
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "EIBullet",
            fontName=font,
            fontSize=9,
            leading=11.5,
            textColor=_color(BODY),
            leftIndent=12,
            spaceAfter=2,
        ),
        "rec_label": ParagraphStyle(
            "EIRecLabel",
            fontName=font_bold,
            fontSize=8,
            leading=10,
            textColor=_color(NAVY),
            spaceAfter=2,
        ),
        "rec_body": ParagraphStyle(
            "EIRecBody",
            fontName=font,
            fontSize=9,
            leading=12,
            textColor=_color(BODY),
            alignment=TA_LEFT,
        ),
        "th": ParagraphStyle(
            "EITH",
            fontName=font_bold,
            fontSize=8,
            leading=10,
            textColor=_color((1, 1, 1)),
        ),
        "td": ParagraphStyle(
            "EITD",
            fontName=font,
            fontSize=8,
            leading=10.5,
            textColor=_color(BODY),
            alignment=TA_LEFT,
        ),
        "chip": ParagraphStyle(
            "EIChip",
            fontName=font,
            fontSize=8,
            leading=10,
            textColor=_color(NAVY),
            alignment=TA_CENTER,
        ),
    }

    usable = 7.1 * inch

    def add_table(story: list, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
        if not headers or not rows:
            return
        n = len(headers)
        widths = _table_widths(n, usable)
        data = [[Paragraph(_inline_md(h), styles["th"]) for h in headers]]
        for row in rows:
            padded = list(row) + [""] * n
            data.append([Paragraph(_inline_md(padded[i]), styles["td"]) for i in range(n)])
        table = Table(data, colWidths=widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _color(HEADER_BG)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), _color((1, 1, 1))),
                    ("FONTNAME", (0, 0), (-1, 0), font_bold),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.25, _color(GRID)),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 7))

    story: list = []
    story.append(Paragraph(_esc(system), styles["title"]))
    story.append(Paragraph(_esc(subtitle), styles["sub"]))

    chips = [c for c in (
        f"DIR {dir_code}" if dir_code else "",
        application,
        selected,
    ) if c]
    if chips:
        chip_cells = [Paragraph(_esc(c), styles["chip"]) for c in chips]
        chip_w = usable / max(1, len(chips))
        chip_table = Table([chip_cells], colWidths=[chip_w] * len(chips))
        chip_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), _color(CALLOUT_BG)),
                    ("BOX", (0, 0), (-1, -1), 0.4, _color(HEADER_BG)),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, _color(GRID)),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(chip_table)
        story.append(Spacer(1, 8))

    if recommendation:
        rec_inner = [
            [Paragraph("Recommendation in one line", styles["rec_label"])],
            [Paragraph(_inline_md(recommendation), styles["rec_body"])],
        ]
        rec_table = Table(rec_inner, colWidths=[usable])
        rec_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), _color(CALLOUT_BG)),
                    ("BOX", (0, 0), (-1, -1), 0.6, _color(HEADER_BG)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (0, 0), 6),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 7),
                ]
            )
        )
        story.append(KeepTogether([rec_table, Spacer(1, 8)]))

    lines = markdown.splitlines()
    i = 0
    first_heading = True
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if line.startswith("---") and not line.strip().startswith("|"):
            i += 1
            continue
        heading = _heading_text(line)
        if heading:
            # Skip a leading H1 that repeats the system title.
            if first_heading and heading.lower() in {system.lower(), "evaluation"}:
                first_heading = False
                i += 1
                continue
            first_heading = False
            hashes = _MD_HEADING_RE.match(line.strip())
            if hashes and hashes.group(1) in {"##", "###"}:
                style = styles["h2"]
            else:
                style = styles["h"]
            story.append(Paragraph(_inline_md(heading), style))
            i += 1
            continue
        if (
            line.strip().startswith("|")
            and i + 1 < len(lines)
            and _is_table_divider(lines[i + 1])
        ):
            headers = _split_table_row(line)
            rows: list[list[str]] = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not _is_table_divider(lines[i]):
                    rows.append(_split_table_row(lines[i]))
                i += 1
            add_table(story, headers, rows)
            continue
        labeled = _labeled_bullet(line)
        if labeled:
            rows = [list(labeled)]
            i += 1
            while i < len(lines):
                nxt = _labeled_bullet(lines[i])
                if not nxt:
                    break
                rows.append(list(nxt))
                i += 1
            if len(rows) >= 2:
                add_table(story, ("Item", "Basis"), rows)
            else:
                story.append(Paragraph(f"• <b>{_esc(rows[0][0])}:</b> {_inline_md(rows[0][1])}", styles["bullet"]))
            continue
        bullet = re.match(r"^(\s*)([-*•]|\d+\.)\s+(.*)$", line.strip())
        if bullet:
            story.append(Paragraph("• " + _inline_md(bullet.group(3)), styles["bullet"]))
            i += 1
            continue
        story.append(Paragraph(_inline_md(line), styles["body"]))
        i += 1

    def _header_footer(canvas, doc):  # noqa: ARG001
        canvas.saveState()
        canvas.setStrokeColor(_color(GRID))
        canvas.setLineWidth(0.5)
        canvas.line(0.7 * inch, 0.62 * inch, 8.05 * inch, 0.62 * inch)
        canvas.setFillColor(_color(MUTED))
        canvas.setFont(font, 8)
        canvas.drawString(0.7 * inch, 0.42 * inch, header_title[:110])
        canvas.drawRightString(8.05 * inch, 0.42 * inch, f"Page {doc.page}")
        canvas.restoreState()

    pdf = SimpleDocTemplate(
        str(out),
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.7 * inch,
        title=header_title,
        author="BPEAI equipment evaluation",
    )
    try:
        pdf.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
        return out
    except PermissionError:
        from datetime import datetime

        stamped = out.with_name(f"{out.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{out.suffix}")
        pdf.filename = str(stamped)
        pdf.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
        return stamped


def build_evaluation_pdf(
    result: Mapping[str, Any],
    *,
    output_path: Path | str,
    title: str | None = None,
) -> Path:
    """Public SDK entry used by evaluator and sizing templates."""
    return write_evaluation_report_pdf(result, output_path, title=title)
