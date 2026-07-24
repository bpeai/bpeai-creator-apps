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


def validate_dir_code(
    pack: KnowledgePack,
    scenario_id: str,
    dir_code: str,
) -> DirValidation:
    """Hard-validate a hyphen-separated DIR code against pack requirements."""
    scenario = pack.scenario(scenario_id)
    requirements = scenario.get("requirements") or []
    if not isinstance(requirements, list) or not requirements:
        return DirValidation(ok=False, error=f"Scenario '{scenario_id}' has no requirements.")

    common = pack.common_codes(scenario_id)
    suggested = common[0] if common else ""

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
    rules = pack.validation_rules.get("application") or {}
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
        from bpeai_taxonomy import valid_applications  # type: ignore

        apps = {str(a).strip().lower() for a in (valid_applications() or [])}
        # taxonomy may return dicts with name=
        if apps and isinstance(next(iter(apps)), str):
            pass
        known = normalized.lower() in apps or raw.lower() in apps
        if known is False and str(rules.get("mode") or "soft").lower() == "soft":
            warning = f"Application '{raw}' not in shared taxonomy (soft)."
    except Exception:
        # Creator-apps clones often lack bpeai_taxonomy — skip.
        known = None
    return ApplicationCheck(normalized=normalized or raw, known=known, warning=warning)
