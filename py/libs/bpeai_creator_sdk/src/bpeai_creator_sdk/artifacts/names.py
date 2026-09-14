"""Evaluation deliverable filenames: {system}_{item}_evaluation.

``system`` comes from the run (equipment_system_name / system_name).
``item`` is SME-owned on the knowledge pack (``evaluated_item`` in pack.yaml).
Identity ``equipment_item_name`` and pack_id inference are fallbacks only.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

DEFAULT_EVALUATION_FILENAME_PATTERN = "{system}_{item}_{family}"
_GENERIC_PACK_IDS = {
    "equipment_evaluator",
    "equipment_sizing",
    "equipment_sizing_v1",
    "mixing_stub",
    "mixing_sizing_stub",
}
_STRIP_SUFFIXES = (
    "_selector",
    "_expert",
    "_evaluator",
    "_matcher",
    "_sizer",
    "_sizing",
)


def filename_token(text: Any) -> str:
    return re.sub(r"[^\w\-]+", "_", str(text or "").strip()).strip("_")


def _pack_meta(pack: Any) -> Mapping[str, Any]:
    if pack is None:
        return {}
    meta = getattr(pack, "meta", None)
    return meta if isinstance(meta, Mapping) else {}


def pack_evaluated_item(pack: Any) -> str:
    if pack is None:
        return ""
    direct = str(getattr(pack, "evaluated_item", "") or "").strip()
    if direct:
        return direct
    meta = _pack_meta(pack)
    item = str(meta.get("evaluated_item") or "").strip()
    if item:
        return item
    nested = meta.get("artifact_filename")
    if isinstance(nested, Mapping):
        return str(nested.get("item") or "").strip()
    return ""


def pack_filename_pattern(pack: Any) -> str:
    if pack is None:
        return ""
    direct = str(getattr(pack, "artifact_filename_pattern", "") or "").strip()
    if direct:
        return direct
    meta = _pack_meta(pack)
    pattern = str(meta.get("artifact_filename_pattern") or "").strip()
    if pattern:
        return pattern
    nested = meta.get("artifact_filename")
    if isinstance(nested, Mapping):
        return str(nested.get("pattern") or "").strip()
    return ""


def infer_evaluated_item_from_pack_id(pack_id: str) -> str:
    leaf = str(pack_id or "").strip().lower().split(".")[-1]
    if not leaf or leaf in _GENERIC_PACK_IDS:
        return ""
    stripped = False
    for suffix in _STRIP_SUFFIXES:
        if leaf.endswith(suffix) and len(leaf) > len(suffix):
            leaf = leaf[: -len(suffix)]
            stripped = True
            break
    if not stripped or not leaf or leaf in _GENERIC_PACK_IDS or leaf in {"equipment", "app"}:
        return ""
    return leaf


def infer_evaluated_item(
    *,
    pack: Any = None,
    result: Mapping[str, Any] | None = None,
    pack_id: str = "",
) -> str:
    """Resolve the equipment-item noun used in evaluation filenames."""
    from_pack = pack_evaluated_item(pack)
    if from_pack:
        return from_pack
    src = result or {}
    item_name = str(
        src.get("equipment_item_name") or src.get("equipment_name") or ""
    ).strip()
    system = str(
        src.get("equipment_system_name") or src.get("system_name") or ""
    ).strip()
    item_tok = filename_token(item_name).lower()
    system_tok = filename_token(system).lower()
    if item_tok and item_tok != system_tok:
        return item_name
    pid = (
        pack_id
        or str(getattr(pack, "pack_id", "") or "")
        or str(src.get("knowledge_pack") or "")
    )
    return infer_evaluated_item_from_pack_id(pid)


def _item_already_in_system(system: str, item: str) -> bool:
    sys_parts = {p for p in filename_token(system).lower().split("_") if p}
    item_parts = {p for p in filename_token(item).lower().split("_") if p}
    return bool(item_parts) and item_parts.issubset(sys_parts)


def evaluation_artifact_stem(
    result: Mapping[str, Any] | None = None,
    *,
    pack: Any = None,
    family: str = "evaluation",
    item: str | None = None,
) -> str:
    src = result or {}
    existing = filename_token(src.get("artifact_stem") or "")
    if existing and item is None and not pack:
        return existing
    system = (
        filename_token(src.get("equipment_system_name") or src.get("system_name") or "")
        or "evaluation"
    )
    resolved = (item if item is not None else infer_evaluated_item(pack=pack, result=src)).strip()
    if resolved and _item_already_in_system(system, resolved):
        resolved = ""
    item_tok = filename_token(resolved)
    family_tok = filename_token(family) or "evaluation"
    pattern = pack_filename_pattern(pack) or DEFAULT_EVALUATION_FILENAME_PATTERN
    try:
        raw = pattern.format(system=system, item=item_tok, family=family_tok)
    except (KeyError, IndexError, ValueError):
        raw = f"{system}_{item_tok}_{family_tok}" if item_tok else f"{system}_{family_tok}"
    stem = re.sub(r"_+", "_", filename_token(raw)).strip("_")
    return stem or "evaluation"


def attach_evaluation_artifact_name(
    result: dict[str, Any],
    *,
    pack: Any = None,
    family: str = "evaluation",
) -> dict[str, Any]:
    """Stamp ``evaluated_item`` and ``artifact_stem`` on an evaluate result."""
    item = infer_evaluated_item(pack=pack, result=result)
    if item:
        result["evaluated_item"] = item
    result["artifact_stem"] = evaluation_artifact_stem(
        result, pack=pack, family=family, item=item
    )
    return result
