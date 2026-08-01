from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Union

from pydantic import BaseModel, Field, model_validator

from .handshake import (
    OPTIONS_ALIAS,
    OPTIONS_FIELD,
    OUTPUT_SCHEMA_VERSION,
    normalize_options_fields,
)

# Re-export for callers that imported from output
__all__ = [
    "OUTPUT_SCHEMA_VERSION",
    "CreatorAttribution",
    "KeySpecValue",
    "EvaluationMatrixRow",
    "EvaluationOption",
    "EquipmentSelectorOutput",
    "validate_output",
    "output_to_equipment_row",
]


class CreatorAttribution(BaseModel):
    display_name: str
    app_id: str


class KeySpecValue(BaseModel):
    key: str
    value: Union[str, int, float, bool]
    unit: str | None = None


class EvaluationMatrixRow(BaseModel):
    option: str = ""
    technical_fit: str = ""
    gmp: str = ""
    scale_up_risk: str = ""
    cost_schedule: str = ""
    reliability: str = ""
    rank: int | None = None


class EvaluationOption(BaseModel):
    """Technology / design option with pros/cons (domain-agnostic)."""

    name: str
    fit: str | None = None
    industrial_applications: List[str] = Field(default_factory=list)
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    manufacturers: List[str] = Field(default_factory=list)


# Backward-compat alias name used in older TS / prompts
MixingOption = EvaluationOption


class EquipmentSelectorOutput(BaseModel):
    schema_version: Literal["equipment_selector_v1"] = "equipment_selector_v1"
    equipment_tag: str
    selected_model: str
    equipment_system: str
    equipment_name: str = ""
    equipment_category: str = ""
    key_specs: List[KeySpecValue] = Field(default_factory=list)
    rationale: str
    creator_attribution: CreatorAttribution
    datasheet_markdown: str = ""
    source_basis: List[str] = Field(default_factory=list)
    # Canonical field for all equipment systems (mixing, filtration, …)
    evaluation_options: List[Dict[str, Any]] = Field(default_factory=list)
    # Compat alias — same content as evaluation_options after validate_output
    mixing_options: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_basis: str = ""
    manufacturers: List[str] = Field(default_factory=list)
    design_basis: str = ""
    dir_summary: str = ""
    objectives: List[str] = Field(default_factory=list)
    failure_modes: List[str] = Field(default_factory=list)
    evaluation_matrix: List[Dict[str, Any]] = Field(default_factory=list)
    alternate_basis: str = ""
    do_not_specify: List[str] = Field(default_factory=list)
    preliminary_specs: List[str] = Field(default_factory=list)
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    handshake_protocol: str = "ei_handshake_v1"

    @model_validator(mode="before")
    @classmethod
    def _alias_options_and_category(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalize_options_fields(data)
        if not str(data.get("equipment_category") or "").strip():
            sys_name = str(data.get("equipment_system") or "").strip()
            data["equipment_category"] = (
                sys_name.replace("_", " ").title() if sys_name else "Equipment"
            )
        data.setdefault("handshake_protocol", "ei_handshake_v1")
        data.setdefault("schema_version", OUTPUT_SCHEMA_VERSION)
        return data


def validate_output(data: Dict[str, Any]) -> EquipmentSelectorOutput:
    payload = dict(data or {})
    normalize_options_fields(payload)
    return EquipmentSelectorOutput.model_validate(payload)


def output_to_equipment_row(
    output: EquipmentSelectorOutput,
    *,
    functional_area_label: str = "Equipment Intelligence",
) -> Dict[str, Any]:
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
    system = output.equipment_system or "equipment"
    return {
        "id": str(uuid.uuid4()),
        "preliminary_tag": output.equipment_tag,
        "functional_area_id": "equipment-intelligence",
        "functional_area_label": functional_area_label,
        "process_step_id": f"ei-{system}",
        "process_step_label": f"Equipment Intelligence — {output.equipment_category or system}",
        "source_module_id": output.creator_attribution.app_id,
        "source_module_label": output.creator_attribution.display_name,
        "equipment_name": output.equipment_name or output.selected_model,
        "equipment_category": output.equipment_category or system,
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
