from __future__ import annotations

from typing import Any, Dict, Optional
import re

from .llm import complete_json, llm_credentials_present, parse_json_safely


# Phrases that commonly appear as application labels in free text.
_APPLICATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bbiopharm(?:a|aceutical)?\b", re.I), "biopharma"),
    (re.compile(r"\bsterile\b", re.I), "sterile"),
    (re.compile(r"\baseptic\b", re.I), "aseptic"),
    (re.compile(r"\bfood(?:\s+&\s*bev|\s+and\s+beverage)?\b", re.I), "food"),
    (re.compile(r"\bchemical\b", re.I), "chemical"),
    (re.compile(r"\bpharma(?:ceutical)?\b", re.I), "pharmaceutical"),
]

_FLUID_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bnitrogen\b|\bN2\b", re.I), "nitrogen"),
    (re.compile(r"\bair\b", re.I), "air"),
    (re.compile(r"\bwfi\b|\bwater\b", re.I), "air / nitrogen"),
]

_SYSTEM_HINT = re.compile(
    r"(?P<name>"
    r"(?:media\s+prep(?:aration)?\s+vessel)|"
    r"(?:buffer\s+(?:prep(?:aration)?\s+)?(?:vessel|tank))|"
    r"(?:process\s+(?:vessel|tank))|"
    r"(?:storage\s+(?:vessel|tank))|"
    r"(?:bioreactor)|"
    r"(?:[\w-]+\s+(?:vessel|tank|reactor))"
    r")",
    re.I,
)


def parse_inputs_heuristic(text: str) -> Dict[str, Any]:
    """Best-effort free-text → inputs dict without calling an LLM."""
    raw = (text or "").strip()
    inputs: Dict[str, Any] = {}
    if not raw:
        return inputs

    # Hyphen-separated numeric DIR code (e.g. 2-1-2-3-1-1).
    if re.fullmatch(r"\d+(?:-\d+)+", raw):
        inputs["dir_code"] = raw
        inputs["phase"] = "evaluate"
        inputs["raw_text"] = raw
        return inputs

    application: Optional[str] = None
    for pattern, label in _APPLICATION_PATTERNS:
        if pattern.search(raw):
            application = label
            break
    if application:
        inputs["application"] = application

    fluid: Optional[str] = None
    for pattern, label in _FLUID_PATTERNS:
        if pattern.search(raw):
            fluid = label
            break
    if fluid:
        inputs["fluid"] = fluid

    match = _SYSTEM_HINT.search(raw)
    if match:
        inputs["system_name"] = " ".join(match.group("name").split()).title()
    else:
        # Use the first comma/semicolon segment, or the whole line, as system name.
        segment = re.split(r"[,;]", raw, maxsplit=1)[0].strip()
        # Drop trailing duty words that are not a system name.
        segment = re.sub(
            r"\b(sterile|aseptic|vent\s+filter|filter|duty)\b",
            "",
            segment,
            flags=re.I,
        ).strip(" ,.-")
        if segment:
            inputs["system_name"] = segment
        else:
            inputs["system_name"] = raw

    inputs["raw_text"] = raw
    return inputs


def heuristics_look_thin(inputs: Dict[str, Any]) -> bool:
    """True when we should consider an LLM parse if a key is available."""
    if inputs.get("dir_code"):
        return False
    system = str(inputs.get("system_name") or "").strip()
    if not system:
        return True
    if system == str(inputs.get("raw_text") or "").strip() and "application" not in inputs:
        return True
    if len(system) < 3:
        return True
    return False


def parse_inputs_with_openai(text: str, *, model: str | None = None) -> Dict[str, Any]:
    """Use the configured creator LLM to extract structured selector inputs."""
    return parse_inputs_with_llm(text, model=model)


def parse_inputs_with_llm(text: str, *, model: str | None = None) -> Dict[str, Any]:
    """Use the configured creator LLM to extract structured selector inputs from free text."""
    if not llm_credentials_present():
        raise RuntimeError("LLM API key is missing for the configured CREATOR_LLM_PROVIDER")

    completion = complete_json(
        system=(
            "Extract equipment selector inputs as a JSON object. "
            "Use keys when present: system_name, application, fluid. "
            "Omit unknown keys. Do not invent equipment models."
        ),
        user=text,
        model=model,
        max_output_tokens=500,
    )
    parsed = parse_json_safely(completion.text)
    parsed["raw_text"] = text.strip()
    return parsed


def parse_free_text(text: str, *, use_openai_if_available: bool = True) -> Dict[str, Any]:
    """Parse free text to inputs: heuristics first, optional LLM enrichment."""
    inputs = parse_inputs_heuristic(text)
    if not use_openai_if_available:
        return inputs
    if not llm_credentials_present() or not heuristics_look_thin(inputs):
        return inputs
    try:
        llm_inputs = parse_inputs_with_llm(text)
    except Exception:
        return inputs
    # Prefer LLM values when present; keep heuristic fallbacks.
    merged = dict(inputs)
    for key, value in llm_inputs.items():
        if value is None or value == "":
            continue
        merged[key] = value
    return merged
