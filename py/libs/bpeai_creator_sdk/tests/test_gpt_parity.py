from __future__ import annotations

from pathlib import Path

import pytest

from pptx import Presentation

from bpeai_creator_sdk.artifacts import (
    build_evaluation_pptx,
    build_slide_pack_from_evaluation,
)
from bpeai_creator_sdk.local_format import format_result_text
from bpeai_creator_sdk.local_run import is_selector_result
from bpeai_creator_sdk.output import validate_output
from bpeai_creator_sdk.sme import (
    missing_report_headings,
    validate_dir_code,
)

from pack_paths import load_platform_pack_or_skip


@pytest.fixture(scope="module")
def py_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def mixing_pack(py_root: Path):
    return load_platform_pack_or_skip("mixing", py_root)


def test_pack_loads_outlines(mixing_pack):
    headings = mixing_pack.required_report_headings()
    assert headings
    assert "Validated DIR" in headings
    assert "Mixing objectives and failure modes" in headings
    assert "Suggested operating recipe for qualification" in headings
    assert "Option evaluation matrix" in headings
    assert "Vendor / manufacturer shortlist" in headings
    assert "References reviewed" in headings
    assert "Manufacturers and references" not in headings
    assert mixing_pack.pptx_outline.get("slide_count") == 7
    assert mixing_pack.fragment("workflow")
    assert mixing_pack.common_code_entries("media_preparation")[0]["caption"]


def test_missing_report_headings():
    md = "# Validated DIR\n# Design basis\n"
    missing = missing_report_headings(
        md,
        ["Validated DIR", "Design basis", "Strong-fit mixing types"],
    )
    assert missing == ["Strong-fit mixing types"]


def test_dir_code_still_validates(mixing_pack):
    ok = validate_dir_code(mixing_pack, "media_preparation", "2-1-2-3-1-1")
    assert ok.ok


def test_build_evaluation_pptx_smoke(tmp_path: Path, mixing_pack):
    fixture = {
        "system_name": "Media Prep Vessel",
        "dir_code": "2-1-2-3-1-1",
        "selected_model": "Top-entry low-shear axial hydrofoil agitator",
        "recommended_basis": "Top-entry low-shear axial hydrofoil agitator",
        "alternate_basis": "Aseptic magnetic bottom mixer",
        "design_basis": "Readily soluble dry powder, manual top-charge, CIP/SIP stainless.",
        "failure_modes": ["Clumping", "Foam", "Seal SIP issue", "Low-fill dead zone"],
        "objectives": ["Dissolve", "Homogenize", "Hygienic"],
        "mixing_options": [
            {
                "name": "Top-entry low-shear axial hydrofoil agitator",
                "fit": "best",
                "pros": ["low foam", "CIP/SIP", "turndown"],
                "cons": ["seal care"],
                "manufacturers": ["Lightnin A310"],
            }
        ],
        "evaluation_matrix": [
            {
                "option": "Hydrofoil",
                "technical_fit": "Best",
                "gmp": "High",
                "scale_up_risk": "Low",
                "cost_schedule": "Best",
                "reliability": "High",
                "rank": 1,
            }
        ],
        "preliminary_specs": ["316L", "VFD", "Baffles"],
        "manufacturers": ["Lightnin", "Alfa Laval"],
        "do_not_specify": ["Rushton-only"],
        "rationale": "Best fit for manual charge media prep.",
        "datasheet_markdown": "# Design basis\nTest body.\n\n# Option evaluation\nDetails here.\n",
    }
    out = tmp_path / "media_prep.pptx"
    slide_pack = build_slide_pack_from_evaluation(fixture)
    path = build_evaluation_pptx(
        fixture,
        outline=mixing_pack.pptx_outline,
        output_path=out,
        slide_pack=slide_pack,
    )
    assert path.is_file()
    prs = Presentation(str(path))
    assert len(prs.slides) == 7
    assert abs(prs.slide_width.inches - 13.333) < 0.01


