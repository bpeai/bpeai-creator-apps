from __future__ import annotations

from bpeai_creator_sdk import (
    CreatorAppManifest,
    EI_RESULT_MANIFEST_VERSION,
    EquipmentSelectorOutput,
    KeySpecValue,
    output_to_equipment_row,
    unwrap_evaluator_result,
    validate_output,
    wrap_evaluator_result,
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
    assert m.template_family == "equipment_evaluator"


def test_manifest_typed_ports_bridge_legacy_required_inputs():
    legacy = CreatorAppManifest(
        id="legacy",
        slug="legacy",
        label="Legacy",
        equipment_system="mixing",
        author={"creator_id": "x", "display_name": "X"},
        required_inputs=["system_name"],
        route="/legacy",
    )
    assert legacy.input_ports[0].schema_ref.endswith("/value/json/v1")

    typed = CreatorAppManifest(
        id="typed",
        slug="typed",
        label="Typed",
        equipment_system="mixing",
        author={"creator_id": "x", "display_name": "X"},
        input_ports=[
            {
                "id": "project_definition",
                "label": "Project definition",
                "schema_ref": "https://bpeai.com/schemas/project-definition/v1",
                "required": True,
            }
        ],
        route="/typed",
    )
    assert typed.required_inputs == ["project_definition"]


def test_evaluator_result_envelope_round_trip_and_legacy_adapter():
    payload = {
        "schema_version": "equipment_selector_v1",
        "equipment_tag": "MX-101",
        "selected_model": "Hydrofoil agitator",
        "equipment_system": "mixing",
        "key_specs": [],
        "rationale": "Suitable duty.",
        "creator_attribution": {"display_name": "BPEAI", "app_id": "test"},
    }
    envelope = wrap_evaluator_result(payload)
    assert envelope.schema_version == EI_RESULT_MANIFEST_VERSION
    assert envelope.result["schema_version"] == "equipment_selector_v1"
    assert envelope.outputs[0].value["schema_version"] == "equipment_selector_v1"
    assert unwrap_evaluator_result(envelope).equipment_tag == "MX-101"
    assert validate_output(envelope.model_dump()).selected_model == "Hydrofoil agitator"
    persisted = {
        "schema_version": "ei_result_manifest_v1",
        "run": {"id": "history-1"},
        "inputs": {"system_name": "MX-101"},
        "result": payload,
        "artifacts": {},
    }
    assert validate_output(persisted).equipment_tag == "MX-101"
    assert validate_output(payload).equipment_tag == "MX-101"
