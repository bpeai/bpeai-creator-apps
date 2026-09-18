"""Shared evaluation-report content assembly (format-agnostic)."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence


_MD_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$")
_NUM_HEADING_RE = re.compile(r"^(\d+)[.)]\s+(?!\d)(.{2,90})$")
_LABELED_RE = re.compile(
    r"^(?:[-*•]|\d+[.)])\s+(?:\*\*)?([^:*]{2,48})(?:\*\*)?\s*:\s+(.+)$"
)


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