def test_slide3_objective_cards_keep_long_titles(tmp_path: Path):
    """Slide 3 titles must wrap in the card, not hard-clip at 22 characters."""
    fixture = {
        "system_name": "MF Harvest Clarification Skid",
        "dir_code": "3-3-3-3-3-3-3",
        "selected_model": "Closed MF-TFF harvest skid",
        "recommended_basis": "Closed MF-TFF harvest skid",
        "objectives": ["Clarify harvest", "Operate at target flux"],
        "failure_modes": ["TMP runaway", "Turbidity breakthrough"],
    }
    slide_pack = build_slide_pack_from_evaluation(fixture)
    slide_pack["slides"][2]["process_steps"] = [
        {"n": 1, "title": "Clarify harvest", "detail": "5,000–10,000 L in ≤8 h; ≥95% recovery."},
        {"n": 2, "title": "Operate at target flux", "detail": "100–155 LMH via constant-flux with TMP limit."},
        {
            "n": 3,
            "title": "Manage hydraulics",
            "detail": "Crossflow 300–600 L/m²/h; TMP 0.8–2.0 bar controlled.",
        },
        {
            "n": 4,
            "title": "Maintain thermal consistency",
            "detail": "≤2 °C temperature rise across skid at design conditions.",
        },
    ]
    path = build_evaluation_pptx(
        fixture,
        outline=None,
        output_path=tmp_path / "slide3.pptx",
        slide_pack=slide_pack,
    )
    prs = Presentation(str(path))
    texts = []
    for shape in prs.slides[2].shapes:
        if shape.has_text_frame:
            texts.append(shape.text_frame.text)
    joined = "\n".join(texts)
    assert "Maintain thermal consistency" in joined
    assert "cons…" not in joined
    assert "design conditions" in joined
    assert "bar controlled" in joined


def test_build_evaluation_docx_and_reference_decks(tmp_path: Path, mixing_pack):
    from bpeai_creator_sdk import build_evaluation_docx, list_reference_decks

    docx = build_evaluation_docx(
        {
            "system_name": "Media Prep Vessel",
            "dir_code": "2-1-2-3-1-1",
            "datasheet_markdown": "# Design basis\n\nSelection implication narrative.\n\n## Option evaluation\n\n- Hydrofoil best fit\n",
            "selected_model": "Hydrofoil",
        },
        output_path=tmp_path / "eval.docx",
    )
    assert docx.is_file()
    assert docx.stat().st_size > 500

    decks = list_reference_decks(mixing_pack.path, outline=mixing_pack.pptx_outline)
    assert decks
    assert any(d["name"].endswith(".pptx") for d in decks)


def test_evaluation_pdf_urs_layout(tmp_path: Path):
    from bpeai_creator_sdk import build_evaluation_docx
    from bpeai_creator_sdk.artifacts import evaluation_docx_text

    docx = build_evaluation_docx(
        {
            "system_name": "Conditioning & Mixing Tank",
            "application": "Biopharmaceuticals",
            "dir_code": "4-3-5-5-2-3-2-2",
            "selected_model": "Pitched-blade turbine",
            "recommended_basis": (
                "Specify a jacketed 316L conditioning tank with a pitched-blade "
                "turbine and VFD so crystal slurry stays suspended without attrition."
            ),
            "datasheet_markdown": """# Conditioning & Mixing Tank

1) Validated DIR

- Working volume: 2.5 m3
- Duty: crystal slurry hold and transfer

## Recommended basis of design

Specify a jacketed 316L tank with a pitched-blade turbine.

## Option evaluation

| Option | Fit | Note |
|---|---|---|
| Pitched-blade turbine | Best | Suspends crystals |
| Hydrofoil | Acceptable | Lower shear |

2.5 m3 is the working volume, not a heading.
""",
        },
        output_path=tmp_path / "conditioning.docx",
    )
    assert docx.is_file()
    text = evaluation_docx_text(docx)
    assert "Conditioning & Mixing Tank" in text
    assert "Recommendation in one line" in text
    assert "Pitched-blade turbine" in text
    assert "Validated DIR" in text
    assert "Working volume" in text
    assert "2.5 m3 is the working volume" in text
    assert "BPEAI equipment evaluation · project-team summary" not in text


