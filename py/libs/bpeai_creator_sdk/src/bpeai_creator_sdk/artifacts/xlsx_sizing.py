"""Equipment-sizing Excel workbook with live formulas.

Layout follows the chromatography resin slurry agitator calculation record:
Design Summary, Sizing Calculations, Inputs & Assumptions, Audit.
Domain equations stay in the calculation_workbook spec. This writer assigns
rows, rewrites ``{id}`` placeholders to cell references, and stores formulas.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from .report_content import _is_table_divider, _split_table_row

_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_CALC_CELL = re.compile(r"\bC\d+\b")

_HEADER = "17365D"
_SECTION = "D9EAF7"
_YELLOW = "FFF2CC"
_BLUE = "EAF3F8"
_WHITE = "FFFFFF"


def parse_markdown_table(markdown: str) -> tuple[list[str], list[list[str]]]:
    """Return (headers, rows) for the first markdown table in ``markdown``."""
    lines = (markdown or "").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|") and i + 1 < len(lines) and _is_table_divider(lines[i + 1]):
            headers = _split_table_row(line)
            rows: list[list[str]] = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not _is_table_divider(lines[i]):
                    rows.append(_split_table_row(lines[i]))
                i += 1
            if headers:
                return headers, rows
        i += 1
    return [], []


def build_sizing_xlsx(
    result: Mapping[str, Any],
    *,
    output_path: Path | str,
) -> Path:
    """Write a four-sheet workbook whose result cells are Excel formulas."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except ImportError as exc:  # pragma: no cover - optional local dep
        raise RuntimeError("openpyxl is required to write the sizing workbook") from exc

    spec = result.get("calculation_workbook")
    if not isinstance(spec, Mapping):
        raise ValueError("calculation_workbook is required to write a sizing workbook")
    inputs = _mapping_list(spec.get("inputs"))
    calculations = _mapping_list(spec.get("calculations"))
    if not inputs or not calculations:
        raise ValueError("calculation_workbook needs inputs and calculations")
    summary = spec.get("summary") if isinstance(spec.get("summary"), Mapping) else {}
    audit_rows = _mapping_list(spec.get("audit"))
    if not audit_rows:
        raise ValueError("calculation_workbook needs audit checks")

    input_cells, calc_cells = _assign_cells(inputs, calculations)
    calc_formulas = [
        _rewrite(str(row.get("formula") or ""), context="calc", input_cells=input_cells, calc_cells=calc_cells)
        for row in calculations
    ]
    for formula in calc_formulas:
        if not _formula_links(formula):
            raise ValueError(f"calculation formula does not reference a cell: {formula}")
    if not any("Inputs & Assumptions" in formula for formula in calc_formulas):
        raise ValueError("at least one calculation must reference an input cell")

    out = Path(output_path)
    if out.suffix.lower() != ".xlsx":
        out = out.with_suffix(".xlsx")
    out.parent.mkdir(parents=True, exist_ok=True)

    header_fill = PatternFill("solid", fgColor=_HEADER)
    header_font = Font(color=_WHITE, bold=True, name="Calibri")
    title_font = Font(bold=True, size=14, color=_HEADER, name="Calibri")
    section_fill = PatternFill("solid", fgColor=_SECTION)
    yellow = PatternFill("solid", fgColor=_YELLOW)
    blue = PatternFill("solid", fgColor=_BLUE)
    wrap = Alignment(wrap_text=True, vertical="center")

    system = str(result.get("system_name") or result.get("equipment_name") or "Equipment").strip()
    item = str(result.get("sized_item") or "sizing").strip()
    wb = Workbook()

    summary_ws = wb.active
    summary_ws.title = "Design Summary"
    calc_ws = wb.create_sheet("Sizing Calculations")
    inputs_ws = wb.create_sheet("Inputs & Assumptions")
    audit_ws = wb.create_sheet("Audit")

    _write_inputs(
        inputs_ws,
        inputs,
        title=str(spec.get("inputs_title") or f"{system} — Inputs and Assumptions"),
        note=str(
            spec.get("inputs_note")
            or "Yellow cells are editable. Calculated sheets use Excel formulas."
        ),
        title_font=title_font,
        header_fill=header_fill,
        header_font=header_font,
        yellow=yellow,
        wrap=wrap,
    )
    _write_calculations(
        calc_ws,
        calculations,
        calc_formulas,
        input_cells=input_cells,
        calc_cells=calc_cells,
        title_font=title_font,
        header_fill=header_fill,
        header_font=header_font,
        blue=blue,
        wrap=wrap,
    )
    _write_summary(
        summary_ws,
        summary,
        title=str(spec.get("title") or f"{system} — Preliminary {item} Basis"),
        duty_line=str(spec.get("duty_line") or ""),
        input_cells=input_cells,
        calc_cells=calc_cells,
        title_font=title_font,
        header_fill=header_fill,
        header_font=header_font,
        section_fill=section_fill,
        yellow=yellow,
        wrap=wrap,
    )
    _write_audit(
        audit_ws,
        audit_rows,
        input_cells=input_cells,
        calc_cells=calc_cells,
        title_font=title_font,
        header_fill=header_fill,
        header_font=header_font,
        blue=blue,
        wrap=wrap,
    )

    for sheet, widths in (
        (summary_ws, (36, 56, 18, 56)),
        (calc_ws, (34, 42, 22, 16, 48, 22)),
        (inputs_ws, (36, 22, 18, 48, 18)),
        (audit_ws, (36, 42, 28, 22)),
    ):
        for index, width in enumerate(widths, start=1):
            sheet.column_dimensions[get_column_letter(index)].width = width
        sheet.freeze_panes = "A7"
        for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row, max_col=len(widths)):
            for cell in row:
                if isinstance(cell.value, str) and len(cell.value) > 48 and cell.alignment.wrap_text is not True:
                    cell.alignment = wrap

    try:
        wb.save(str(out))
        return out
    except PermissionError:
        from datetime import datetime

        stamped = out.with_name(f"{out.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{out.suffix}")
        wb.save(str(stamped))
        return stamped


