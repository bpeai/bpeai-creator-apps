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
    "SIZING_SCHEMA_VERSION",
    "EI_RESULT_MANIFEST_VERSION",
    "EQUIPMENT_SELECTOR_SCHEMA_REF",
    "EQUIPMENT_SIZING_SCHEMA_REF",
    "EQUIPMENT_EVALUATOR_OUTPUT_PORT",
    "EQUIPMENT_SIZING_OUTPUT_PORT",
    "CreatorAttribution",
    "KeySpecValue",
    "QuantitySpec",
    "ConnectionSpec",
    "DimensionSpec",
    "EvaluationMatrixRow",
    "EvaluationOption",
    "EquipmentSelectorOutput",
    "EquipmentSizingOutput",
    "EiResultOutput",
    "EiResultManifest",
    "validate_output",
    "validate_result_manifest",
    "wrap_evaluator_result",
    "wrap_sizing_result",
    "unwrap_evaluator_result",
    "unwrap_result_payload",
    "output_to_equipment_row",
    "coerce_string_list_items",
    "apply_user_identity",
    "canonicalize_equipment_tag",
]

EI_RESULT_MANIFEST_VERSION = "ei_result_manifest_v1"
EQUIPMENT_SELECTOR_SCHEMA_REF = "https://bpeai.com/schemas/equipment-selector/v1"
EQUIPMENT_SIZING_SCHEMA_REF = "https://bpeai.com/schemas/equipment-sizing/v1"
EQUIPMENT_EVALUATOR_OUTPUT_PORT = "equipment_selection"
EQUIPMENT_SIZING_OUTPUT_PORT = "equipment_sizing"
SIZING_SCHEMA_VERSION = "equipment_sizing_v1"


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
    equipment_item_name: str = ""
    equipment_system_name: str = ""
    equipment_system_tag: str = ""
    composition_role: str = ""
    source_module_id: str = ""
    source_module_label: str = ""
    core_equipment_module_id: str = ""
    core_equipment_module_label: str = ""
    functional_area_id: str = ""
    functional_area_label: str = ""
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


def _quantity_from_unknown(raw: Any) -> Dict[str, str]:
    if raw is None:
        return {"value": "", "unit": "", "basis": ""}
    if isinstance(raw, Mapping):
        return {
            "value": str(raw.get("value") or raw.get("envelope") or "").strip(),
            "unit": str(raw.get("unit") or "").strip(),
            "basis": str(raw.get("basis") or raw.get("method") or "").strip(),
        }
    text = str(raw).strip()
    return {"value": text, "unit": "", "basis": ""}


class QuantitySpec(BaseModel):
    value: str = ""
    unit: str = ""
    basis: str = ""


class ConnectionSpec(BaseModel):
    name: str
    size: str = ""
    unit: str = ""
    service: str = ""
    basis: str = ""


class DimensionSpec(BaseModel):
    value: str = ""
    unit: str = ""
    method: str = ""
    length: str | None = None
    width: str | None = None
    height: str | None = None


