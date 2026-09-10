from __future__ import annotations

from pathlib import Path

from bpeai_creator_sdk.app_paths import resolve_app_dir


def _write_manifest(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "manifest.json").write_text("{}", encoding="utf-8")


def test_resolve_app_dir_family_leaf_does_not_collide_with_template(tmp_path: Path):
    py_root = tmp_path / "py"
    live = py_root / "apps" / "equipment_sizing" / "vessel_agitator"
    template = py_root / "apps" / "_templates" / "equipment_sizing"
    _write_manifest(live)
    _write_manifest(template)

    found = resolve_app_dir("equipment_sizing/vessel_agitator", py_root)
    assert found == live.resolve()


def test_resolve_app_dir_family_id_still_finds_template(tmp_path: Path):
    py_root = tmp_path / "py"
    template = py_root / "apps" / "_templates" / "equipment_sizing"
    family_pkg = py_root / "apps" / "equipment_sizing"
    family_pkg.mkdir(parents=True)
    (family_pkg / "__init__.py").write_text("", encoding="utf-8")
    _write_manifest(template)

    found = resolve_app_dir("equipment_sizing", py_root)
    assert found == template.resolve()
