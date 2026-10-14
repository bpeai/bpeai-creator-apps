from pathlib import Path

from bpeai_creator_sdk.deliverables import default_deliverables, resolve_generate_flags


def test_family_defaults():
    assert default_deliverables("equipment_evaluator") == {"docx": True, "pptx": True, "xlsx": False}
    assert default_deliverables("equipment_sizing")["xlsx"] is True


def test_injected_flags_override_manifest(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"deliverables": {"docx": true, "pptx": true, "xlsx": true}}', encoding="utf-8")
    flags = resolve_generate_flags(
        {"generate_pptx": False, "generate_docx": False},
        template_family="equipment_sizing",
        manifest_path=manifest,
    )
    assert flags == {"docx": False, "pptx": False, "xlsx": True}


def test_manifest_used_when_run_omits_flags(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"deliverables": {"xlsx": false}}', encoding="utf-8")
    flags = resolve_generate_flags({}, template_family="equipment_sizing", manifest_path=manifest)
    assert flags["xlsx"] is False
    assert flags["docx"] is True
