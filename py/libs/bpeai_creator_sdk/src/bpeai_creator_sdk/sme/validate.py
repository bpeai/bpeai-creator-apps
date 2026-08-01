from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .pack_loader import KnowledgePack


@dataclass
class DirValidation:
    ok: bool
    error: str = ""
    suggested_correction: str = ""
    decoded: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class OptionCheck:
    unknown_names: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ApplicationCheck:
    normalized: str
    known: bool | None = None  # None = taxonomy unavailable
    warning: str = ""


def _requirement_count(scenario: Mapping[str, Any]) -> int:
    reqs = scenario.get("requirements") or []
    return len(reqs) if isinstance(reqs, list) else 0


def _option_max(requirement: Mapping[str, Any]) -> int:
    options = requirement.get("options") or []
    if not isinstance(options, list) or not options:
        return 0
    indexes = []
    for opt in options:
        if isinstance(opt, Mapping) and "index" in opt:
            try:
                indexes.append(int(opt["index"]))
            except (TypeError, ValueError):
                continue
    return max(indexes) if indexes else len(options)


def is_numeric_dir_code(code: str, *, requirement_count: int | None = None) -> bool:
    """True when ``code`` is a hyphen-separated positive integer sequence."""
    parts = [p.strip() for p in (code or "").split("-") if p.strip()]
    if not parts or not all(p.isdigit() and int(p) >= 1 for p in parts):
        return False
    if requirement_count is not None and len(parts) != requirement_count:
        return False
    return True


def validate_dir_code(
    pack: KnowledgePack,
    scenario_id: str,
    dir_code: str,
    *,
    requirements: Sequence[Mapping[str, Any]] | None = None,
    common_codes: Sequence[Any] | None = None,
) -> DirValidation:
    """Hard-validate a hyphen-separated DIR code against pack / menu requirements."""
    if requirements is None:
        scenario = pack.scenario(scenario_id)
        requirements = scenario.get("requirements") or []
    if not isinstance(requirements, list) or not requirements:
        return DirValidation(ok=False, error=f"Scenario '{scenario_id}' has no requirements.")

    if common_codes is None:
        common = pack.common_codes(scenario_id)
    else:
        common = []
        for item in common_codes:
            if isinstance(item, str):
                common.append(item)
            elif isinstance(item, Mapping) and item.get("code"):
                common.append(str(item["code"]))
    # Prefer numeric starter codes with correct arity (repair stale 6-of-7 packs).
    from .dir_catalog import ensure_common_codes_for_requirements

    repaired = ensure_common_codes_for_requirements(
        common_codes if common_codes is not None else common,
        requirements,
    )
    numeric_common = [c["code"] for c in repaired]
    suggested = (numeric_common or [""])[0]

    rules = (pack.validation_rules.get("dir_code") or {}) if isinstance(pack.validation_rules, dict) else {}
    min_index = int(rules.get("min_index") or 1)

    parts = [p.strip() for p in (dir_code or "").split("-") if p.strip()]
    expected = len(requirements)
    if len(parts) != expected:
        return DirValidation(
            ok=False,
            error=f"Expected {expected} indexes, got {len(parts)}.",
            suggested_correction=suggested,
        )

    decoded: List[Dict[str, Any]] = []
    for i, part in enumerate(parts):
        req = requirements[i] if isinstance(requirements[i], Mapping) else {}
        if not part.isdigit():
            return DirValidation(
                ok=False,
                error=f"Invalid index '{part}'.",
                suggested_correction=suggested,
            )
        idx = int(part)
        max_idx = _option_max(req)
        if idx < min_index or (max_idx and idx > max_idx):
            label = req.get("label") or f"requirement {i + 1}"
            return DirValidation(
                ok=False,
                error=f"Index {idx} out of range for '{label}' (1–{max_idx}).",
                suggested_correction=suggested,
            )
        # Resolve option text when possible.
        opt_text = ""
        for opt in req.get("options") or []:
            if isinstance(opt, Mapping) and int(opt.get("index") or 0) == idx:
                opt_text = str(opt.get("text") or "")
                break
        decoded.append(
            {
                "requirement_index": int(req.get("index") or i + 1),
                "label": req.get("label"),
                "option_index": idx,
                "option_text": opt_text,
            }
        )

    return DirValidation(ok=True, decoded=decoded, suggested_correction=suggested)


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def check_equipment_option_names(
    pack: KnowledgePack,
    names: Sequence[str],
) -> OptionCheck:
    """Soft-check option / selected_model names against the pack catalog."""
    rules = pack.validation_rules.get("equipment_option_name") or {}
    mode = str(rules.get("mode") or "soft").lower()
    catalog = {_normalize_name(n): n for n in pack.option_names()}
    unknown: List[str] = []
    warnings: List[str] = []
    for name in names:
        raw = str(name or "").strip()
        if not raw:
            continue
        key = _normalize_name(raw)
        if key in catalog:
            continue
        # Fuzzy: substring either way.
        if any(key in c or c in key for c in catalog):
            continue
        unknown.append(raw)
        if mode == "soft":
            warnings.append(f"Option not in SME catalog: {raw}")
    return OptionCheck(unknown_names=unknown, warnings=warnings)


def check_application(pack: KnowledgePack, application: str) -> ApplicationCheck:
    """Soft-normalize application; optionally check shared taxonomy if installed."""
    rules_raw = pack.validation_rules.get("application") or {}
    # Draft LLM packs sometimes emit a bare string; treat as empty soft rules.
    rules = rules_raw if isinstance(rules_raw, Mapping) else {}
    aliases = rules.get("aliases") or {}
    raw = (application or "").strip()
    normalized = raw
    if str(rules.get("normalize") or "").lower() == "lowercase_strip":
        normalized = raw.lower().strip()
    if isinstance(aliases, Mapping):
        mapped = aliases.get(normalized)
        if mapped:
            normalized = str(mapped).strip()

    known: bool | None = None
    warning = ""
    try:
        apps = _taxonomy_application_names()
        if apps is None:
            known = None
        else:
            known = normalized.lower() in apps or raw.lower() in apps
            if known is False and str(rules.get("mode") or "soft").lower() == "soft":
                warning = f"Application '{raw}' not in shared taxonomy (soft)."
    except Exception:
        # Creator-apps clones often lack bpeai_taxonomy — skip.
        known = None
    return ApplicationCheck(normalized=normalized or raw, known=known, warning=warning)


def _taxonomy_application_names() -> set[str] | None:
    """Normalize bpeai_taxonomy applications.yaml shapes to a lowercase name set."""
    try:
        from bpeai_taxonomy import valid_applications  # type: ignore
    except Exception:
        return None

    raw = valid_applications()
    if raw is None:
        return None
    names: set[str] = set()
    if isinstance(raw, Mapping):
        # {applications: [...]} or similar
        items = raw.get("applications") or raw.get("items") or []
        if not isinstance(items, list):
            items = []
    elif isinstance(raw, list):
        items = raw
    else:
        return None

    for item in items:
        if isinstance(item, str):
            names.add(item.strip().lower())
        elif isinstance(item, Mapping):
            for key in ("name", "id", "label", "slug"):
                val = item.get(key)
                if val:
                    names.add(str(val).strip().lower())
                    break
    return names
