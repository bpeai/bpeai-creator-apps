"""Deliverable filenames for evaluator and sizing apps.

Evaluator: ``{system}_{item}_Evaluation`` (underscores), e.g.
``Chromatography_Skid_Pump_Evaluation``. The item noun is omitted when it is
already a token in the system name (``CIP_Return_Pump_Evaluation``, not
``CIP_Return_Pump_Pump_Evaluation``).

Sizing: ``{system} {item} Sizing`` (spaces), e.g. ``Buffer Preparation Agitator Sizing``.

Item nouns are SME-owned on the knowledge pack (``evaluated_item`` /
``sized_item`` in pack.yaml). App/pack id inference (``pump_selector`` → pump)
wins over identity instance names. Identity is a last-resort type-noun fallback.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

DEFAULT_EVALUATION_FILENAME_PATTERN = "{system}_{item}_{family}"
DEFAULT_SIZING_FILENAME_PATTERN = "{system} {item} Sizing"
_UNSAFE_FILENAME = re.compile(r'[\\/:*?"<>|]+')
_GENERIC_LAST_TOKENS = {"sizing", "sizer", "pack", "stub", "v1", "app", "system"}
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


def pack_sized_item(pack: Any) -> str:
    if pack is None:
        return ""
    direct = str(getattr(pack, "sized_item", "") or "").strip()
    if direct:
        return direct
    meta = _pack_meta(pack)
    item = str(meta.get("sized_item") or "").strip()
    if item:
        return item
    return pack_evaluated_item(pack)


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
    raw = str(pack_id or "").strip().lower().replace("\\", "/")
    leaf = raw.split("/")[-1].split(".")[-1].replace("-", "_")
    if not leaf or leaf in _GENERIC_PACK_IDS:
        return ""
    stripped = False
    for suffix in _STRIP_SUFFIXES:
        if leaf.endswith(suffix) and len(leaf) > len(suffix):
            leaf = leaf[: -len(suffix)]
            stripped = True
            break
    if stripped and leaf and leaf not in _GENERIC_PACK_IDS and leaf not in {"equipment", "app"}:
        return leaf
    if "_" in leaf:
        last = leaf.rsplit("_", 1)[-1]
        if last and last not in _GENERIC_LAST_TOKENS and last not in _GENERIC_PACK_IDS:
            return last
    return ""


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _candidate_pack_ids(
    *,
    pack: Any = None,
    result: Mapping[str, Any] | None = None,
    pack_id: str = "",
) -> list[str]:
    src = result or {}
    attribution = _mapping(src.get("creator_attribution"))
    handshake = _mapping(src.get("_handshake"))
    ordered = [
        pack_id,
        str(getattr(pack, "pack_id", "") or ""),
        str(src.get("knowledge_pack") or ""),
        str(attribution.get("app_id") or ""),
        str(handshake.get("app_id") or ""),
        str(handshake.get("knowledge_pack_id") or ""),
    ]
    seen: set[str] = set()
    out: list[str] = []
    for value in ordered:
        token = str(value or "").strip()
        key = token.lower()
        if not token or key in seen:
            continue
        seen.add(key)
        out.append(token)
    return out


def _item_already_in_system(system: str, item: str) -> bool:
    sys_parts = {p for p in filename_token(system).lower().split("_") if p}
    item_parts = {p for p in filename_token(item).lower().split("_") if p}
    return bool(item_parts) and item_parts.issubset(sys_parts)


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
    for candidate in _candidate_pack_ids(pack=pack, result=src, pack_id=pack_id):
        inferred = infer_evaluated_item_from_pack_id(candidate)
        if inferred:
            return inferred
    stamped = str(src.get("evaluated_item") or "").strip()
    if stamped:
        return stamped
    item_name = str(
        src.get("equipment_item_name") or src.get("equipment_name") or ""
    ).strip()
    system = str(
        src.get("equipment_system_name") or src.get("system_name") or ""
    ).strip()
    if not item_name:
        return ""
    if filename_token(item_name).lower() == filename_token(system).lower():
        return ""
    if _item_already_in_system(system, item_name):
        return ""
    return item_name


def display_filename_part(text: Any) -> str:
    cleaned = _UNSAFE_FILENAME.sub(" ", str(text or "").replace("_", " ")).strip()
    return re.sub(r"\s+", " ", cleaned)


def title_item_noun(text: str) -> str:
    part = display_filename_part(text)
    if not part:
        return ""
    if part.isupper() and len(part) <= 4:
        return part
    if part.islower() or part.isupper():
        return part.title()
    return part


def _evaluation_family_token(family: str) -> str:
    raw = str(family or "").strip() or "evaluation"
    if raw.lower() == "evaluation":
        return filename_token(title_item_noun(raw)) or "Evaluation"
    return filename_token(raw) or "Evaluation"


def evaluation_artifact_stem(
    result: Mapping[str, Any] | None = None,
    *,
    pack: Any = None,
    family: str = "evaluation",
    item: str | None = None,
    pack_id: str = "",
) -> str:
    src = result or {}
    existing = filename_token(src.get("artifact_stem") or "")
    system = (
        filename_token(src.get("equipment_system_name") or src.get("system_name") or "")
        or "evaluation"
    )
    resolved = (
        item
        if item is not None
        else infer_evaluated_item(pack=pack, result=src, pack_id=pack_id)
    ).strip()
    if resolved and _item_already_in_system(system, resolved):
        resolved = ""
    item_tok = filename_token(title_item_noun(resolved)) if resolved else ""
    family_tok = _evaluation_family_token(family)
    if existing and item is None and not pack and not pack_id:
        existing_parts = {p for p in existing.lower().split("_") if p}
        inferred_missing = bool(item_tok) and item_tok.lower() not in existing_parts
        if not inferred_missing:
            return existing
    pattern = pack_filename_pattern(pack) or DEFAULT_EVALUATION_FILENAME_PATTERN
    try:
        raw = pattern.format(system=system, item=item_tok, family=family_tok)
    except (KeyError, IndexError, ValueError):
        raw = f"{system}_{item_tok}_{family_tok}" if item_tok else f"{system}_{family_tok}"
    stem = re.sub(r"_+", "_", filename_token(raw)).strip("_")
    return stem or "Evaluation"


def attach_evaluation_artifact_name(
    result: dict[str, Any],
    *,
    pack: Any = None,
    family: str = "evaluation",
    pack_id: str = "",
) -> dict[str, Any]:
    """Stamp ``evaluated_item`` and ``artifact_stem`` on an evaluate result."""
    item = infer_evaluated_item(pack=pack, result=result, pack_id=pack_id)
    if item:
        result["evaluated_item"] = item
    result["artifact_stem"] = evaluation_artifact_stem(
        result, pack=pack, family=family, item=item, pack_id=pack_id
    )
    return result


def infer_sized_item_from_pack_id(pack_id: str) -> str:
    from_eval = infer_evaluated_item_from_pack_id(pack_id)
    if from_eval:
        return from_eval
    leaf = str(pack_id or "").strip().lower().split(".")[-1]
    if not leaf or leaf in _GENERIC_PACK_IDS or "_" not in leaf:
        return ""
    last = leaf.rsplit("_", 1)[-1]
    if last in _GENERIC_LAST_TOKENS or last in _GENERIC_PACK_IDS:
        return ""
    return last


def infer_sized_item(
    *,
    pack: Any = None,
    result: Mapping[str, Any] | None = None,
    pack_id: str = "",
) -> str:
    from_pack = pack_sized_item(pack)
    if from_pack:
        return from_pack
    src = result or {}
    stamped = str(src.get("sized_item") or "").strip()
    if stamped:
        return stamped
    for candidate in _candidate_pack_ids(pack=pack, result=src, pack_id=pack_id):
        inferred = infer_sized_item_from_pack_id(candidate)
        if inferred:
            return inferred
    item_name = str(
        src.get("equipment_item_name") or src.get("equipment_name") or ""
    ).strip()
    system = str(
        src.get("equipment_system_name") or src.get("system_name") or ""
    ).strip()
    if not item_name:
        return ""
    if filename_token(item_name).lower() == filename_token(system).lower():
        return ""
    if _item_already_in_system(system, item_name):
        return ""
    return item_name


def sizing_artifact_stem(
    result: Mapping[str, Any] | None = None,
    *,
    pack: Any = None,
    item: str | None = None,
) -> str:
    src = result or {}
    existing = display_filename_part(src.get("artifact_stem") or "")
    if existing and item is None and not pack:
        return existing
    system = (
        display_filename_part(src.get("equipment_system_name") or src.get("system_name") or "")
        or "Vessel"
    )
    resolved = (item if item is not None else infer_sized_item(pack=pack, result=src)).strip()
    if resolved and _item_already_in_system(system, resolved):
        resolved = ""
    item_part = title_item_noun(resolved)
    pattern = pack_filename_pattern(pack) or DEFAULT_SIZING_FILENAME_PATTERN
    try:
        raw = pattern.format(system=system, item=item_part, family="Sizing")
    except (KeyError, IndexError, ValueError):
        raw = f"{system} {item_part} Sizing" if item_part else f"{system} Sizing"
    stem = display_filename_part(raw)
    return stem or "Vessel Sizing"


def attach_sizing_artifact_name(
    result: dict[str, Any],
    *,
    pack: Any = None,
) -> dict[str, Any]:
    """Stamp ``sized_item`` and spaced ``artifact_stem`` on a sizing result."""
    item = infer_sized_item(pack=pack, result=result)
    if item:
        result["sized_item"] = item
    result["artifact_stem"] = sizing_artifact_stem(result, pack=pack, item=item)
    return result
