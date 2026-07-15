from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Union

from pydantic import BaseModel, Field

OUTPUT_SCHEMA_VERSION = "equipment_selector_v1"


class CreatorAttribution(BaseModel):
    display_name: str
    app_id: str


class KeySpecValue(BaseModel):
    key: str
    value: Union[str, int, float, bool]
    unit: str | None = None


class EquipmentSelectorOutput(BaseModel):
    schema_version: Literal["equipment_selector_v1"] = "equipment_selector_v1"
    equipment_tag: str
    selected_model: str
    equipment_system: str
    equipment_name: str = ""
    equipment_category: str = "Mixing"
    key_specs: List[KeySpecValue] = Field(default_factory=list)
    rationale: str
    creator_attribution: CreatorAttribution
    datasheet_markdown: str = ""
    source_basis: List[str] = Field(default_factory=list)
    mixing_options: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_basis: str = ""
    manufacturers: List[str] = Field(default_factory=list)


def validate_output(data: Dict[str, Any]) -> EquipmentSelectorOutput:
    return EquipmentSelectorOutput.model_validate(data)


def output_to_equipment_row(output: EquipmentSelectorOutput, *, functional_area_label: str = "Equipment Intelligence") -> Dict[str, Any]:
    """Map selector output to vendor_api EquipmentRow-compatible dict."""
    design_params = [
        {
            "id": f"spec-{i}",
            "label": spec.key,
            "unit": spec.unit,
            "notes": str(spec.value),
        }
        for i, spec in enumerate(output.key_specs)
    ]
    return {
        "id": str(uuid.uuid4()),
        "preliminary_tag": output.equipment_tag,
        "functional_area_id": "equipment-intelligence",
        "functional_area_label": functional_area_label,
        "process_step_id": "ei-mixing",
        "process_step_label": "Equipment Intelligence — Mixing",
        "source_module_id": output.creator_attribution.app_id,
        "source_module_label": output.creator_attribution.display_name,
        "equipment_name": output.equipment_name or output.selected_model,
        "equipment_category": output.equipment_category,
        "quantity": 1,
        "sizing_basis": output.recommended_basis or output.rationale[:500],
        "capacity": None,
        "materials_of_construction": None,
        "utility_usage": {},
        "dimensions_approx": None,
        "design_parameters_needed": [],
        "typical_design_parameters": design_params,
        "utility_requirements": [],
        "gmp_criticality": "Per project URS",
        "single_use_applicability": "TBD",
        "stainless_steel_applicability": "TBD",
        "assumptions": output.source_basis,
        "warnings": [],
        "open_questions": [],
        "confidence": "preliminary",
        "source_basis": output.source_basis,
        "notes": output.rationale,
    }
