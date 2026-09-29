"""Optional creator helpers for equipment_sizing apps.

Copy this file with the template. Non-coders can ignore it — pack YAML
(``prompt_fragments.yaml``, outlines, options) is the primary dial.

HANDSHAKE: helpers must stay inside existing run phases (dir / evaluate / pptx /
generate_dir) and known result shapes (dir_requirements JSON or
equipment_sizing_v1). They may call ``agent.status(...)`` (SSE ``status``).
They must NOT invent new SSE event names or assume custom hub UI buttons.

See ``EXTENSIONS.md`` and ``docs/EI_CREATOR_EXTENSIONS.md``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Sequence

DEFAULT_SIZING_HEADINGS = (
    "Design basis from DIR",
    "Sized-item concept and criteria",
    "Capacity",
    "Connections for the sized item",
    "Envelope / dimensions",
    "Calculation table",
    "Assumptions, exclusions, vendor confirmation",
)


def research_context_note(system_name: str, application: str) -> str:
    """Build a short note you can append to a user prompt (evaluate / DIR).

    HANDSHAKE: prompt text only — does not emit SSE or change result schema.
    """
    name = (system_name or "equipment").strip()
    app = (application or "biopharmaceutical").strip()
    return (
        f"Creator research focus: prioritize industrial references for {name} "
        f"in a {app} context; cite title + URL when used."
    )


def postprocess_evaluation_result(
    result: MutableMapping[str, Any],
    *,
    extra_warning: str = "",
) -> Dict[str, Any]:
    """Light post-process after ``validate_output`` / model_dump.

    HANDSHAKE: may add ``sme_warnings`` entries; must keep ``phase`` =
    ``evaluation`` and ``equipment_sizing_v1`` fields intact.
    """
    out = dict(result)
    if extra_warning.strip():
        warnings = list(out.get("sme_warnings") or [])
        if not isinstance(warnings, list):
            warnings = []
        warnings.append(extra_warning.strip())
        out["sme_warnings"] = warnings
    return out


def merge_status_prefix(message: str, *, app_label: str = "") -> str:
    """Format a status line for ``self.status(...)``.

    HANDSHAKE: ``self.status(text)`` → SSE event ``status`` (string payload).
    """
    label = (app_label or "").strip()
    msg = (message or "").strip()
    if label:
        return f"[{label}] {msg}"
    return msg


def optional_dir_enrichment(
    dir_payload: Mapping[str, Any],
    *,
    note: str = "",
) -> Dict[str, Any]:
    """Optionally annotate a DIR questionnaire payload before return.

    HANDSHAKE: return must keep ``phase`` = ``dir_requirements`` and the
    fields the generic UI reads (``requirements``, ``common_codes``,
    ``message``, etc.). Extra keys are additive only.
    """
    out = dict(dir_payload)
    if note.strip():
        existing = str(out.get("message") or "").rstrip()
        out["message"] = f"{existing}\n\n{note.strip()}" if existing else note.strip()
    return out


def _as_spec_list(raw: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        unit = item.get("unit")
        out.append(
            {
                "key": key,
                "value": item.get("value") if item.get("value") is not None else "",
                "unit": unit if unit not in (None, "") else None,
            }
        )
    return out


def _mapping_rows(raw: Any) -> list:
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def workbook_markdown(workbook: Mapping[str, Any]) -> str:
    """Human-readable echo of a calculation workbook. Formulas stay in the method column."""
    rows = _mapping_rows(workbook.get("calculations"))
    if not rows:
        return ""
    lines = [
        "| Item | Method/formula | Result | Unit | Basis |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        name = str(row.get("name") or row.get("id") or "").replace("|", "/")
        method = str(row.get("method") or "").replace("|", "/")
        formula = str(row.get("formula") or "").strip().replace("|", "/")
        shown = f"{method}; {formula}".strip("; ") if formula else method
        unit = str(row.get("unit") or "").replace("|", "/")
        basis = str(row.get("acceptance") or row.get("basis") or "").replace("|", "/")
        lines.append(f"| {name} | {shown} | {formula} | {unit} | {basis} |")
    return "\n".join(lines)


def _calculation_heading(headings: Sequence[str]) -> str:
    for heading in headings:
        text = str(heading or "").strip()
        if not text:
            continue
        lowered = text.lower()
        if "calculat" in lowered or "excel" in lowered:
            return text
    return "Calculation table"


def sizing_report_user_message(
    *,
    system_name: str,
    application: str,
    dir_code: str,
    decoded_text: str,
    sizing_text: str,
    plan: Mapping[str, Any],
    cap_raw: Mapping[str, Any],
    conn_raw: Mapping[str, Any],
    dim_raw: Mapping[str, Any],
    search_context: str,
    creator_block: str,
    required_headings: Sequence[str],
    sized_item: str = "",
    sme_instructions: str = "",
) -> str:
    """User message for the sizing_report LLM (generic; pack supplies headings)."""
    headings = ", ".join(str(h) for h in required_headings if str(h).strip()) or ", ".join(
        DEFAULT_SIZING_HEADINGS
    )
    item = (sized_item or "sized item").strip()
    user = (
        f"System: {system_name}\nApplication: {application}\nDIR code: {dir_code}\n"
        f"Sized item: {item}\n"
        f"Decoded DIR:\n{decoded_text}\n"
        f"Sizing inputs:\n{sizing_text or '(none)'}\n"
        f"Plan: {plan}\n"
        f"Capacity JSON: {cap_raw}\n"
        f"Connections JSON: {conn_raw}\n"
        f"Dimensions JSON: {dim_raw}\n"
        f"Search context:\n{(search_context or '')[:12000]}\n"
    )
    if creator_block:
        user += f"{creator_block[:8000]}\n"
    if sme_instructions:
        user += f"\n{sme_instructions}\n"
    user += (
        "Return JSON only:\n"
        '{"datasheet_markdown":"markdown with the required headings",'
        '"selected_model":"sized-item concept string",'
        '"key_specs":[{"key":"","value":"","unit":""}],'
        '"calculation_workbook":{'
        '"duty_line":"one-line duty",'
        '"inputs":[{"id":"conc","name":"","value":0,"unit":"","basis":"","status":"Provided"}],'
        '"calculations":[{"id":"mass","name":"","method":"C x V / 1000","formula":"={conc}*{volume}/1000",'
        '"unit":"","acceptance":"","status":""}],'
        '"summary":{"configuration":[{"item":"","ref":"mass","unit":""}],'
        '"screening":[{"metric":"","ref":"mass","unit":"","interpretation":""}],'
        '"conclusion":"","vendor_confirmation":[{"item":"","why":"","confirmation":""}]},'
        '"audit":[{"name":"","method":"","formula":"={conc}*{volume}/1000-{mass}","expected":"0"}]'
        "}}\n"
        f"Required datasheet_markdown headings in order: {headings}.\n"
        "calculation_workbook is the calculation record. Do not put evaluated numbers in result cells.\n"
        "inputs: every editable parameter (DIR value or assumption), with id, name, value, unit, basis, "
        "and status Provided, Assumption, or Vendor confirm. "
        "calculations: a chained set for this sized item (typically 8–20 rows). "
        "formula uses {input_id} and {calc_id} placeholders, never hardcoded project numbers and never "
        "a bare numeric result. Later rows must reference earlier calc ids. "
        "method is the equation in words. acceptance states the screen. "
        "status is empty, a short flag such as VENDOR CONFIRM, or an Excel IF using the same placeholders "
        '(example =IF({tip}<={tip_max},"MEETS SCREEN","REVIEW")). '
        "summary.configuration and summary.screening ref fields name an input or calculation id "
        "(quantities are links, not typed numbers). Text concept rows use text instead of ref. "
        "conclusion is the engineering limitation paragraph. vendor_confirmation lists what the vendor must confirm. "
        "audit formulas are identities or pass/fail checks that reference the same ids; expected is the pass text. "
        "Constants an engineer might change belong in inputs. "
        f"Size connections that belong to this {item}; do not invent unrelated host "
        "process nozzles unless the DIR or pack instructions require them. "
        "Use units on every number. Label estimates vs catalog values."
    )
    return user


def merge_sizing_report(
    raw: MutableMapping[str, Any],
    report: Mapping[str, Any],
    *,
    headings: Sequence[str] = (),
) -> Dict[str, Any]:
    """Fold sizing_report JSON into equipment_sizing_v1 fields before validate_output."""
    out = dict(raw)
    md = str(report.get("datasheet_markdown") or "").strip()
    workbook = report.get("calculation_workbook")
    if isinstance(workbook, Mapping) and _mapping_rows(workbook.get("calculations")):
        out["calculation_workbook"] = dict(workbook)
        echo = workbook_markdown(workbook)
        if echo:
            report = dict(report)
            report["excel_ready_table"] = echo
    table = str(report.get("excel_ready_table") or "").strip()
    if table:
        out["excel_ready_table"] = table
        calc_heading = _calculation_heading(headings)
        if calc_heading.lower() not in md.lower():
            md = (md + f"\n\n## {calc_heading}\n\n" + table).strip()
        elif table not in md:
            md = md.rstrip() + "\n\n" + table
    if md:
        out["datasheet_markdown"] = md
    model = str(report.get("selected_model") or "").strip()
    if model:
        out["selected_model"] = model
        if not str(out.get("equipment_name") or "").strip():
            out["equipment_name"] = model
    specs = _as_spec_list(report.get("key_specs"))
    if specs:
        existing = _as_spec_list(out.get("key_specs"))
        keys = {str(item.get("key")) for item in existing}
        for spec in specs:
            if spec["key"] not in keys:
                existing.append(spec)
        out["key_specs"] = existing
    missing_heads = [
        heading
        for heading in headings
        if heading and heading.lower() not in (out.get("datasheet_markdown") or "").lower()
    ]
    if missing_heads:
        warnings = list(out.get("sme_warnings") or [])
        warnings.append("Datasheet missing headings: " + ", ".join(missing_heads))
        out["sme_warnings"] = warnings
    return out


def fallback_sizing_markdown(
    *,
    system_name: str,
    headings: Sequence[str],
    cap_raw: Mapping[str, Any],
    conn_raw: Mapping[str, Any],
    dim_raw: Mapping[str, Any],
    excel_ready_table: str = "",
) -> str:
    """Deterministic datasheet if sizing_report JSON is empty."""
    import json

    heads = [str(h).strip() for h in headings if str(h).strip()] or list(DEFAULT_SIZING_HEADINGS)
    cap = cap_raw.get("capacity") if isinstance(cap_raw.get("capacity"), Mapping) else {}
    conn = conn_raw.get("connections") if isinstance(conn_raw.get("connections"), list) else []
    dim = dim_raw.get("dimensions") if isinstance(dim_raw.get("dimensions"), Mapping) else {}
    assumptions = [
        str(item).strip()
        for item in (
            *(cap_raw.get("assumptions") or []),
            *(conn_raw.get("assumptions") or []),
            *(dim_raw.get("assumptions") or []),
        )
        if str(item).strip()
    ]
    parts = [f"# {system_name} sizing"]
    for heading in heads:
        parts.append(f"## {heading}")
        lowered = heading.lower()
        if "capacit" in lowered:
            value = f"{cap.get('value', '')} {cap.get('unit', '')}".strip()
            basis = str(cap.get("basis") or "").strip()
            parts.append(value or json.dumps(cap or {}, indent=2))
            if basis:
                parts.append(f"Basis: {basis}")
        elif "connection" in lowered:
            parts.append(json.dumps(conn, indent=2) if conn else "(none)")
            utilities = str(conn_raw.get("utilities") or "").strip()
            if utilities:
                parts.append(f"Utilities: {utilities}")
        elif "envelope" in lowered or "dimension" in lowered:
            parts.append(json.dumps(dim or {}, indent=2))
        elif "calculat" in lowered or "excel" in lowered:
            parts.append(excel_ready_table.strip() or "(no calculation table)")
        elif "assumption" in lowered:
            parts.append("\n".join(f"- {item}" for item in assumptions) or "(none)")
        elif "concept" in lowered or "criteri" in lowered:
            parts.append("Sized-item concept from DIR and pack criteria.")
        else:
            parts.append("From validated DIR and sizing JSON.")
    return "\n\n".join(parts).strip() + "\n"
