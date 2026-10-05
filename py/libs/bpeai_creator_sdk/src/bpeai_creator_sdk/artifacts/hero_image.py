"""Evidence-only PPTX visuals shared by local and website runtimes.

Catalogs are SME-authored pack assets, never output from the slide LLM.
No network access, inferred geometry, or generated equipment imagery is used.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, MutableMapping

from PIL import Image

CATALOG_PATH = "references/visuals/catalog.json"
MAX_ASSET_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 15 * 1024 * 1024
MATCH_FIELDS = {"equipment_name", "equipment_item_name", "system_name", "equipment_type",
                "sized_item", "selected_model", "recommended_basis", "dir_code"}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def engineering_basis_sha256(result: Mapping[str, Any]) -> str:
    """Bind project drawings to the reviewed engineering inputs/results."""
    keys = sorted(MATCH_FIELDS | {"capacity", "connections", "dimensions", "key_specs",
                                "assumptions", "inputs_used", "missing_inputs", "application"})
    basis = {key: result[key] for key in keys if key in result}
    return hashlib.sha256(json.dumps(basis, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def safe_asset_path(value: Any) -> str:
    text = str(value or "")
    path = PurePosixPath(text)
    if ("\\" in text or ":" in text or "\x00" in text or path.is_absolute()
            or any(part in {"..", ".", ""} for part in text.split("/")) or not text.startswith("references/visuals/")
            or path.suffix.lower() not in {".png", ".jpg", ".jpeg"}):
        raise ValueError("Visual must be a relative PNG/JPEG under references/visuals/")
    return text


def load_visual_catalog(root: Path) -> dict[str, Any]:
    """Missing or malformed catalogs never prevent an engineering report."""
    try:
        source = root / CATALOG_PATH
        if source.stat().st_size > 1024 * 1024:
            return {}
        value = json.loads(source.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _asset_bytes(asset: Mapping[str, Any], root: Path | None) -> bytes:
    relative = safe_asset_path(asset.get("path"))
    encoded = asset.get("data_base64")
    if encoded is not None:
        if not isinstance(encoded, str) or len(encoded) > (MAX_ASSET_BYTES + 2) // 3 * 4:
            raise ValueError("Visual exceeds size limit")
        data = base64.b64decode(encoded, validate=True)
    elif root is not None:
        source = (root / relative).resolve()
        source.relative_to(root.resolve())
        if source.stat().st_size > MAX_ASSET_BYTES:
            raise ValueError("Visual exceeds size limit")
        data = source.read_bytes()
    else:
        raise ValueError("Visual bytes unavailable")
    if not data or len(data) > MAX_ASSET_BYTES:
        raise ValueError("Visual exceeds size limit")
    if hashlib.sha256(data).hexdigest() != str(asset.get("sha256") or "").lower():
        raise ValueError("Visual differs from reviewed asset")
    with Image.open(io.BytesIO(data)) as image:
        expected = "PNG" if relative.lower().endswith(".png") else "JPEG"
        if image.format != expected or image.width * image.height > 20_000_000:
            raise ValueError("Invalid image format or dimensions")
        image.load()
    return data


def select_verified_visual(result: Mapping[str, Any], catalog: Mapping[str, Any],
                           root: Path | None = None) -> tuple[dict[str, Any], bytes] | None:
    """Fail closed: review, exact applicability and the reviewed bytes must match."""
    if catalog.get("schema_version") != "ei_visual_assets_v1":
        return None
    assets = catalog.get("assets")
    if not isinstance(assets, list) or len(assets) > 50:
        return None
    priority = {"project_configuration": 0, "exact_model": 1, "product_family": 2}
    candidates = sorted((a for a in assets[:50] if isinstance(a, Mapping)),
                        key=lambda a: priority.get(str(a.get("scope")), 3))
    for asset in candidates:
        if not isinstance(asset, Mapping):
            continue
        if str(asset.get("kind")) not in {"vendor_photo", "vendor_drawing", "project_drawing"}:
            continue
        if str(asset.get("scope")) not in {"exact_model", "product_family", "project_configuration"}:
            continue
        if asset.get("review_status") != "approved":
            continue
        try:
            date.fromisoformat(str(asset.get("reviewed_at") or "")[:10])
        except ValueError:
            continue
        required = ("id", "reviewed_by", "reviewed_at", "applicability", "attribution", "reuse_basis")
        if any(not isinstance(asset.get(key), str) or not asset[key].strip() for key in required):
            continue
        if not asset.get("source_url") and not asset.get("source_document"):
            continue
        if asset["kind"].startswith("vendor_") and not (asset.get("manufacturer") and asset.get("model")):
            continue
        match = asset.get("match")
        if not isinstance(match, Mapping) or not match or set(match) - MATCH_FIELDS:
            continue
        if not set(match) & {"equipment_name", "equipment_item_name", "system_name"}:
            continue
        if not set(match) & {"selected_model", "recommended_basis", "equipment_type", "sized_item"}:
            continue
        if asset["scope"] == "exact_model":
            if not _norm(asset.get("model")) or _norm(match.get("selected_model")) != _norm(asset["model"]):
                continue
        if asset["scope"] == "project_configuration":
            if "dir_code" not in match or asset.get("result_sha256") != engineering_basis_sha256(result):
                continue
        if any(not isinstance(value, str) or not _norm(value) or _norm(result.get(key)) != _norm(value) for key, value in match.items()):
            continue
        try:
            data = _asset_bytes(asset, root)
        except (OSError, ValueError, TypeError, SyntaxError, EOFError, Image.DecompressionBombError):
            continue
        return {key: value for key, value in asset.items() if key != "data_base64"}, data
    return None


def attach_title_hero_image(result: Mapping[str, Any], slide_pack: MutableMapping[str, Any],
                            *, output_path: Path | str, knowledge_pack: Any = None) -> Path | None:
    """Compatibility entry point. Never trusts LLM images or legacy image paths."""
    slide_pack.pop("hero_image_path", None)
    slide_pack["visual_evidence"] = {"mode": "summary", "reason": "No applicable reviewed visual"}
    catalog = getattr(knowledge_pack, "visual_assets", {})
    root = getattr(knowledge_pack, "path", None)
    selected = select_verified_visual(result, catalog, root) if isinstance(catalog, Mapping) else None
    if selected is None:
        return None
    evidence, data = selected
    dest = Path(output_path).with_suffix(Path(evidence["path"]).suffix.lower())
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        dest.write_bytes(data)
    except OSError:
        slide_pack["visual_evidence"] = {"mode": "summary", "reason": "Reviewed visual could not be materialized"}
        return None
    slide_pack["hero_image_path"] = str(dest)
    slide_pack["visual_evidence"] = {**evidence, "mode": "asset"}
    return dest


def render_title_hero(result: Mapping[str, Any], *, output_path: Path | str,
                      callouts: Any = None) -> None:
    """Legacy API: unsupported inferred drawings are intentionally disabled."""
    return None


def engineering_summary(result: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Use supplied engineering results, without physical assumptions."""
    rows: list[tuple[str, str]] = []
    def known(value: Any) -> bool:
        return value is not None and str(value).strip() != "" and _norm(value) not in {
            "unknown", "tbd", "n/a", "none", "not specified", "to be confirmed"}

    def add(label: str, value: Any) -> None:
        text = str(value if value is not None else "").strip()
        if known(value):
            rows.append((label, text))
    sizing = result.get("schema_version") == "equipment_sizing_v1" or result.get("template_family") == "equipment_sizing"
    if sizing:
        capacity = result.get("capacity") or {}
        if isinstance(capacity, Mapping) and known(capacity.get("value")):
            add("Capacity / duty", f"{capacity['value']} {capacity.get('unit') or ''}".strip())
            add("Sizing basis", capacity.get("basis"))
        dims = result.get("dimensions") or {}
        if isinstance(dims, Mapping) and known(dims.get("value")):
            add("Envelope", " ".join(str(dims.get(k) or "") for k in ("value", "unit", "method")).strip())
        connections = result.get("connections") or []
        values = [" ".join(str(c.get(k) or "") for k in ("name", "size", "unit")).strip()
                  for c in connections if isinstance(c, Mapping) and known(c.get("size"))]
        if values:
            add("Connections", "; ".join(values))
        open_items = list(result.get("missing_inputs") or []) + list(result.get("assumptions") or [])
        if open_items:
            add("Open items / assumptions", "; ".join(map(str, open_items)))
    else:
        add("Recommended technology", result.get("recommended_basis") or result.get("selected_model"))
        add("Selection rationale", result.get("rationale"))
        specs = [s for s in result.get("key_specs") or [] if isinstance(s, Mapping)
                 and s.get("key") and known(s.get("value"))]
        if specs:
            add("Selection criteria", "; ".join(f"{s['key']}: {s['value']} {s.get('unit') or ''}".strip() for s in specs[:3]))
        limits = result.get("do_not_specify") or result.get("failure_modes") or []
        if limits:
            add("Limitations", "; ".join(map(str, limits)))
    if not rows:
        add("Equipment", result.get("equipment_name") or result.get("system_name"))
        add("Engineering basis", "No additional supported information is available.")
    return rows[:5]
