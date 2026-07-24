from __future__ import annotations

from pathlib import Path

import pytest

from bpeai_creator_sdk.local_format import format_dir_text, format_result_text
from bpeai_creator_sdk.local_parse import parse_inputs_heuristic
from bpeai_creator_sdk.local_run import is_selector_result, repo_py_root
from bpeai_creator_sdk.sme import (
    load_knowledge_pack,
    resolve_scenario_id,
    validate_dir_code,
)


@pytest.fixture(scope="module")
def py_root() -> Path:
    # tests/ → bpeai_creator_sdk/ → libs/ → py/
    return Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def mixing_pack(py_root: Path):
    return load_knowledge_pack("mixing", py_root=py_root)


def test_repo_py_root_finds_knowledge(py_root: Path):
    root = repo_py_root(py_root)
    assert (root / "knowledge" / "mixing" / "pack.yaml").is_file()


def test_load_mixing_pack(mixing_pack):
    assert mixing_pack.pack_id == "mixing"
    assert mixing_pack.equipment_system == "mixing"
    assert "media_preparation" in mixing_pack.scenarios
    assert mixing_pack.option_names()
    assert mixing_pack.fragment("role")
    assert mixing_pack.fragment("depth_requirements")
    system = mixing_pack.build_system_prompt()
    assert "Minimum depth bar" in system or "depth" in system.lower()


def test_thin_report_sections():
    from bpeai_creator_sdk.sme import thin_report_sections

    headings = ["Design basis", "Option evaluation"]
    thin_md = "## Design basis\nShort.\n\n## Option evaluation\nAlso thin.\n"
    assert thin_report_sections(thin_md, headings, min_chars=120) == headings

    rich_md = (
        "## Design basis\n"
        + ("This selection implication explains volume, vessel format, solids handling, "
           "and why axial hydrofoil agitation is preferred for this DIR. " * 3)
        + "\n\n## Option evaluation\n"
        + ("Each option is compared on industrial applications, pros, cons, and vendors. " * 4)
    )
    assert thin_report_sections(rich_md, headings, min_chars=120) == []

    # Nested ## under # Option evaluation should count toward depth
    nested = (
        "# Option evaluation\n"
        "## Option 1\n"
        + ("Detailed industrial applications pros cons manufacturers and DIR fit. " * 5)
        + "\n# Do not specify\n"
        + ("Exclude high-shear options for this DIR. " * 3)
    )
    assert thin_report_sections(nested, ["Option evaluation"], min_chars=120) == []


def test_resolve_scenario_aliases(mixing_pack):
    assert resolve_scenario_id(mixing_pack, "Media Preparation Vessel") == "media_preparation"
    assert (
        resolve_scenario_id(mixing_pack, "Chromatography resin slurry tank")
        == "chromatography_resin_slurry"
    )


def test_validate_dir_code_ok(mixing_pack):
    result = validate_dir_code(mixing_pack, "media_preparation", "2-1-2-3-1-1")
    assert result.ok
    assert len(result.decoded) == 6


def test_validate_dir_code_bad_length(mixing_pack):
    result = validate_dir_code(mixing_pack, "media_preparation", "2-1-2")
    assert not result.ok
    assert "Expected 6" in result.error
    assert result.suggested_correction


def test_validate_dir_code_out_of_range(mixing_pack):
    result = validate_dir_code(mixing_pack, "media_preparation", "9-1-2-3-1-1")
    assert not result.ok


def test_parse_dir_code_heuristic():
    parsed = parse_inputs_heuristic("2-1-2-3-1-1")
    assert parsed.get("dir_code") == "2-1-2-3-1-1"
    assert parsed.get("phase") == "evaluate"
    assert "system_name" not in parsed


def test_is_selector_result_skips_dir():
    assert not is_selector_result({"phase": "dir_requirements", "requirements": []})
    assert is_selector_result(
        {
            "schema_version": "equipment_selector_v1",
            "equipment_tag": "MX-101",
            "selected_model": "Hydrofoil",
            "rationale": "fit",
        }
    )


def test_format_dir_text():
    text = format_dir_text(
        {
            "phase": "dir_requirements",
            "system_name": "Media Prep",
            "application": "biopharmaceutical",
            "requirements": [
                {
                    "index": 1,
                    "label": "Working volume",
                    "options": [{"index": 1, "text": "50–250 L"}],
                }
            ],
            "common_codes": ["2-1-2-3-1-1"],
            "message": "Reply with a DIR code.",
        }
    )
    assert "Design Input Requirements" in text
    assert "Working volume" in text
    assert "2-1-2-3-1-1" in text
    assert format_result_text({"phase": "dir_requirements", "requirements": []}).startswith(
        "Design Input"
    )
