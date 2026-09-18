"""Evaluation report PDF matching the agitator URS writer (DejaVu, navy tables).

Content stays ``datasheet_markdown`` from the evaluate LLM. Layout is Python —
the same split as ``vessel_agitator/urs_pdf.py``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Sequence


from .names import evaluation_display_title

NAVY = (31 / 255, 78 / 255, 121 / 255)
BODY = (34 / 255, 34 / 255, 34 / 255)
MUTED = (91 / 255, 103 / 255, 112 / 255)
HEADER_BG = (31 / 255, 78 / 255, 121 / 255)
GRID = (197 / 255, 205 / 255, 212 / 255)
ROW_ALT = (245 / 255, 248 / 255, 252 / 255)
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


_KEEP_TAG_RE = re.compile(
    r"</?(?:b|i|u|br|super|sub|strike)\s*/?>"
    r"|<font\b[^<>]*>|</font>"
    r"|<link\b[^<>]*>|</link>",
    re.IGNORECASE,
)


def _inline_md(text: str) -> str:
    s = str(text or "")
    kept: list[str] = []

    def _stash(match: re.Match[str]) -> str:
        kept.append(match.group(0))
        return f"\x00TAG{len(kept) - 1}\x00"

    s = _KEEP_TAG_RE.sub(_stash, s)
    s = _esc(s)
    for i, tag in enumerate(kept):
        if re.fullmatch(r"<br\s*/?>", tag, re.I):
            restored = "<br/>"
        elif re.fullmatch(r"</?(?:b|i|u)>", tag, re.I):
            restored = tag.lower()
        else:
            restored = tag
        s = s.replace(f"\x00TAG{i}\x00", restored)
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
        "## Design basis from DIR code",
        str(result.get("design_basis") or result.get("dir_summary") or ""),
        "",
        "## Rationale",
        str(result.get("rationale") or ""),
    ]
    return "\n".join(parts)


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, Mapping):
            text = str(item.get("text") or item.get("name") or item.get("value") or "").strip()
        else:
            text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _eval_options(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = result.get("evaluation_options") or result.get("mixing_options") or []
    if not isinstance(raw, list):
        return []
    return [row for row in raw if isinstance(row, Mapping)]


def _decoded_rows(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = result.get("decoded_dir") or []
    if not isinstance(raw, list):
        return []
    return [row for row in raw if isinstance(row, Mapping)]


def _has_structured_eval(result: Mapping[str, Any]) -> bool:
    return bool(
        _eval_options(result)
        or result.get("evaluation_matrix")
        or _decoded_rows(result)
        or _as_str_list(result.get("objectives"))
        or _as_str_list(result.get("failure_modes"))
    )


def _item_noun(result: Mapping[str, Any]) -> str:
    item = str(result.get("evaluated_item") or "").strip()
    if item:
        return item
    category = str(result.get("equipment_category") or "").strip()
    if category:
        return category.lower()
    return "equipment"


def _markdown_section(markdown: str, *needles: str) -> str:
    if not markdown:
        return ""
    lines = markdown.splitlines()
    capture = False
    parts: list[str] = []
    lowered = tuple(n.lower() for n in needles)
    for line in lines:
        heading = _heading_text(line)
        if heading:
            hit = any(n in heading.lower() for n in lowered)
            if capture and not hit:
                break
            capture = hit
            continue
        if capture:
            parts.append(line)
    return "\n".join(parts).strip()


def _table_widths(n: int, usable: float, headers: Sequence[str] | None = None) -> list[float]:
    blob = " ".join(str(h or "").lower() for h in (headers or []))
    if n == 3 and "step" in blob and "objective" in blob:
        return [usable * 0.14, usable * 0.38, usable * 0.48]
    if n <= 1:
        return [usable]
    if n == 2:
        return [usable * 0.32, usable * 0.68]
    if n == 3:
        return [usable * 0.28, usable * 0.32, usable * 0.40]
    if n == 5:
        return [usable * 0.22, usable * 0.18, usable * 0.18, usable * 0.16, usable * 0.26]
    if n == 6:
        return [usable * 0.24, usable * 0.14, usable * 0.14, usable * 0.14, usable * 0.12, usable * 0.22]
    if n == 7:
        first = usable * 0.20
        rest = (usable - first) / 6
        return [first] + [rest] * 6
    return [usable / n] * n


def _split_labeled(text: str) -> tuple[str, str]:
    raw = str(text or "").strip()
    for sep in (" — ", " – ", ": ", " - "):
        if sep in raw:
            left, right = raw.split(sep, 1)
            if 1 <= len(left.split()) <= 8:
                return left.strip(), right.strip()
    return raw, ""


def _fit_position(fit: str) -> str:
    key = str(fit or "").strip().lower().replace("_", "-")
    return {
        "best": "Basis of design",
        "strong": "Second-source / robust backup",
        "conditional": "Conditional",
        "limited": "Limited",
        "add-on": "Add-on",
        "addon": "Add-on",
        "special-case": "Special case",
    }.get(key, str(fit or "").replace("-", " ").title() or "—")


def _rating_dots(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "—"
    if set(raw.replace(" ", "")) <= set("●○•*"):
        return raw
    token = raw.lower().replace("_", " ").replace("-", " ")
    mapping = {
        "best": 5,
        "very high": 5,
        "excellent": 5,
        "high": 4,
        "strong": 4,
        "medium high": 4,
        "medium": 3,
        "conditional": 3,
        "moderate": 3,
        "low medium": 2,
        "limited": 2,
        "fair": 2,
        "low": 1,
        "poor": 1,
        "weak": 1,
    }
    n = mapping.get(token)
    if n is None:
        return raw
    return ("●" * n) + ("○" * (5 - n))


def _header_blob(headers: Sequence[str]) -> str:
    return " ".join(str(h or "").lower() for h in headers)


def _is_step_objective_control_table(headers: Sequence[str]) -> bool:
    """True when a markdown table is Step / Objective / Key control (not DIR or exclusions)."""
    if len(headers) < 2:
        return False
    blob = _header_blob(headers)
    if "objective" not in blob:
        return False
    if any(bad in blob for bad in ("dir element", "technology", "selected basis", "reason not")):
        return False
    return "control" in blob or "step" in blob or "detail" in blob


def _split_tech_reason(text: str) -> tuple[str, str]:
    """Split 'Technology: reason' without the short-label limit used for objectives."""
    raw = str(text or "").strip()
    if not raw:
        return "", ""
    for sep in (": ", " — ", " – ", " - ", ":"):
        if sep in raw:
            left, right = raw.split(sep, 1)
            left, right = left.strip().strip("-*• "), right.strip()
            if left and right:
                return left, right
    return raw, ""


def _is_technology_reason_table(headers: Sequence[str]) -> bool:
    if len(headers) < 2:
        return False
    blob = _header_blob(headers)
    if any(bad in blob for bad in ("dir element", "selected basis", "step", "objective", "specification")):
        return False
    has_tech = any(tok in blob for tok in ("technology", "type", "option", "pump", "equipment"))
    has_reason = any(
        tok in blob for tok in ("reason", "why", "not primary", "not evaluated", "rationale")
    )
    return has_tech and has_reason


def _exclusion_pair(item: Any) -> tuple[str, str]:
    if isinstance(item, Mapping):
        tech = str(
            item.get("technology")
            or item.get("name")
            or item.get("type")
            or item.get("option")
            or ""
        ).strip()
        reason = str(
            item.get("reason") or item.get("why") or item.get("detail") or item.get("value") or ""
        ).strip()
        if tech:
            return tech, reason
        text = str(item.get("text") or "").strip()
        return _split_tech_reason(text) if text else ("", "")
    return _split_tech_reason(str(item or ""))


def _coerce_exclusion_rows(
    headers: Sequence[str], rows: Sequence[Sequence[str]]
) -> list[list[str]]:
    if _is_technology_reason_table(headers):
        tech_i = _column_index(headers, "technology", "type", "option", "pump", "equipment") or 0
        reason_i = _column_index(
            headers, "reason", "why", "not primary", "not evaluated", "rationale"
        )
        if reason_i is None:
            reason_i = 1 if len(headers) > 1 else 0
        out: list[list[str]] = []
        for row in rows:
            cells = list(row) + [""] * 3
            tech = str(cells[tech_i] or "").strip()
            reason = str(cells[reason_i] or "").strip() if reason_i != tech_i else ""
            if not reason:
                tech, reason = _split_tech_reason(tech)
            if tech:
                out.append([tech, reason])
        return out
    if len(headers) == 1:
        out = []
        for row in rows:
            tech, reason = _split_tech_reason(str(row[0] if row else ""))
            if tech:
                out.append([tech, reason])
        if any(reason for _tech, reason in out):
            return out
    return []


def _exclusion_rows(section: str, excluded: Sequence[Any]) -> list[list[str]]:
    for headers, rows in _iter_md_tables(section):
        coerced = _coerce_exclusion_rows(headers, rows)
        if coerced:
            return coerced
    out: list[list[str]] = []
    for item in excluded:
        tech, reason = _exclusion_pair(item)
        if tech:
            out.append([tech, reason])
    return out


def _column_index(headers: Sequence[str], *needles: str) -> int | None:
    lowered = [str(h or "").lower() for h in headers]
    for needle in needles:
        for i, header in enumerate(lowered):
            if needle in header:
                return i
    return None


def _coerce_objective_rows(
    headers: Sequence[str], rows: Sequence[Sequence[str]]
) -> list[list[str]]:
    step_i = _column_index(headers, "step")
    obj_i = _column_index(headers, "objective", "action", "title")
    ctrl_i = _column_index(headers, "control", "detail", "how")
    if obj_i is None:
        obj_i = 1 if len(headers) > 1 else 0
    if ctrl_i is None:
        ctrl_i = 2 if len(headers) > 2 else (1 if obj_i == 0 and len(headers) > 1 else obj_i)
    out: list[list[str]] = []
    for i, row in enumerate(rows, start=1):
        cells = list(row) + [""] * 4
        step = str(cells[step_i] if step_i is not None else i).strip() or str(i)
        num = re.match(r"^(\d+)\.?\s*$", step)
        step_out = num.group(1) if num else (str(i) if step_i is None else step)
        objective = str(cells[obj_i] or "").strip()
        control = str(cells[ctrl_i] or "").strip() if ctrl_i != obj_i else ""
        if objective:
            out.append([step_out, objective, control])
    return out


def _process_steps_from_result(result: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    if not isinstance(result, Mapping):
        return []
    raw = result.get("process_steps")
    if isinstance(raw, list):
        steps = [row for row in raw if isinstance(row, Mapping) and (row.get("title") or row.get("detail"))]
        if steps:
            return steps
    slides = result.get("slides")
    if not isinstance(slides, list):
        pack = result.get("pptx") or result.get("slide_pack")
        slides = pack.get("slides") if isinstance(pack, Mapping) else []
    for slide in slides or []:
        if not isinstance(slide, Mapping):
            continue
        sid = str(slide.get("id") or slide.get("heading") or "").lower()
        if "objective" not in sid and "failure" not in sid:
            continue
        steps = [row for row in (slide.get("process_steps") or []) if isinstance(row, Mapping)]
        if steps:
            return steps
    return []


def _objective_rows(
    section: str,
    objectives: Sequence[str],
    result: Mapping[str, Any] | None = None,
) -> list[list[str]]:
    for headers, rows in _iter_md_tables(section):
        if _is_step_objective_control_table(headers):
            coerced = _coerce_objective_rows(headers, rows)
            if coerced:
                return coerced
    steps = _process_steps_from_result(result)
    if steps:
        out: list[list[str]] = []
        for i, step in enumerate(steps, start=1):
            title = str(step.get("title") or step.get("objective") or "").strip()
            detail = str(step.get("detail") or step.get("control") or step.get("key_control") or "").strip()
            if title or detail:
                out.append([str(step.get("n") or i), title, detail])
        if out:
            return out
    out = []
    for idx, obj in enumerate(objectives, start=1):
        left, right = _split_labeled(obj)
        if right:
            out.append([str(idx), left, right])
        elif str(obj).strip():
            out.append([str(idx), str(obj).strip(), ""])
    return out


def _iter_md_tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    tables: list[tuple[list[str], list[list[str]]]] = []
    lines = (text or "").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
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
            if headers and rows:
                tables.append((headers, rows))
            continue
        i += 1
    return tables


def _extract_md_table(text: str) -> tuple[list[str], list[list[str]]] | None:
    tables = _iter_md_tables(text)
    return tables[0] if tables else None


def _section_intro(text: str) -> str:
    parts: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            break
        if not stripped or stripped.startswith(("#", "-", "*", "•")):
            continue
        if _NUM_HEADING_RE.match(stripped) or _MD_HEADING_RE.match(stripped):
            continue
        parts.append(stripped)
    return " ".join(parts)


def _key_spec_pairs(result: Mapping[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for spec in result.get("key_specs") or []:
        if isinstance(spec, Mapping):
            label = str(spec.get("key") or "").strip()
            value = str(spec.get("value") or "").strip()
        else:
            label, value = _split_labeled(str(spec or ""))
        if label:
            out.append((label, value))
        if len(out) >= 4:
            break
    return out


def write_evaluation_report_pdf(
    result: Mapping[str, Any],
    output_path: Path | str,
    *,
    title: str | None = None,
) -> Path:
    """Render evaluate markdown to a URS-style evaluation report PDF."""
    from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
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

    display_title = (title or "").strip() or evaluation_display_title(result)
    system = display_title
    dir_code = str(result.get("dir_code") or "").strip()
    application = str(result.get("application") or "").strip()
    selected = str(result.get("selected_model") or "").strip()
    item_noun = _item_noun(result)
    if str(result.get("schema_version") or "") == "equipment_sizing_v1":
        subtitle = f"Preliminary {item_noun} sizing and recommended basis of design"
    else:
        subtitle = f"Preliminary {item_noun}-system option evaluation and recommended basis of design"
    header_title = display_title
    if dir_code:
        header_title += f" • Basis: user DIR code {dir_code}"
    recommendation = _extract_recommendation(result, markdown)

    styles = {
        "title": ParagraphStyle(
            "EITitle",
            fontName=font_bold,
            fontSize=18,
            leading=22,
            textColor=_color(NAVY),
            alignment=TA_LEFT,
            spaceAfter=3,
        ),
        "sub": ParagraphStyle(
            "EISub",
            fontName=font,
            fontSize=9,
            leading=12,
            textColor=_color(MUTED),
            alignment=TA_LEFT,
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
        "chip_label": ParagraphStyle(
            "EIChipLabel",
            fontName=font_bold,
            fontSize=8,
            leading=10,
            textColor=_color(NAVY),
            alignment=TA_LEFT,
        ),
        "chip_value": ParagraphStyle(
            "EIChipValue",
            fontName=font,
            fontSize=7.5,
            leading=9.5,
            textColor=_color(MUTED),
            alignment=TA_LEFT,
        ),
    }

    usable = 7.1 * inch

    def add_table(story: list, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
        if not headers or not rows:
            return
        n = len(headers)
        widths = _table_widths(n, usable, headers)
        data = [[Paragraph(_inline_md(h), styles["th"]) for h in headers]]
        for row in rows:
            padded = list(row) + [""] * n
            data.append([Paragraph(_inline_md(padded[i]), styles["td"]) for i in range(n)])
        table = Table(data, colWidths=widths, repeatRows=1)
        commands = [
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
        for idx in range(1, len(data)):
            if idx % 2 == 0:
                commands.append(("BACKGROUND", (0, idx), (-1, idx), _color(ROW_ALT)))
        table.setStyle(TableStyle(commands))
        story.append(table)
        story.append(Spacer(1, 7))

    def add_label_table(story: list, rows: Sequence[Sequence[str]]) -> None:
        if not rows:
            return
        widths = [usable * 0.28, usable * 0.72]
        data = [
            [
                Paragraph(_inline_md(str(row[0])), styles["th"]),
                Paragraph(_inline_md(str(row[1]) if len(row) > 1 else ""), styles["td"]),
            ]
            for row in rows
        ]
        table = Table(data, colWidths=widths)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), _color(HEADER_BG)),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("BOX", (0, 0), (-1, -1), 0.4, _color(GRID)),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.25, _color(GRID)),
                    ("BACKGROUND", (1, 0), (1, -1), _color((1, 1, 1))),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 8))

    def add_md_table_or(story: list, section: str, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> bool:
        parsed = _extract_md_table(section)
        if parsed:
            add_table(story, parsed[0], parsed[1])
            return True
        if headers and rows:
            add_table(story, headers, rows)
            return True
        return False

    story: list = []
    story.append(Paragraph(_esc(system), styles["title"]))
    story.append(Paragraph(_esc(subtitle), styles["sub"]))

    attr_pairs = _key_spec_pairs(result)
    if attr_pairs:
        attr_w = usable / len(attr_pairs)
        attr_cells = []
        for label, value in attr_pairs:
            attr_cells.append(
                [
                    Paragraph(_esc(label), styles["chip_label"]),
                    Paragraph(_esc(value), styles["chip_value"]),
                ]
            )
        # Flatten to one row of stacked label/value cells.
        top = [cell[0] for cell in attr_cells]
        bottom = [cell[1] for cell in attr_cells]
        attr_table = Table([top, bottom], colWidths=[attr_w] * len(attr_pairs))
        attr_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), _color((1, 1, 1))),
                    ("BOX", (0, 0), (-1, -1), 0.4, _color(GRID)),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, _color(GRID)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, 0), 5),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(attr_table)
        story.append(Spacer(1, 6))

    meta_cells = [c for c in (
        f"Validated DIR: {dir_code}" if dir_code else "",
        f"Application assumption: {application}" if application else "",
    ) if c]
    if meta_cells:
        meta_w = usable / len(meta_cells)
        meta_table = Table(
            [[Paragraph(_esc(c), styles["chip_label"]) for c in meta_cells]],
            colWidths=[meta_w] * len(meta_cells),
        )
        meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), _color(CALLOUT_BG)),
                    ("BOX", (0, 0), (-1, -1), 0.4, _color(HEADER_BG)),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, _color(GRID)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(meta_table)
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

    def _bullets(values: Sequence[str]) -> str:
        return "<br/>".join(f"• {_inline_md(v)}" for v in values if str(v).strip())

    def _append_structured_report() -> None:
        decoded = _decoded_rows(result)
        options = _eval_options(result)
        matrix = [
            row for row in (result.get("evaluation_matrix") or []) if isinstance(row, Mapping)
        ]
        n = 1
        implication_label = "Mixing implication" if item_noun == "mixing" else "Implication"
        basis_md = _markdown_section(markdown, "design basis from dir")
        if decoded or _extract_md_table(basis_md):
            story.append(Paragraph(f"{n}. Design basis from DIR code", styles["h"]))
            n += 1
            intro = _section_intro(basis_md)
            if intro:
                story.append(Paragraph(_inline_md(intro), styles["body"]))
            basis_rows = []
            unknown_any = False
            for row in decoded:
                unknown = bool(row.get("unknown"))
                unknown_any = unknown_any or unknown
                selected = str(row.get("option_text") or row.get("value") or "")
                implication = str(row.get("implication") or row.get("mixing_implication") or "")
                if unknown and not implication:
                    implication = (
                        "Assume the most likely industrial case for this duty; "
                        "confirm when project data exist."
                    )
                basis_rows.append(
                    [
                        str(row.get("label") or ""),
                        selected,
                        implication,
                    ]
                )
            if unknown_any and not intro:
                story.append(
                    Paragraph(
                        "Unknown / TBD selections are not yet defined by project engineering. "
                        "The evaluation assumes the most likely case and states consequences.",
                        styles["body"],
                    )
                )
            add_md_table_or(
                story,
                basis_md,
                ("DIR element", "Selected basis", implication_label),
                basis_rows,
            )
        objectives = _as_str_list(result.get("objectives"))
        failures = _as_str_list(result.get("failure_modes"))
        obj_md = _markdown_section(markdown, "objectives and failure")
        obj_rows = _objective_rows(obj_md, objectives, result)
        if obj_rows or failures:
            story.append(
                Paragraph(f"{n}. {item_noun.title()} objectives and failure modes", styles["h"])
            )
            n += 1
            if obj_rows:
                add_table(story, ("Step", "Objective", "Key control"), obj_rows)
            if failures:
                story.append(
                    Paragraph(
                        "<b>Failure modes:</b> " + _inline_md("; ".join(failures)),
                        styles["body"],
                    )
                )
        practice_md = _markdown_section(markdown, "industry best practice")
        if practice_md:
            story.append(
                Paragraph(f"{n}. Industry best practice for this duty", styles["h"])
            )
            n += 1
            intro = _section_intro(practice_md)
            if intro:
                story.append(Paragraph(_inline_md(intro), styles["body"]))
        short_md = _markdown_section(
            markdown, "best-fit", "strong-fit", "system shortlist"
        )
        if options or matrix or _extract_md_table(short_md):
            story.append(
                Paragraph(f"{n}. Best-fit {item_noun}-system shortlist", styles["h"])
            )
            n += 1
            intro = _section_intro(short_md)
            if intro:
                story.append(Paragraph(_inline_md(intro), styles["body"]))
            short_rows = []
            by_name = {
                str(row.get("option") or "").strip().lower(): row
                for row in matrix
            }
            for opt in options:
                name = str(opt.get("name") or "Option")
                fit = str(opt.get("fit") or "").replace("_", "-")
                mrow = by_name.get(name.lower(), {})
                short_rows.append(
                    [
                        name,
                        _rating_dots(mrow.get("technical_fit") or fit),
                        _rating_dots(mrow.get("gmp") or ""),
                        _rating_dots(mrow.get("scale_up_risk") or ""),
                        str(fit or "").replace("-", " ").title() or "—",
                        _fit_position(fit),
                    ]
                )
            if not short_rows:
                for row in matrix:
                    short_rows.append(
                        [
                            str(row.get("option") or ""),
                            _rating_dots(row.get("technical_fit") or ""),
                            _rating_dots(row.get("gmp") or ""),
                            _rating_dots(row.get("scale_up_risk") or ""),
                            str(row.get("reliability") or row.get("rank") or ""),
                            "",
                        ]
                    )
            add_md_table_or(
                story,
                short_md,
                ("Option", "Technical fit", "GMP / hygienic", "Scale-up risk", "Fit", "Position"),
                short_rows,
            )
        if options:
            story.append(Paragraph(f"{n}. Option evaluation", styles["h"]))
            n += 1
            for idx, opt in enumerate(options, start=1):
                name = str(opt.get("name") or f"Option {idx}")
                story.append(Paragraph(f"{idx}. {_esc(name)}", styles["h2"]))
                apps = _as_str_list(opt.get("industrial_applications"))
                if apps:
                    story.append(
                        Paragraph(
                            "<b>Industrial applications:</b> " + _inline_md("; ".join(apps)),
                            styles["body"],
                        )
                    )
                rows = []
                pros = _as_str_list(opt.get("pros"))
                cons = _as_str_list(opt.get("cons"))
                mfrs = _as_str_list(opt.get("manufacturers"))
                if pros:
                    rows.append(["Pros", _bullets(pros)])
                if cons:
                    rows.append(["Cons / watchouts", _bullets(cons)])
                if mfrs:
                    rows.append(["Manufacturers", _inline_md("; ".join(mfrs))])
                if rows:
                    add_label_table(story, rows)
        rec_basis = str(result.get("recommended_basis") or selected or "").strip()
        specs = _as_str_list(result.get("preliminary_specs"))
        spec_md = _markdown_section(
            markdown, "recommended preliminary", "preliminary specification", "preliminary basis"
        )
        if rec_basis or specs or _extract_md_table(spec_md):
            story.append(Paragraph(f"{n}. Recommended preliminary basis of design", styles["h"]))
            n += 1
            if rec_basis:
                selected_box = Table(
                    [[Paragraph(f"<b>Selected basis:</b> {_inline_md(rec_basis)}", styles["rec_body"])]],
                    colWidths=[usable],
                )
                selected_box.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), _color(CALLOUT_BG)),
                            ("BOX", (0, 0), (-1, -1), 0.4, _color(HEADER_BG)),
                            ("LEFTPADDING", (0, 0), (-1, -1), 8),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ]
                    )
                )
                story.append(selected_box)
                story.append(Spacer(1, 6))
            intro = _section_intro(spec_md)
            if intro:
                story.append(Paragraph(_inline_md(intro), styles["body"]))
            alt = str(result.get("alternate_basis") or "").strip()
            if alt:
                story.append(Paragraph("<b>Alternate:</b> " + _inline_md(alt), styles["body"]))
            spec_rows = []
            for spec in specs:
                key, val = _split_labeled(spec)
                spec_rows.append([key, val or spec])
            add_md_table_or(
                story,
                spec_md,
                ("Specification item", "Preliminary basis"),
                spec_rows,
            )
        recipe = _markdown_section(markdown, "operating recipe", "qualification")
        if recipe:
            story.append(Paragraph(f"{n}. Suggested operating recipe for qualification", styles["h"]))
            n += 1
            for line in recipe.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("|") and not _heading_text(stripped):
                    story.append(Paragraph(_inline_md(stripped.lstrip("-* ")), styles["bullet"]))
        excluded_raw = result.get("do_not_specify")
        excluded = excluded_raw if isinstance(excluded_raw, list) else _as_str_list(excluded_raw)
        excl_md = _markdown_section(
            markdown, "not recommended", "do not specify"
        )
        excl_rows = _exclusion_rows(excl_md, excluded)
        if excl_rows:
            story.append(Paragraph(f"{n}. Options not recommended as primary basis", styles["h"]))
            n += 1
            add_table(
                story,
                ("Technology", "Reason not primary for this DIR"),
                excl_rows,
            )
        matrix_md = _markdown_section(markdown, "evaluation matrix", "option evaluation matrix")
        if matrix or _extract_md_table(matrix_md):
            story.append(Paragraph(f"{n}. Preliminary option evaluation matrix", styles["h"]))
            n += 1
            add_md_table_or(
                story,
                matrix_md,
                ("Option", "Technical fit", "GMP / cleanability", "Scale-up risk", "Cost / schedule", "Overall"),
                [
                    [
                        str(row.get("option") or ""),
                        str(row.get("technical_fit") or ""),
                        str(row.get("gmp") or ""),
                        str(row.get("scale_up_risk") or ""),
                        str(row.get("cost_schedule") or ""),
                        str(row.get("reliability") or row.get("rank") or ""),
                    ]
                    for row in matrix
                ],
            )
        vendors = _as_str_list(result.get("manufacturers"))
        vendor_md = _markdown_section(markdown, "vendor / manufacturer", "manufacturer shortlist")
        if vendors or _extract_md_table(vendor_md):
            story.append(Paragraph(f"{n}. Vendor / manufacturer shortlist", styles["h"]))
            n += 1
            vendor_rows = []
            for item in vendors:
                left, right = _split_labeled(item)
                if right:
                    vendor_rows.append([left, right])
                else:
                    vendor_rows.append(["Manufacturer shortlist", item])
            if not vendor_rows:
                vendor_rows = [["Manufacturer shortlist", "; ".join(vendors)]]
            add_md_table_or(
                story,
                vendor_md,
                ("Role", "Likely manufacturers / suppliers"),
                vendor_rows,
            )
        refs = _markdown_section(markdown, "references reviewed", "references")
        if refs:
            story.append(Paragraph(f"{n}. References reviewed", styles["h"]))
            for line in refs.splitlines():
                if line.strip() and not line.strip().startswith("|"):
                    story.append(Paragraph(_inline_md(line.lstrip("-* ")), styles["bullet"]))

    if _has_structured_eval(result):
        _append_structured_report()
    else:
        lines = markdown.splitlines()
        i = 0
        first_heading = True
        skip_titles = {
            system.lower(),
            display_title.lower(),
            "evaluation",
        }
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
                lowered = heading.lower()
                if lowered in skip_titles or lowered.startswith("validated dir"):
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
        canvas.line(0.7 * inch, 0.55 * inch, 8.05 * inch, 0.55 * inch)
        canvas.setFillColor(_color(MUTED))
        canvas.setFont(font, 8)
        canvas.drawString(0.7 * inch, 0.38 * inch, header_title[:120])
        canvas.drawRightString(8.05 * inch, 0.38 * inch, f"Page {doc.page}")
        canvas.restoreState()

    pdf = SimpleDocTemplate(
        str(out),
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.85 * inch,
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