def test_cip_system_pump_evaluation_title_and_tables(tmp_path: Path):
    from bpeai_creator_sdk.artifacts.names import evaluation_title_lines
    from bpeai_creator_sdk import build_evaluation_docx, build_evaluation_pptx
    from bpeai_creator_sdk.artifacts import evaluation_docx_text

    result = {
        "system_name": "CIP system",
        "evaluated_item": "pump",
        "application": "biopharmaceutical",
        "dir_code": "3-3-2-1-2-2-4",
        "selected_model": "High-head hygienic sanitary centrifugal CIP supply pump",
        "recommended_basis": (
            "Preliminary: high-head hygienic sanitary centrifugal CIP supply pump "
            "with VFD, vendor-certified across all recipe system curves."
        ),
        "key_specs": [
            {"key": "hygienic", "value": "Sanitary connections"},
            {"key": "high-head", "value": "6 to 10 bar differential"},
            {"key": "variable-speed", "value": "VFD-protected NPSH"},
            {"key": "drainable", "value": "CIP supply and recirculation"},
        ],
        "decoded_dir": [
            {"label": "Duty", "option_text": "CIP supply and recirculation"},
            {"label": "Flow envelope", "option_text": "30 to 60 m3/h"},
        ],
        "objectives": [
            "Supply CIP: Achieve qualified flow or line velocity",
            "Protect NPSH: Stay above vendor NPSHR with margin",
        ],
        "failure_modes": ["Cavitation", "Deadhead", "Dry running"],
        "evaluation_options": [
            {
                "name": "High-head sanitary centrifugal",
                "fit": "best",
                "industrial_applications": ["CIP supply", "hot caustic recirculation"],
                "pros": ["Hygienic", "VFD turndown", "Broad vendor availability"],
                "cons": ["Needs NPSH protection", "Seal-flush duty"],
                "manufacturers": ["Alfa Laval LKH", "SPX FLOW"],
            }
        ],
        "evaluation_matrix": [
            {
                "option": "High-head sanitary centrifugal",
                "technical_fit": "High",
                "gmp": "High",
                "scale_up_risk": "Low",
                "cost_schedule": "Moderate",
                "reliability": "Recommended",
            }
        ],
        "preliminary_specs": ["Materials: 316L stainless", "Drive: VFD"],
        "do_not_specify": ["PD lobe pump: Over-specified for CIP supply"],
        "manufacturers": ["Alfa Laval LKH", "SPX FLOW"],
        "datasheet_markdown": """# CIP System Pump Evaluation

## Suggested operating recipe for qualification

- Fill and vent the circuit before starting the pump.

## Options not recommended as primary basis

| Technology | Reason not primary for this DIR |
| --- | --- |
| PD lobe pump | Over-specified for CIP supply |

## References reviewed

- Vendor hygienic centrifugal CIP application notes.
""",
    }
    assert evaluation_title_lines(result) == ["CIP System Pump", "Evaluation"]
    docx = build_evaluation_docx(result, output_path=tmp_path / "CIP System Pump Evaluation.docx")
    assert docx.name == "CIP System Pump Evaluation.docx"
    text = evaluation_docx_text(docx)
    assert "CIP System Pump Evaluation" in text
    assert "Recommendation in one line" in text
    assert "1. Design basis from DIR code" in text
    assert "Best-fit pump-system shortlist" in text
    assert "High-head sanitary centrifugal" in text
    assert "Specification item" in text
    assert "PD lobe pump" in text
    assert "Over-specified for CIP supply" in text
    assert "Technology" in text
    assert "Reason not primary for this DIR" in text
    assert "VFD turndown" in text
    assert "Needs NPSH protection" in text
    assert "Selected basis:" in text
    assert "<br" not in text.lower()
    assert "<b>" not in text.lower()
    assert "</b>" not in text.lower()
    assert "&lt;b" not in text.lower()
    pptx = build_evaluation_pptx(result, output_path=tmp_path / "CIP System Pump Evaluation.pptx")
    assert pptx.name == "CIP System Pump Evaluation.pptx"
    prs = Presentation(str(pptx))
    title_text = "\n".join(shape.text_frame.text for shape in prs.slides[0].shapes if shape.has_text_frame)
    assert "CIP System Pump" in title_text
    assert "Evaluation" in title_text
    assert "Fluid-Transfer" not in title_text
    assert "Step" in text
    assert "Objective" in text
    assert "Key control" in text
    assert "Supply CIP" in text
    assert "Achieve qualified flow" in text


def test_pdf_objectives_table_ignores_wrong_markdown_and_uses_json(tmp_path: Path):
    from bpeai_creator_sdk import build_evaluation_docx
    from bpeai_creator_sdk.artifacts import evaluation_docx_text

    result = {
        "system_name": "CIP Return Pump",
        "evaluated_item": "pump",
        "dir_code": "2-2-2-2-2-2",
        "selected_model": "Hygienic self-priming centrifugal",
        "recommended_basis": "Hygienic self-priming centrifugal for CIP return.",
        "objectives": [
            "Establish return flow: Meet qualified circuit velocity or other approved cleaning criterion.",
            "Maintain stable operation: Control startup, liquid-full, minimum-flow, and changing-pressure cases.",
            "Manage intermittent gas: Recover prime without persistent air-lock, damaging vibration, or uncontrolled cycling.",
            "Protect NPSH margin: Evaluate highest temperature, lowest suction level, and maximum credible flow.",
        ],
        "failure_modes": [
            "Loss of prime or air-lock collapses return flow and cleaning exposure.",
            "Cavitation under hot, low-suction conditions damages seals and internals.",
        ],
        "evaluation_options": [
            {
                "name": "Hygienic self-priming centrifugal",
                "fit": "best",
                "pros": ["Air handling"],
                "cons": ["NPSH"],
            }
        ],
        "datasheet_markdown": """# CIP Return Pump Evaluation

## Pump objectives and failure modes

| Topic | Description |
| --- | --- |
| Do not assume flooded suction | CIP return may see air and two-phase flow |
| Loss of prime | collapses return flow |

Failure modes: dry running damages seals.
""",
    }
    docx = build_evaluation_docx(result, output_path=tmp_path / "cip-return-objectives.docx")
    text = evaluation_docx_text(docx)
    assert "Step" in text
    assert "Objective" in text
    assert "Key control" in text
    assert "Establish return flow" in text
    assert "Meet qualified circuit velocity" in text
    assert "Protect NPSH margin" in text
    assert "Do not assume flooded suction" not in text


