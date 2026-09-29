from __future__ import annotations

import importlib.util
from pathlib import Path

from bpeai_creator_sdk.artifacts import (
    build_sizing_docx,
    build_sizing_xlsx,
    parse_markdown_table,
    sizing_docx_text,
)
from bpeai_creator_sdk.output import validate_output


def _creator_tools():
    py_root = Path(__file__).resolve().parents[3]
    path = py_root / "apps" / "_templates" / "equipment_sizing" / "creator_tools.py"
    spec = importlib.util.spec_from_file_location("equipment_sizing_creator_tools", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _agitator_table() -> str:
    return (
        "| Item | Method/formula | Result | Unit | Basis |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| Impeller diameter | DIR / catalog | 0.45 | m | vessel D/3 |\n"
        "| Tip speed | =PI()*0.45*2.2 | 3.11 | m/s | 2.2 s^-1 |\n"
        "| Motor power | vendor curve | 5.5 | kW | catalog |\n"
    )


def _pump_table() -> str:
    return (
        "| Item | Method/formula | Result | Unit | Basis |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| Flow | DIR | 12.5 | m3/h | transfer duty |\n"
        "| Differential head | =25000/(1000*9.81) | 2.55 | m | 25 kPa |\n"
        "| NPSH required | vendor curve | 2.1 | m | catalog |\n"
    )


def _sizing_fixture(*, item: str, table: str, capacity_value: str, capacity_unit: str) -> dict:
    headings = (
        "Design basis from DIR",
        "Sized-item concept and criteria",
        "Capacity",
        "Connections for the sized item",
        "Envelope / dimensions",
        "Calculation table",
        "Assumptions, exclusions, vendor confirmation",
    )
    md = "\n\n".join(
        [
            f"# Process vessel {item} sizing",
            "## Design basis from DIR",
            "DIR working volume and duty are used as the sizing basis.",
            "## Sized-item concept and criteria",
            f"Preliminary {item} concept sized from DIR and catalog geometry.",
            "## Capacity",
            f"{capacity_value} {capacity_unit} from DIR.",
            "## Connections for the sized item",
            "Mounting flange and utility connections belong to the sized item.",
            "## Envelope / dimensions",
            "Overall height 2.4 m; diameter 1.8 m (catalog scale).",
            "## Calculation table",
            table,
            "## Assumptions, exclusions, vendor confirmation",
            "Vendor must confirm catalog selection and utility loads.",
        ]
    )
    data = {
        "schema_version": "equipment_sizing_v1",
        "equipment_tag": "EQ-101",
        "equipment_name": f"Process vessel {item}",
        "system_name": "Process vessel",
        "application": "biopharmaceutical",
        "dir_code": "2-1-3",
        "sized_item": item,
        "equipment_system": "mixing" if item == "agitator" else "fluid_transfer",
        "capacity": {"value": capacity_value, "unit": capacity_unit, "basis": "DIR"},
        "connections": [
            {"name": "mounting flange", "size": "6", "unit": "in", "service": "mechanical"}
        ],
        "dimensions": {"value": "2.4 m H x 1.8 m D", "unit": "m", "method": "catalog"},
        "assumptions": ["Vendor confirmation required"],
        "missing_inputs": [],
        "source_basis": ["dir", "knowledge_pack"],
        "datasheet_markdown": md,
        "excel_ready_table": table,
        "selected_model": f"Preliminary {item}",
        "key_specs": [
            {"key": "capacity", "value": capacity_value, "unit": capacity_unit},
            {"key": "envelope", "value": "2.4 x 1.8", "unit": "m"},
        ],
        "creator_attribution": {"display_name": "BPEAI", "app_id": "equipment_sizing"},
    }
    validated = validate_output(data).model_dump()
    validated.update(
        {
            "system_name": "Process vessel",
            "application": "biopharmaceutical",
            "dir_code": "2-1-3",
            "sized_item": item,
            "excel_ready_table": table,
            "datasheet_markdown": md,
        }
    )
    assert all(h.lower() in validated["datasheet_markdown"].lower() for h in headings)
    return validated


def test_parse_markdown_table_headers():
    headers, rows = parse_markdown_table(_agitator_table())
    assert headers[0].lower().startswith("item")
    assert any("result" in h.lower() for h in headers)
    assert rows
    assert "0.45" in rows[0]


def _column_workbook() -> dict:
    return {
        "duty_line": "20 kg batch | 2,000 L | 10 g/L",
        "inputs": [
            {
                "id": "conc",
                "name": "Product concentration",
                "value": 10,
                "unit": "g/L",
                "basis": "DIR",
                "status": "Provided",
            },
            {
                "id": "volume",
                "name": "Feed volume",
                "value": 2000,
                "unit": "L",
                "basis": "DIR",
                "status": "Provided",
            },
            {
                "id": "cycles",
                "name": "Cycles",
                "value": 4,
                "unit": "count",
                "basis": "Equal-cycle assumption",
                "status": "Assumption",
            },
        ],
        "calculations": [
            {
                "id": "mass",
                "name": "Batch target-product mass",
                "method": "C x V / 1000",
                "formula": "={conc}*{volume}/1000",
                "unit": "kg/batch",
                "acceptance": "Calculated from provided feed basis",
            },
            {
                "id": "per_cycle",
                "name": "Product mass per cycle",
                "method": "mass / cycles",
                "formula": "={mass}/{cycles}",
                "unit": "kg/cycle",
                "acceptance": "Four equal cycles",
                "status": '=IF({per_cycle}>0,"MEETS SCREEN","REVIEW")',
            },
        ],
        "summary": {
            "configuration": [
                {"item": "Batch mass", "ref": "mass", "unit": "kg/batch"},
                {"item": "Column concept", "text": "Packed bed", "unit": "-"},
            ],
            "screening": [
                {
                    "metric": "Mass per cycle",
                    "ref": "per_cycle",
                    "unit": "kg/cycle",
                    "interpretation": "Equal-cycle screen",
                }
            ],
            "conclusion": "Preliminary column mass balance. Not a vendor guarantee.",
            "vendor_confirmation": [
                {"item": "Resin loading", "why": "Sets bed volume", "confirmation": "Resin supplier data"}
            ],
        },
        "audit": [
            {
                "name": "Mass identity",
                "method": "conc*vol/1000 - mass",
                "formula": "={conc}*{volume}/1000-{mass}",
                "expected": "0 kg",
            }
        ],
    }


def test_build_sizing_xlsx_column_formulas(tmp_path: Path):
    result = _sizing_fixture(
        item="column",
        table=_pump_table(),
        capacity_value="2000",
        capacity_unit="L",
    )
    result["system_name"] = "Capture chromatography column"
    result["sized_item"] = "column"
    result["calculation_workbook"] = _column_workbook()
    path = build_sizing_xlsx(result, output_path=tmp_path / "column.xlsx")
    from openpyxl import load_workbook

    wb = load_workbook(path)
    assert wb.sheetnames == [
        "Design Summary",
        "Sizing Calculations",
        "Inputs & Assumptions",
        "Audit",
    ]
    inputs = wb["Inputs & Assumptions"]
    assert inputs["B7"].value == 10
    assert inputs["B8"].value == 2000
    assert "FFF2CC" in str(inputs["B7"].fill.fgColor.rgb)
    calc = wb["Sizing Calculations"]
    assert calc["C7"].value == "='Inputs & Assumptions'!B7*'Inputs & Assumptions'!B8/1000"
    assert calc["C8"].value == "=C7/'Inputs & Assumptions'!B9"
    assert "EAF3F8" in str(calc["C7"].fill.fgColor.rgb)
    assert calc["F8"].value == '=IF(C8>0,"MEETS SCREEN","REVIEW")'
    assert all(
        str(calc.cell(row, 3).value or "").startswith("=") for row in range(7, 9)
    )
    summary_formulas = [
        str(cell.value)
        for row in wb["Design Summary"].iter_rows()
        for cell in row
        if str(cell.value or "").startswith("=")
    ]
    assert any(item.startswith("='Sizing Calculations'!") for item in summary_formulas)
    audit = wb["Audit"]
    assert str(audit["C7"].value).startswith("=")
    assert "Sizing Calculations" in str(audit["C7"].value)
    assert "Inputs & Assumptions" in str(audit["C7"].value)


def test_build_sizing_xlsx_rejects_unlinked_result(tmp_path: Path):
    result = {"system_name": "Column", "calculation_workbook": _column_workbook()}
    result["calculation_workbook"]["calculations"][0]["formula"] = "20"
    try:
        build_sizing_xlsx(result, output_path=tmp_path / "bad.xlsx")
    except ValueError as exc:
        assert "reference" in str(exc).lower() or "formula" in str(exc).lower()
    else:
        raise AssertionError("bare numeric result was written")


def test_build_sizing_xlsx_rejects_unresolved_placeholder(tmp_path: Path):
    result = {"system_name": "Column", "calculation_workbook": _column_workbook()}
    result["calculation_workbook"]["calculations"][0]["formula"] = "={missing}*{volume}/1000"
    try:
        build_sizing_xlsx(result, output_path=tmp_path / "bad.xlsx")
    except ValueError as exc:
        assert "unresolved" in str(exc).lower()
    else:
        raise AssertionError("unresolved placeholder was written")


def test_sizing_prompt_requires_formula_workbook():
    tools = _creator_tools()
    message = tools.sizing_report_user_message(
        system_name="Capture column",
        application="biopharmaceutical",
        dir_code="3-3-3",
        decoded_text="DIR",
        sizing_text="",
        plan={},
        cap_raw={},
        conn_raw={},
        dim_raw={},
        search_context="",
        creator_block="",
        required_headings=tools.DEFAULT_SIZING_HEADINGS,
        sized_item="column",
    )
    assert "calculation_workbook" in message
    assert "{conc}*{volume}/1000" in message
    assert "Result column MUST contain evaluated numbers" not in message


def test_title_hero_sketch_accepts_callouts(tmp_path: Path):
    from bpeai_creator_sdk.artifacts.hero_image import (
        infer_sketch_family,
        render_title_hero,
        resolve_hero_callouts,
    )

    column = {"system_name": "Capture chromatography column", "equipment_type": "column"}
    assert infer_sketch_family(column) == "column"
    assert infer_sketch_family({"system_name": "CIP skid heat exchanger"}) == "heat_exchanger"
    assert infer_sketch_family({"equipment_name": "Media prep vessel agitator"}) == "vessel"
    labels = resolve_hero_callouts(column, [{"label": "Bed", "detail": "20 cm"}])
    assert labels[0] == {"label": "Bed", "detail": "20 cm"}
    path = render_title_hero(
        column,
        output_path=tmp_path / "hero.png",
        callouts=[{"label": "Bed", "detail": "20 cm"}],
    )
    assert path.is_file()
    assert path.stat().st_size > 1000
    for name, title in (
        ("vessel", "Media prep vessel agitator"),
        ("exchanger", "CIP skid heat exchanger"),
    ):
        drawn = render_title_hero(
            {"system_name": title},
            output_path=tmp_path / f"{name}.png",
            callouts=[{"label": "Nozzle", "detail": "2 in"}],
        )
        assert drawn.is_file() and drawn.stat().st_size > 1000
    generic = render_title_hero(
        {"system_name": "process skid"},
        output_path=tmp_path / "generic.png",
    )
    assert generic.is_file()
    assert resolve_hero_callouts({"system_name": "process skid"}) == []


def test_build_sizing_docx_includes_numbers(tmp_path: Path):
    result = _sizing_fixture(item="agitator", table=_agitator_table(), capacity_value="2000", capacity_unit="L")
    path = build_sizing_docx(result, output_path=tmp_path / "agitator.docx")
    text = sizing_docx_text(path).lower()
    assert "2000" in text
    assert "capacity" in text
    assert "calculation" in text or "tip speed" in text
    assert "option evaluation" not in text
    assert "process vessel agitator sizing" in text
    assert "process vessel agitator evaluation" not in text


def test_sizing_docx_title_is_system_item_sizing(tmp_path: Path):
    from bpeai_creator_sdk.artifacts.names import attach_sizing_artifact_name

    result = _sizing_fixture(item="agitator", table=_agitator_table(), capacity_value="2000", capacity_unit="L")
    result["system_name"] = "Buffer Preparation Vessel"
    result["schema_version"] = "equipment_sizing_v1"
    result["template_family"] = "equipment_sizing"
    attach_sizing_artifact_name(result)
    path = build_sizing_docx(result, output_path=tmp_path / "buffer.docx")
    text = sizing_docx_text(path)
    assert text.splitlines()[0] == "Buffer Preparation Vessel Agitator Sizing"
    assert "Agitator Evaluation" not in text


def test_sizing_slide_pack_title_says_sizing_not_evaluation():
    from bpeai_creator_sdk.artifacts import build_slide_pack_from_evaluation
    from bpeai_creator_sdk.artifacts.names import attach_sizing_artifact_name

    result = _sizing_fixture(item="agitator", table=_agitator_table(), capacity_value="2000", capacity_unit="L")
    result["system_name"] = "Buffer Preparation Vessel"
    result["schema_version"] = "equipment_sizing_v1"
    result["template_family"] = "equipment_sizing"
    attach_sizing_artifact_name(result)
    pack = build_slide_pack_from_evaluation(result)
    title_lines = pack["slides"][0]["title_lines"]
    joined = " ".join(title_lines)
    assert joined == "Buffer Preparation Vessel Agitator Sizing"
    assert title_lines[-1] == "Sizing"
    assert "Evaluation" not in joined


def test_merge_sizing_report_keeps_required_headings():
    tools = _creator_tools()
    headings = tools.DEFAULT_SIZING_HEADINGS
    raw = {
        "schema_version": "equipment_sizing_v1",
        "equipment_tag": "EQ-1",
        "equipment_name": "Process vessel",
        "datasheet_markdown": "",
    }
    thin_md = "## Capacity\n\n2000 L\n"
    table = _agitator_table()
    merged = tools.merge_sizing_report(
        raw,
        {
            "datasheet_markdown": thin_md,
            "selected_model": "Hydrofoil agitator",
            "key_specs": [{"key": "working volume", "value": "2000", "unit": "L"}],
            "excel_ready_table": table,
        },
        headings=headings,
    )
    md = merged["datasheet_markdown"]
    assert "Capacity" in md
    assert "Calculation table" in md
    assert "2000" in md
    assert merged["excel_ready_table"] == table.strip()
    assert merged["selected_model"] == "Hydrofoil agitator"
    echoed = tools.merge_sizing_report(
        {"datasheet_markdown": "## Calculation table\n"},
        {
            "calculation_workbook": _column_workbook(),
            "excel_ready_table": "| Item | Method/formula | Result | Unit | Basis |\n| --- | --- | --- | --- | --- |\n| Mass | C x V | 20 | kg | number |\n",
        },
        headings=["Calculation table"],
    )
    assert "={conc}*{volume}/1000" in echoed["excel_ready_table"]
    assert "| 20 |" not in echoed["excel_ready_table"]
    assert echoed["calculation_workbook"]["calculations"][0]["id"] == "mass"
    fallback = tools.fallback_sizing_markdown(
        system_name="Process vessel",
        headings=headings,
        cap_raw={"capacity": {"value": "2000", "unit": "L", "basis": "DIR"}},
        conn_raw={"connections": [{"name": "seal flush", "size": "0.5", "unit": "in"}]},
        dim_raw={"dimensions": {"value": "2.4 m H", "unit": "m"}},
        excel_ready_table=table,
    )
    for heading in headings:
        assert heading.lower() in fallback.lower()
    assert "2000" in fallback
