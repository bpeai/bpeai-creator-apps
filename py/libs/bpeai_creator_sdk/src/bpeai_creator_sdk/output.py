from __future__ import annotations

import uuid
from collections.abc import Mapping
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
    "EI_RESULT_MANIFEST_VERSION",
    "EQUIPMENT_SELECTOR_SCHEMA_REF",
    "EQUIPMENT_EVALUATOR_OUTPUT_PORT",
    "CreatorAttribution",
    "KeySpecValue",
    "EvaluationMatrixRow",
    "EvaluationOption",
    "EquipmentSelectorOutput",
    "EiResultOutput",
    "EiResultManifest",
    "validate_output",
    "validate_result_manifest",
    "wrap_evaluator_result",
    "unwrap_evaluator_result",
    "output_to_equipment_row",
    "coerce_string_list_items",
]

EI_RESULT_MANIFEST_VERSION = "ei_result_manifest_v1"
EQUIPMENT_SELECTOR_SCHEMA_REF = "https://bpeai.com/schemas/equipment-selector/v1"
EQUIPMENT_EVALUATOR_OUTPUT_PORT = "equipment_selection"


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

# LLM-facing string arrays that are often emitted as {key, value} objects.
_STRING_LIST_FIELDS = (
    "objectives",
    "failure_modes",
    "do_not_specify",
    "preliminary_specs",
    "manufacturers",
    "source_basis",
)


def _coerce_string_list_item(item: Any) -> str:
    """Turn a list item into a display string.

    Models frequently copy the key_specs {key, value, unit?} shape onto
    preliminary_specs and other string arrays.
    """
    if item is None:
        return ""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, Mapping):
        key = item.get("key")
        value = item.get("value")
        unit = item.get("unit")
        if key is not None or value is not None:
            label = str(key or "").strip()
            val = "" if value is None else str(value).strip()
            unit_s = str(unit).strip() if unit not in (None, "") else ""
            if unit_s:
                val = f"{val} {unit_s}".strip() if val else unit_s
            if label and val:
                return f"{label}: {val}"
            return val or label
        parts = []
        for k, v in item.items():
            if v is None:
                continue
            parts.append(f"{k}: {v}")
        return ", ".join(parts)
    return str(item).strip()


def coerce_string_list_items(items: Any) -> list[str]:
    """Coerce a string, dict, or list (including {key, value} objects) to List[str]."""
    if items is None:
        return []
    if isinstance(items, str):
        text = items.strip()
        return [text] if text else []
    if isinstance(items, Mapping):
        text = _coerce_string_list_item(items)
        return [text] if text else []
    if not isinstance(items, list):
        text = str(items).strip()
        return [text] if text else []
    out: list[str] = []
    for item in items:
        text = _coerce_string_list_item(item)
        if text:
            out.append(text)
    return out


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
        for field in _STRING_LIST_FIELDS:
            if field in data:
                data[field] = coerce_string_list_items(data[field])
        return data


class EiResultOutput(BaseModel):
    """One typed value emitted by an EI app."""

    port_id: str
    schema_ref: str
    value: Any
    label: str = ""


class EiResultManifest(BaseModel):
    """Deliverable-neutral result envelope used for EI app composition."""

    schema_version: Literal["ei_result_manifest_v1"] = "ei_result_manifest_v1"
    template_family: str = "equipment_evaluator"
    run: Dict[str, Any] = Field(default_factory=dict)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    outputs: List[EiResultOutput] = Field(default_factory=list)
    artifacts: Dict[str, Any] = Field(default_factory=dict)


def validate_result_manifest(data: Dict[str, Any]) -> EiResultManifest:
    return EiResultManifest.model_validate(data)


def wrap_evaluator_result(
    data: Dict[str, Any] | EquipmentSelectorOutput,
    *,
    output_port_id: str = EQUIPMENT_EVALUATOR_OUTPUT_PORT,
    run: Dict[str, Any] | None = None,
    inputs: Dict[str, Any] | None = None,
) -> EiResultManifest:
    """Wrap equipment_selector_v1 without changing its payload contract."""
    output = data if isinstance(data, EquipmentSelectorOutput) else validate_output(data)
    payload = output.model_dump()
    return EiResultManifest(
        template_family="equipment_evaluator",
        run=run or {},
        inputs=inputs or {},
        result=payload,
        outputs=[
            EiResultOutput(
                port_id=output_port_id,
                label="Equipment selection",
                schema_ref=EQUIPMENT_SELECTOR_SCHEMA_REF,
                value=payload,
            )
        ],
        artifacts=output.artifacts,
    )


def unwrap_evaluator_result(
    data: Dict[str, Any] | EiResultManifest | EquipmentSelectorOutput,
) -> EquipmentSelectorOutput:
    """Read either a generic envelope or the legacy bare evaluator payload."""
    if isinstance(data, EquipmentSelectorOutput):
        return data
    manifest = data if isinstance(data, EiResultManifest) else validate_result_manifest(data)
    if isinstance(manifest.result, dict):
        return EquipmentSelectorOutput.model_validate(manifest.result)
    for item in manifest.outputs:
        if (
            item.port_id == EQUIPMENT_EVALUATOR_OUTPUT_PORT
            or item.schema_ref == EQUIPMENT_SELECTOR_SCHEMA_REF
        ):
            if not isinstance(item.value, dict):
                raise ValueError("equipment evaluator output value must be an object")
            return EquipmentSelectorOutput.model_validate(item.value)
    raise ValueError("result manifest has no equipment_selector_v1 output")


def validate_output(data: Dict[str, Any] | EiResultManifest) -> EquipmentSelectorOutput:
    if isinstance(data, EiResultManifest) or data.get("schema_version") == EI_RESULT_MANIFEST_VERSION:
        return unwrap_evaluator_result(data)
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
