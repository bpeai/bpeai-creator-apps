"""Pack brand.yaml / logo theme loading and artifact branding."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from PIL import Image


@pytest.fixture(scope="module")
def py_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_load_report_theme_defaults():
    from bpeai_creator_sdk.artifacts.theme import load_report_theme

    theme = load_report_theme(None)
    assert theme.navy == "17324D"
    assert theme.teal == "00A398"
    assert theme.display_font == "Aptos Display"
    assert theme.docx_font == "Calibri"
    assert theme.logo_path is None


def test_load_report_theme_pack_override_and_logo(tmp_path: Path):
    from bpeai_creator_sdk.artifacts.theme import load_report_theme

    style = tmp_path / "references" / "style"
    style.mkdir(parents=True)
    (style / "brand.yaml").write_text(
        yaml.safe_dump(
            {
                "colors": {"navy": "AABBCC", "teal": "112233"},
                "fonts": {"docx_font": "Georgia", "display": "Custom Display"},
            }
        ),
        encoding="utf-8",
    )
    logo = style / "logo.png"
    Image.new("RGB", (40, 20), color=(170, 187, 204)).save(logo)

    theme = load_report_theme(tmp_path, template_family="equipment_evaluator")
    assert theme.navy == "AABBCC"
    assert theme.teal == "112233"
    assert theme.header_bg == "AABBCC"
    assert theme.docx_font == "Georgia"
    assert theme.display_font == "Custom Display"
    assert theme.logo_path == logo.resolve()


def test_load_report_theme_outline_fallback(tmp_path: Path):
    from bpeai_creator_sdk.artifacts.theme import load_report_theme

    outline = {
        "style": {
            "colors": {"navy": "010203"},
            "fonts": {"body": "Outline Body"},
        }
    }
    theme = load_report_theme(tmp_path, outline=outline)
    assert theme.navy == "010203"
    assert theme.body_font == "Outline Body"


def test_seed_copies_brand_yaml_no_clobber(
    py_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from bpeai_creator_sdk.sme import seed_template_references, template_references_root

    monkeypatch.delenv("BPEAI_TEMPLATE_REFERENCES_ROOT", raising=False)
    monkeypatch.delenv("BPEAI_REFERENCES_ROOT", raising=False)
    shared = template_references_root(py_root, template_family="equipment_evaluator")
    assert shared is not None
    assert (shared / "brand.yaml").is_file()

    copied = seed_template_references(
        "_brand_seed_tmp",
        py_root=tmp_path,
        template_root=shared,
        template_family="equipment_evaluator",
    )
    dest = tmp_path / "knowledge" / "_brand_seed_tmp" / "references" / "style"
    assert any(p.endswith("brand.yaml") for p in copied)
    brand_path = dest / "brand.yaml"
    assert brand_path.is_file()
    brand_path.write_text("colors:\n  navy: 'FF0000'\n", encoding="utf-8")
    assert (
        seed_template_references(
            "_brand_seed_tmp",
            py_root=tmp_path,
            template_root=shared,
            template_family="equipment_evaluator",
        )
        == []
    )
    assert "FF0000" in brand_path.read_text(encoding="utf-8")


def _ooxml_blob_contains(path: Path, needle: str) -> bool:
    import zipfile

    target = needle.encode("ascii").lower()
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if name.endswith((".xml", ".rels")):
                if target in zf.read(name).lower():
                    return True
    return False


def test_pptx_and_docx_use_pack_navy(tmp_path: Path):
    from bpeai_creator_sdk.artifacts import build_evaluation_docx, build_evaluation_pptx

    style = tmp_path / "references" / "style"
    style.mkdir(parents=True)
    (style / "brand.yaml").write_text(
        yaml.safe_dump({"colors": {"navy": "DECADE"}}),
        encoding="utf-8",
    )
    logo = style / "logo.png"
    Image.new("RGB", (32, 16), color=(222, 202, 222)).save(logo)

    result = {
        "schema_version": "equipment_selector_v1",
        "template_family": "equipment_evaluator",
        "system_name": "Test Mixer",
        "dir_code": "LS-MIX-TEST",
        "selected_model": "Option A",
        "datasheet_markdown": "# Test Mixer\n\n## Recommendation\n\nUse Option A.\n",
        "options": [
            {
                "name": "Option A",
                "rating": 5,
                "pros": ["fits"],
                "cons": ["cost"],
            }
        ],
    }

    pptx_path = build_evaluation_pptx(
        result,
        output_path=tmp_path / "out.pptx",
        pack_path=tmp_path,
        template_family="equipment_evaluator",
    )
    docx_path = build_evaluation_docx(
        result,
        output_path=tmp_path / "out.docx",
        pack_path=tmp_path,
        template_family="equipment_evaluator",
    )
    assert _ooxml_blob_contains(pptx_path, "DECADE")
    assert _ooxml_blob_contains(docx_path, "DECADE")
