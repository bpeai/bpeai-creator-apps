from __future__ import annotations

from pathlib import Path

import pytest

from bpeai_creator_sdk.local_format import format_dir_text, format_result_text
from bpeai_creator_sdk.local_parse import parse_inputs_heuristic
from bpeai_creator_sdk.local_run import is_selector_result, repo_py_root
from bpeai_creator_sdk.sme import (
    list_missing_pack_files,
    load_knowledge_pack,
    pack_is_loadable,
    resolve_dir_menu,
    resolve_scenario_id,
    stamp_draft_meta,
    validate_dir_code,
    write_pack_file,
)


@pytest.fixture(scope="module")
def py_root() -> Path:
    # tests/ → bpeai_creator_sdk/ → libs/ → py/
    return Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def examples_root(py_root: Path) -> Path:
    return py_root / "knowledge" / "_examples"


@pytest.fixture(scope="module")
def mixing_stub(py_root: Path, examples_root: Path):
    return load_knowledge_pack("mixing_stub", py_root=py_root, pack_root=examples_root)


def test_repo_has_example_stub_not_production_packs(py_root: Path):
    root = repo_py_root(py_root)
    assert (root / "knowledge" / "_examples" / "mixing_stub" / "pack.yaml").is_file()
    assert not (root / "knowledge" / "mixing").is_dir()
    assert not (root / "knowledge" / "filtration").is_dir()


def test_load_mixing_stub(mixing_stub):
    assert mixing_stub.pack_id == "mixing_stub"
    assert mixing_stub.equipment_system == "mixing"
    assert "media_preparation" in mixing_stub.scenarios
    assert mixing_stub.option_names()
    assert mixing_stub.fragment("role")
    assert mixing_stub.fragment("depth_requirements")
    system = mixing_stub.build_system_prompt()
    assert "depth" in system.lower() or "EXAMPLE" in system or "example" in system.lower()


def test_pack_bootstrap_inventory(py_root: Path, examples_root: Path, tmp_path: Path):
    assert pack_is_loadable("mixing_stub", py_root=py_root, pack_root=examples_root)
    assert (
        list_missing_pack_files(
            "mixing_stub",
            py_root=py_root,
            pack_root=examples_root,
            include_optional=False,
        )
        == []
    )
    path = write_pack_file(
        "demo_pack",
        "pack.yaml",
        stamp_draft_meta(
            {"label": "Demo"},
            pack_id="demo_pack",
            equipment_system="demo",
        ),
        py_root=tmp_path,
        draft=True,
    )
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "draft_pending_sme_approval" in text or "DRAFT" in text
    missing = list_missing_pack_files("demo_pack", py_root=tmp_path, include_optional=False)
    assert "dir_requirements.yaml" in missing
    assert not pack_is_loadable("demo_pack", py_root=tmp_path)


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

    nested = (
        "# Option evaluation\n"
        "## Option 1\n"
        + ("Detailed industrial applications pros cons manufacturers and DIR fit. " * 5)
        + "\n# Do not specify\n"
        + ("Exclude high-shear options for this DIR. " * 3)
    )
    assert thin_report_sections(nested, ["Option evaluation"], min_chars=120) == []


def test_resolve_scenario_aliases(mixing_stub):
    assert resolve_scenario_id(mixing_stub, "Media Preparation Vessel") == "media_preparation"


def test_resolve_dir_menu_industry_variant(mixing_stub):
    menu = resolve_dir_menu(
        mixing_stub,
        system_name="Media Preparation Vessel",
        industry="Biopharmaceuticals",
        equipment_system_variant="general_mixing",
        require_approved=True,
    )
    assert menu.scenario_id == "media_preparation"
    assert menu.industry == "Biopharmaceuticals"
    assert menu.is_approved
    assert len(menu.requirements) == 3


def test_validate_dir_code_ok(mixing_stub):
    result = validate_dir_code(mixing_stub, "media_preparation", "2-1-2")
    assert result.ok
    assert len(result.decoded) == 3


def test_validate_dir_code_bad_length(mixing_stub):
    result = validate_dir_code(mixing_stub, "media_preparation", "2-1")
    assert not result.ok
    assert "Expected 3" in result.error
    assert result.suggested_correction


def test_validate_dir_code_out_of_range(mixing_stub):
    result = validate_dir_code(mixing_stub, "media_preparation", "9-1-2")
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
            "common_codes": ["2-1-2"],
            "message": "Reply with a DIR code.",
        }
    )
    assert "Design Input Requirements" in text
    assert "Working volume" in text
    assert "2-1-2" in text
    assert format_result_text({"phase": "dir_requirements", "requirements": []}).startswith(
        "Design Input"
    )
