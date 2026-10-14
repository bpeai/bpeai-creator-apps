"""Which XLSX / DOCX / PPTX files a run should build.

Platform runs inject ``generate_docx``, ``generate_pptx``, and ``generate_xlsx``.
Local runs without those keys read ``deliverables`` from ``manifest.json``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if not text:
            return default
        return text not in {"0", "false", "no", "off"}
    return default


def default_deliverables(template_family: str) -> dict[str, bool]:
    sizing = template_family == "equipment_sizing"
    return {"docx": True, "pptx": True, "xlsx": sizing}


def deliverables_from_manifest(manifest_path: Path | None, template_family: str) -> dict[str, bool]:
    flags = default_deliverables(template_family)
    if manifest_path is None or not manifest_path.is_file():
        return flags
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return flags
    raw = data.get("deliverables") if isinstance(data, dict) else None
    if not isinstance(raw, dict) and isinstance(data, dict):
        profile = data.get("catalog_profile")
        if isinstance(profile, dict):
            raw = profile.get("deliverables")
    if isinstance(raw, dict):
        for key in ("docx", "pptx", "xlsx"):
            if key in raw:
                flags[key] = _as_bool(raw.get(key), flags[key])
    return flags


def resolve_generate_flags(
    inputs: Mapping[str, Any],
    *,
    template_family: str,
    manifest_path: Path | None = None,
) -> dict[str, bool]:
    """Platform-injected generate_* wins. Otherwise the manifest, then family defaults."""
    base = deliverables_from_manifest(manifest_path, template_family)
    out: dict[str, bool] = {}
    for key in ("docx", "pptx", "xlsx"):
        injected = inputs.get(f"generate_{key}")
        out[key] = base[key] if injected is None else _as_bool(injected, base[key])
    return out