def _mapping_list(raw: Any) -> list[Mapping[str, Any]]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def _assign_cells(
    inputs: Sequence[Mapping[str, Any]],
    calculations: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, str], dict[str, str]]:
    input_cells: dict[str, str] = {}
    calc_cells: dict[str, str] = {}
    for offset, row in enumerate(inputs):
        key = _row_id(row, kind="input")
        if key in input_cells:
            raise ValueError(f"duplicate input id {key}")
        input_cells[key] = f"'Inputs & Assumptions'!B{7 + offset}"
    for offset, row in enumerate(calculations):
        key = _row_id(row, kind="calculation")
        if key in calc_cells or key in input_cells:
            raise ValueError(f"duplicate calculation id {key}")
        calc_cells[key] = f"C{7 + offset}"
    return input_cells, calc_cells


def _row_id(row: Mapping[str, Any], *, kind: str) -> str:
    key = str(row.get("id") or "").strip()
    if not key or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        raise ValueError(f"{kind} id must be a placeholder name, got {key!r}")
    return key


def _rewrite(
    formula: str,
    *,
    context: str,
    input_cells: Mapping[str, str],
    calc_cells: Mapping[str, str],
) -> str:
    text = str(formula or "").strip()
    if not text:
        raise ValueError("calculation formula is empty")
    if not text.startswith("="):
        text = "=" + text

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in input_cells and key not in calc_cells:
            raise ValueError(f"unresolved placeholder {{{key}}}")
        if context == "calc" and key in calc_cells:
            return calc_cells[key]
        if key in input_cells and context == "calc":
            return input_cells[key]
        if key in calc_cells:
            return f"'Sizing Calculations'!{calc_cells[key]}"
        return input_cells[key]

    rewritten = _PLACEHOLDER.sub(repl, text)
    if "{" in rewritten and _PLACEHOLDER.search(rewritten):
        raise ValueError(f"unresolved placeholder in {rewritten}")
    if not rewritten.startswith("="):
        raise ValueError(f"formula must start with '=': {rewritten}")
    return rewritten


def _formula_links(formula: str) -> bool:
    return "Inputs & Assumptions" in formula or bool(_CALC_CELL.search(formula))


