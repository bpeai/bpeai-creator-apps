from __future__ import annotations

from bpeai_creator_sdk import (
    CreatorAppManifest,
    EquipmentSelectorOutput,
    KeySpecValue,
    output_to_equipment_row,
    validate_output,
)


def test_validate_output_minimal():
    data = {
        "schema_version": "equipment_selector_v1",
        "equipment_tag": "MX-101",
        "selected_model": "Top-entry axial hydrofoil agitator",
        "equipment_system": "mixing",
        "key_specs": [{"key": "power_kw", "value": 15, "unit": "kW"}],
        "rationale": "Best fit for low-shear dissolution.",
        "creator_attribution": {"display_name": "BPEAI", "app_id": "agitator_duty_impeller_matcher"},
    }
    out = validate_output(data)
    assert out.equipment_tag == "MX-101"


def test_output_to_equipment_row():
    out = EquipmentSelectorOutput(
        equipment_tag="AG-101",
        selected_model="Hydrofoil agitator",
        equipment_system="mixing",
        key_specs=[KeySpecValue(key="speed_rpm", value=60, unit="RPM")],
        rationale="Low-shear dissolution duty.",
        creator_attribution={"display_name": "BPEAI", "app_id": "test"},
    )
    row = output_to_equipment_row(out)
    assert row["preliminary_tag"] == "AG-101"
    assert row["equipment_name"] == "Hydrofoil agitator"


def test_manifest_model():
    m = CreatorAppManifest(
        id="test",
        slug="test",
        label="Test Selector",
        equipment_system="mixing",
        author={"creator_id": "x", "display_name": "X"},
        route="/test",
    )
    assert m.output_schema_version == "equipment_selector_v1"