def test_pdf_objectives_table_uses_matching_markdown(tmp_path: Path):
    from bpeai_creator_sdk import build_evaluation_docx
    from bpeai_creator_sdk.artifacts import evaluation_docx_text

    result = {
        "system_name": "Media Preparation Vessel",
        "evaluated_item": "agitator",
        "dir_code": "2-1-2-3-1-1",
        "selected_model": "Top-entry axial hydrofoil",
        "recommended_basis": "Top-entry VFD sanitary agitator with a low-shear axial hydrofoil.",
        "objectives": ["Wrong JSON objective: should not appear"],
        "failure_modes": ["Surface vortexing and foam."],
        "evaluation_options": [
            {
                "name": "Top-entry axial hydrofoil",
                "fit": "best",
                "pros": ["Low foam"],
                "cons": ["Seal care"],
            }
        ],
        "datasheet_markdown": """# Media Preparation Vessel

## Mixing objectives and failure modes

| Topic | Description |
| --- | --- |
| Ignore this | Wrong first table |

| Step | Objective | Key control |
| --- | --- | --- |
| 1 | Charge water/WFI/PW | Establish recirculating axial flow before powder charge. |
| 2 | Wet dry powder | Avoid dry rafts, fisheyes, wall/baffle deposits, and dust release. |
""",
    }
    docx = build_evaluation_docx(result, output_path=tmp_path / "media-prep-objectives.docx")
    text = evaluation_docx_text(docx)
    assert "Step" in text
    assert "Objective" in text
    assert "Key control" in text
    assert "Charge water/WFI/PW" in text
    assert "Establish recirculating axial flow" in text
    assert "Wrong JSON objective" not in text
    assert "Ignore this" not in text


def test_pdf_unknown_tbd_design_basis_states_assumption(tmp_path: Path):
    from bpeai_creator_sdk import build_evaluation_docx
    from bpeai_creator_sdk.artifacts import evaluation_docx_text

    result = {
        "system_name": "CIP Return Pump",
        "evaluated_item": "pump",
        "dir_code": "4-1-2",
        "selected_model": "Hygienic self-priming centrifugal",
        "recommended_basis": "Preliminary self-priming hygienic centrifugal for CIP return.",
        "rationale": "Fit",
        "creator_attribution": {"display_name": "test", "app_id": "pump_selector"},
        "decoded_dir": [
            {
                "label": "Return flow envelope",
                "option_text": "Unknown / TBD — not yet defined",
                "unknown": True,
            },
            {
                "label": "Hygienic duty",
                "option_text": "Product-contact CIP return",
                "unknown": False,
            },
        ],
        "evaluation_options": [
            {
                "name": "Hygienic self-priming centrifugal",
                "fit": "best",
                "pros": ["Air handling"],
                "cons": ["NPSH"],
            }
        ],
        "datasheet_markdown": "# CIP Return Pump Evaluation\n",
    }
    docx = build_evaluation_docx(result, output_path=tmp_path / "tbd.docx")
    text = evaluation_docx_text(docx)
    assert "Unknown / TBD" in text
    assert "most likely" in text.lower()
    assert "Product-contact CIP return" in text