class EquipmentSizingOutput(BaseModel):
    schema_version: Literal["equipment_sizing_v1"] = "equipment_sizing_v1"
    equipment_tag: str
    equipment_name: str = ""
    equipment_item_name: str = ""
    equipment_system: str = ""
    equipment_system_name: str = ""
    equipment_system_tag: str = ""
    composition_role: str = ""
    source_module_id: str = ""
    source_module_label: str = ""
    core_equipment_module_id: str = ""
    core_equipment_module_label: str = ""
    functional_area_id: str = ""
    functional_area_label: str = ""
    equipment_type: str = ""
    equipment_category: str = ""
    capacity: QuantitySpec = Field(default_factory=QuantitySpec)
    connections: List[ConnectionSpec] = Field(default_factory=list)
    dimensions: DimensionSpec = Field(default_factory=DimensionSpec)
    utilities: str = ""
    inputs_used: List[str] = Field(default_factory=list)
    missing_inputs: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    source_basis: List[str] = Field(default_factory=list)
    datasheet_markdown: str = ""
    creator_attribution: CreatorAttribution
    handshake_protocol: str = "ei_handshake_v1"
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    # PPTX / hub display alias — not part of the sizing field catalog.
    selected_model: str = ""
    key_specs: List[KeySpecValue] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_sizing(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        payload.setdefault("schema_version", SIZING_SCHEMA_VERSION)
        payload.setdefault("handshake_protocol", "ei_handshake_v1")
        cap = _quantity_from_unknown(payload.get("capacity"))
        payload["capacity"] = cap
        dim_raw = payload.get("dimensions")
        if isinstance(dim_raw, Mapping):
            payload["dimensions"] = {
                "value": str(dim_raw.get("value") or dim_raw.get("envelope") or "").strip(),
                "unit": str(dim_raw.get("unit") or "").strip(),
                "method": str(dim_raw.get("method") or dim_raw.get("basis") or "").strip(),
                "length": dim_raw.get("length"),
                "width": dim_raw.get("width"),
                "height": dim_raw.get("height"),
            }
        elif dim_raw is not None and not isinstance(dim_raw, Mapping):
            payload["dimensions"] = {"value": str(dim_raw).strip(), "unit": "", "method": ""}
        utils = payload.get("utilities")
        if isinstance(utils, list):
            payload["utilities"] = "; ".join(str(item).strip() for item in utils if item)
        elif isinstance(utils, Mapping):
            payload["utilities"] = "; ".join(
                f"{k}: {v}" for k, v in utils.items() if v not in (None, "")
            )
        conns = payload.get("connections")
        if isinstance(conns, list):
            normalized: List[Dict[str, Any]] = []
            for item in conns:
                if isinstance(item, Mapping):
                    normalized.append(
                        {
                            "name": str(item.get("name") or item.get("id") or "").strip() or "connection",
                            "size": str(item.get("size") or item.get("value") or "").strip(),
                            "unit": str(item.get("unit") or "").strip(),
                            "service": str(item.get("service") or "").strip(),
                            "basis": str(item.get("basis") or "").strip(),
                        }
                    )
                elif item:
                    normalized.append({"name": str(item).strip(), "size": "", "unit": "", "service": "", "basis": ""})
            payload["connections"] = normalized
        for field in ("inputs_used", "missing_inputs", "assumptions", "source_basis"):
            if field in payload:
                payload[field] = coerce_string_list_items(payload[field])
        if not str(payload.get("selected_model") or "").strip():
            payload["selected_model"] = str(
                payload.get("equipment_name") or payload.get("equipment_type") or "Sized equipment"
            ).strip()
        if not str(payload.get("equipment_category") or "").strip():
            sys_name = str(payload.get("equipment_system") or payload.get("equipment_type") or "").strip()
            payload["equipment_category"] = (
                sys_name.replace("_", " ").title() if sys_name else "Equipment"
            )
        return payload


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


def unwrap_result_payload(data: Dict[str, Any] | EiResultManifest) -> Dict[str, Any]:
    """Return the inner deliverable dict from a bare result or ei_result_manifest_v1."""
    if isinstance(data, EiResultManifest):
        payload = data.model_dump()
    else:
        payload = dict(data or {})
    if payload.get("schema_version") != EI_RESULT_MANIFEST_VERSION:
        return payload
    inner = payload.get("result")
    if isinstance(inner, dict):
        return inner
    for item in payload.get("outputs") or []:
        if not isinstance(item, dict):
            continue
        value = item.get("value")
        if isinstance(value, dict):
            return value
    raise ValueError("result manifest has no typed output payload")


def wrap_sizing_result(
    data: Dict[str, Any] | EquipmentSizingOutput,
    *,
    output_port_id: str = EQUIPMENT_SIZING_OUTPUT_PORT,
    run: Dict[str, Any] | None = None,
    inputs: Dict[str, Any] | None = None,
) -> EiResultManifest:
    """Wrap equipment_sizing_v1 without changing its payload contract."""
    output = data if isinstance(data, EquipmentSizingOutput) else EquipmentSizingOutput.model_validate(
        unwrap_result_payload(data) if isinstance(data, dict) else data
    )
    payload = output.model_dump()
    return EiResultManifest(
        template_family="equipment_sizing",
        run=run or {},
        inputs=inputs or {},
        result=payload,
        outputs=[
            EiResultOutput(
                port_id=output_port_id,
                label="Equipment sizing",
                schema_ref=EQUIPMENT_SIZING_SCHEMA_REF,
                value=payload,
            )
        ],
        artifacts=output.artifacts,
    )


def canonicalize_equipment_tag(raw: Any) -> str:
    cleaned = str(raw or "").strip().upper()
    out: List[str] = []
    prev_dash = False
    for ch in cleaned:
        if ch.isalnum() or ch in "._-":
            if ch == "-":
                if prev_dash:
                    continue
                prev_dash = True
            else:
                prev_dash = False
            out.append(ch)
        else:
            if not prev_dash:
                out.append("-")
                prev_dash = True
    return "".join(out).strip("-")


def apply_user_identity(result: Dict[str, Any], inputs: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Force user-owned system/item names and tags onto a result payload."""
    src = dict(inputs or {})
    item_tag = canonicalize_equipment_tag(src.get("equipment_tag") or src.get("equipment_key") or "")
    item_name = str(src.get("equipment_item_name") or "").strip()
    system_name = str(src.get("equipment_system_name") or src.get("system_name") or "").strip()
    system_tag = canonicalize_equipment_tag(src.get("equipment_system_tag") or "")
    role = str(src.get("composition_role") or "").strip()

    if item_tag:
        result["equipment_tag"] = item_tag
    elif not str(result.get("equipment_tag") or "").strip():
        result["equipment_tag"] = canonicalize_equipment_tag(result.get("equipment_tag") or "")

    if item_name:
        result["equipment_item_name"] = item_name
        result["equipment_name"] = item_name
    elif str(result.get("equipment_item_name") or "").strip():
        result["equipment_name"] = str(result.get("equipment_item_name") or "").strip()

    if system_name:
        result["equipment_system_name"] = system_name
        result["system_name"] = system_name

    if system_tag:
        result["equipment_system_tag"] = system_tag
    elif item_tag and not str(result.get("equipment_system_tag") or "").strip():
        result["equipment_system_tag"] = item_tag

    final_item = canonicalize_equipment_tag(result.get("equipment_tag") or "")
    final_system = canonicalize_equipment_tag(result.get("equipment_system_tag") or "")
    if role in {"standalone", "skid", "system_child"}:
        result["composition_role"] = role
    else:
        result["composition_role"] = (
            "system_child" if final_system and final_item and final_system != final_item else "standalone"
        )

    for key in (
        "source_module_id",
        "source_module_label",
        "core_equipment_module_id",
        "core_equipment_module_label",
        "functional_area_id",
        "functional_area_label",
    ):
        value = str(src.get(key) or "").strip()
        if value:
            result[key] = value
    return result


def unwrap_evaluator_result(
    data: Dict[str, Any] | EiResultManifest | EquipmentSelectorOutput,
) -> EquipmentSelectorOutput:
    """Read either a generic envelope or the legacy bare evaluator payload."""
    if isinstance(data, EquipmentSelectorOutput):
        return data
    if isinstance(data, EquipmentSizingOutput):
        raise ValueError("expected equipment_selector_v1, got equipment_sizing_v1")
    payload = unwrap_result_payload(data)
    return EquipmentSelectorOutput.model_validate(payload)


def validate_output(
    data: Dict[str, Any] | EiResultManifest,
) -> EquipmentSelectorOutput | EquipmentSizingOutput:
    if isinstance(data, EquipmentSelectorOutput) or isinstance(data, EquipmentSizingOutput):
        return data
    payload = unwrap_result_payload(data)
    schema = str(payload.get("schema_version") or "").strip()
    if schema == SIZING_SCHEMA_VERSION:
        return EquipmentSizingOutput.model_validate(payload)
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
    cem_source_id = (output.source_module_id or "").strip()
    cem_source_label = (output.source_module_label or "").strip()
    fa_id = (output.functional_area_id or "").strip() or (
        "equipment-intelligence" if not cem_source_id else cem_source_id
    )
    fa_label = (output.functional_area_label or "").strip() or (
        functional_area_label if not cem_source_id else cem_source_label or functional_area_label
    )
    return {
        "id": str(uuid.uuid4()),
        "preliminary_tag": output.equipment_tag,
        "functional_area_id": fa_id,
        "functional_area_label": fa_label,
        "process_step_id": cem_source_id or f"ei-{system}",
        "process_step_label": cem_source_label or f"Equipment Intelligence — {output.equipment_category or system}",
        "source_module_id": cem_source_id or output.creator_attribution.app_id,
        "source_module_label": cem_source_label or output.creator_attribution.display_name,
        "core_equipment_module_id": (output.core_equipment_module_id or "").strip() or None,
        "core_equipment_module_label": (output.core_equipment_module_label or "").strip() or None,
        "equipment_name": output.equipment_item_name or output.equipment_name or output.selected_model,
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