def _excel_value(raw: Any) -> Any:
    if isinstance(raw, bool) or isinstance(raw, (int, float)):
        return raw
    text = str(raw if raw is not None else "").strip()
    if not text:
        return None
    compact = text.replace(",", "")
    if re.fullmatch(r"-?\d+", compact):
        return int(compact)
    if re.fullmatch(r"-?\d+(\.\d+)?([eE][+-]?\d+)?", compact):
        return float(compact)
    return text


def _style_header(sheet, row: int, columns: int, fill, font) -> None:
    for col in range(1, columns + 1):
        cell = sheet.cell(row, col)
        cell.fill = fill
        cell.font = font


def _section(sheet, row: int, text: str, fill, columns: int = 4) -> None:
    from openpyxl.styles import Font

    sheet.cell(row, 1, text)
    sheet.cell(row, 1).font = Font(bold=True, color="17365D")
    for col in range(1, columns + 1):
        sheet.cell(row, col).fill = fill


def _ref_formula(ref: str, *, input_cells: Mapping[str, str], calc_cells: Mapping[str, str]) -> str:
    key = str(ref or "").strip()
    if key in calc_cells:
        return f"='Sizing Calculations'!{calc_cells[key]}"
    if key in input_cells:
        return f"={input_cells[key]}"
    raise ValueError(f"unresolved summary reference {{{key}}}")


def _write_inputs(sheet, inputs, *, title, note, title_font, header_fill, header_font, yellow, wrap) -> None:
    sheet["A2"] = title
    sheet["A2"].font = title_font
    sheet["A4"] = note
    sheet["A4"].alignment = wrap
    headers = ("Parameter", "Value", "Unit", "Basis / source", "Status")
    for col, header in enumerate(headers, start=1):
        sheet.cell(6, col, header)
    _style_header(sheet, 6, len(headers), header_fill, header_font)
    for offset, row in enumerate(inputs):
        excel_row = 7 + offset
        sheet.cell(excel_row, 1, str(row.get("name") or row.get("id") or ""))
        value_cell = sheet.cell(excel_row, 2, _excel_value(row.get("value")))
        value_cell.fill = yellow
        sheet.cell(excel_row, 3, str(row.get("unit") or ""))
        basis = sheet.cell(excel_row, 4, str(row.get("basis") or ""))
        basis.alignment = wrap
        sheet.cell(excel_row, 5, str(row.get("status") or ""))


def _write_calculations(
    sheet,
    calculations,
    formulas,
    *,
    input_cells,
    calc_cells,
    title_font,
    header_fill,
    header_font,
    blue,
    wrap,
) -> None:
    sheet["A2"] = "Sizing Calculations"
    sheet["A2"].font = title_font
    sheet["A4"] = "Preliminary sizing screen. All blue-value cells contain visible Excel formulas."
    headers = ("Calculation", "Formula / method", "Result", "Unit", "Acceptance / interpretation", "Status")
    for col, header in enumerate(headers, start=1):
        sheet.cell(6, col, header)
    _style_header(sheet, 6, len(headers), header_fill, header_font)
    for offset, (row, formula) in enumerate(zip(calculations, formulas)):
        excel_row = 7 + offset
        sheet.cell(excel_row, 1, str(row.get("name") or row.get("id") or ""))
        method = sheet.cell(excel_row, 2, str(row.get("method") or ""))
        method.alignment = wrap
        result = sheet.cell(excel_row, 3, formula)
        result.fill = blue
        result.number_format = "0.000"
        sheet.cell(excel_row, 4, str(row.get("unit") or ""))
        acceptance = sheet.cell(excel_row, 5, str(row.get("acceptance") or ""))
        acceptance.alignment = wrap
        status = str(row.get("status") or "").strip()
        if status:
            if status.startswith("=") or "{" in status:
                status = _rewrite(status, context="calc", input_cells=input_cells, calc_cells=calc_cells)
            sheet.cell(excel_row, 6, status)