def test_pdf_exclusions_table_is_two_column_technology_reason(tmp_path: Path):
    from bpeai_creator_sdk import build_evaluation_docx
    from bpeai_creator_sdk.artifacts import evaluation_docx_text

    result = {
        "system_name": "CIP Return Pump",
        "evaluated_item": "pump",
        "dir_code": "2-2-2-2-2-2",
        "selected_model": "Hygienic self-priming liquid-ring",
        "recommended_basis": "Hygienic self-priming liquid-ring pump for CIP return.",
        "evaluation_options": [
            {
                "name": "Hygienic self-priming liquid-ring",
                "fit": "best",
                "pros": ["Air handling"],
                "cons": ["NPSH"],
            }
        ],
        "do_not_specify": [
            "Close-clearance hygienic circumferential-piston pump: Pulsation and overpressure on CIP return.",
            "Peristaltic hose pump: Not a hygienic CIP-return duty pump.",
        ],
        "datasheet_markdown": """# CIP Return Pump Evaluation

## Options not recommended as primary basis

| Do not specify as primary basis |
| --- |
| Rotary-lobe pump: Over-specified for low-viscosity CIP return with air |
| Air-operated double-diaphragm pump: Poor CIP return NPSH and drainability |
""",
    }
    docx = build_evaluation_docx(result, output_path=tmp_path / "cip-return-exclusions.docx")
    text = evaluation_docx_text(docx)
    assert "Technology" in text
    assert "Reason not primary for this DIR" in text
    assert "Rotary-lobe pump" in text
    assert "Over-specified for low-viscosity CIP return with air" in text
    assert "Air-operated double-diaphragm pump" in text
    # One-column leftover heading must not be the table.
    assert "Do not specify as primary basis" not in text


def test_pdf_exclusions_splits_long_technology_names_from_json(tmp_path: Path):
    from bpeai_creator_sdk import build_evaluation_docx
    from bpeai_creator_sdk.artifacts import evaluation_docx_text

    result = {
        "system_name": "CIP Return Pump",
        "evaluated_item": "pump",
        "dir_code": "2-2-2-2-2-2",
        "selected_model": "Hygienic self-priming liquid-ring",
        "recommended_basis": "Hygienic self-priming liquid-ring pump for CIP return.",
        "evaluation_options": [
            {"name": "Hygienic self-priming liquid-ring", "fit": "best", "pros": ["Air"], "cons": ["NPSH"]}
        ],
        "do_not_specify": [
            "Close-clearance hygienic circumferential-piston pump: Pulsation and overpressure on CIP return."
        ],
        "datasheet_markdown": "# CIP Return Pump Evaluation\n",
    }
    docx = build_evaluation_docx(result, output_path=tmp_path / "cip-return-excl-json.docx")
    text = evaluation_docx_text(docx)
    blob = " ".join(text.split())
    assert "Technology" in text
    assert "Reason not primary for this DIR" in text
    assert "Close-clearance hygienic circumferential-piston pump" in blob
    assert "Pulsation and overpressure on CIP return." in blob
    assert "Close-clearance hygienic circumferential-piston pump: Pulsation" not in blob


def test_format_evaluation_mentions_pptx_prompt():
    text = format_result_text(
        {
            "phase": "evaluation",
            "schema_version": "equipment_selector_v1",
            "system_name": "Media Prep",
            "dir_code": "2-1-2-3-1-1",
            "selected_model": "Hydrofoil",
            "recommended_basis": "Hydrofoil",
            "rationale": "Fit",
            "mixing_options": [{"name": "Hydrofoil", "fit": "best", "pros": ["low foam"]}],
            "pptx_prompt": "Would you like a presentation-ready PPTX file? Reply pptx or y.",
        }
    )
    assert "Recommended basis" in text
    assert "pptx" in text.lower()


def test_validate_preserves_session_extras_when_merged():
    """run_agent merges validated fields back onto extras used for pptx session."""
    raw = {
        "schema_version": "equipment_selector_v1",
        "equipment_tag": "AG-101",
        "selected_model": "Hydrofoil",
        "equipment_system": "mixing",
        "rationale": "Fit",
        "creator_attribution": {"display_name": "T", "app_id": "equipment_evaluator"},
        "phase": "evaluation",
        "system_name": "Media Prep Vessel",
        "application": "biopharmaceutical",
        "dir_code": "3-1-3-3-3-4",
        "pptx_prompt": "Reply pptx or y.",
        "artifacts": {"markdown_path": "artifacts/x.md"},
    }
    assert is_selector_result(raw)
    validated = validate_output(raw).model_dump()
    # Bare validate strips extras (the bug that broke pptx session storage).
    assert "phase" not in validated or validated.get("phase") is None
    merged = dict(raw)
    merged.update(validated)
    assert merged["phase"] == "evaluation"
    assert merged["dir_code"] == "3-1-3-3-3-4"
    assert merged["system_name"] == "Media Prep Vessel"
    assert merged["selected_model"] == "Hydrofoil"