def _write_summary(
    sheet,
    summary,
    *,
    title,
    duty_line,
    input_cells,
    calc_cells,
    title_font,
    header_fill,
    header_font,
    section_fill,
    yellow,
    wrap,
) -> None:
    sheet["A2"] = title
    sheet["A2"].font = title_font
    if duty_line:
        sheet["A4"] = duty_line
        sheet["A4"].alignment = wrap
    row = 6
    _section(sheet, row, "Recommended preliminary configuration", section_fill)
    row = 7
    for col, header in enumerate(("Item", "Preliminary basis", "Unit"), start=1):
        sheet.cell(row, col, header)
    _style_header(sheet, row, 3, header_fill, header_font)
    for item in _mapping_list(summary.get("configuration")):
        row += 1
        sheet.cell(row, 1, str(item.get("item") or item.get("name") or ""))
        ref = str(item.get("ref") or "").strip()
        if ref:
            cell = sheet.cell(row, 2, _ref_formula(ref, input_cells=input_cells, calc_cells=calc_cells))
            cell.number_format = "0.000"
        else:
            sheet.cell(row, 2, str(item.get("text") or item.get("value") or ""))
        sheet.cell(row, 3, str(item.get("unit") or ""))
    row += 2
    _section(sheet, row, "Key screening results", section_fill)
    row += 1
    for col, header in enumerate(("Metric", "Result", "Unit", "Interpretation"), start=1):
        sheet.cell(row, col, header)
    _style_header(sheet, row, 4, header_fill, header_font)
    for item in _mapping_list(summary.get("screening")):
        row += 1
        sheet.cell(row, 1, str(item.get("metric") or item.get("item") or ""))
        ref = str(item.get("ref") or "").strip()
        if ref:
            cell = sheet.cell(row, 2, _ref_formula(ref, input_cells=input_cells, calc_cells=calc_cells))
            cell.number_format = "0.000"
        else:
            text = str(item.get("text") or "")
            if text.startswith("=") or "{" in text:
                text = _rewrite(text, context="summary", input_cells=input_cells, calc_cells=calc_cells)
            sheet.cell(row, 2, text)
        sheet.cell(row, 3, str(item.get("unit") or ""))
        note = sheet.cell(row, 4, str(item.get("interpretation") or ""))
        note.alignment = wrap
    conclusion = str(summary.get("conclusion") or "").strip()
    if conclusion:
        row += 2
        _section(sheet, row, "Engineering conclusion and limitations", section_fill)
        row += 1
        cell = sheet.cell(row, 1, conclusion)
        cell.fill = yellow
        cell.alignment = wrap
        sheet.row_dimensions[row].height = 64
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
    vendor = _mapping_list(summary.get("vendor_confirmation"))
    if vendor:
        row += 2
        _section(sheet, row, "Critical vendor-confirmation items", section_fill)
        row += 1
        for col, header in enumerate(("No.", "Item", "Why it matters", "Required confirmation"), start=1):
            sheet.cell(row, col, header)
        _style_header(sheet, row, 4, header_fill, header_font)
        for index, item in enumerate(vendor, start=1):
            row += 1
            sheet.cell(row, 1, index)
            sheet.cell(row, 2, str(item.get("item") or ""))
            why = sheet.cell(row, 3, str(item.get("why") or ""))
            why.alignment = wrap
            confirm = sheet.cell(row, 4, str(item.get("confirmation") or ""))
            confirm.alignment = wrap


def _write_audit(
    sheet,
    audit_rows,
    *,
    input_cells,
    calc_cells,
    title_font,
    header_fill,
    header_font,
    blue,
    wrap,
) -> None:
    sheet["A2"] = "Audit and Traceability"
    sheet["A2"].font = title_font
    sheet["A4"] = "Terminal checks only; no calculation or output depends on this sheet."
    headers = ("Check", "Formula", "Result", "Expected")
    for col, header in enumerate(headers, start=1):
        sheet.cell(6, col, header)
    _style_header(sheet, 6, len(headers), header_fill, header_font)
    for offset, row in enumerate(audit_rows):
        excel_row = 7 + offset
        sheet.cell(excel_row, 1, str(row.get("name") or row.get("check") or ""))
        method = sheet.cell(excel_row, 2, str(row.get("method") or ""))
        method.alignment = wrap
        formula = _rewrite(
            str(row.get("formula") or ""),
            context="audit",
            input_cells=input_cells,
            calc_cells=calc_cells,
        )
        result = sheet.cell(excel_row, 3, formula)
        result.fill = blue
        sheet.cell(excel_row, 4, str(row.get("expected") or ""))
