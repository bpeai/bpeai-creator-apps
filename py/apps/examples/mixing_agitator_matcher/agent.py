from __future__ import annotations

# Allow `python agent.py` from this folder as well as package imports.
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    _py_root = Path(__file__).resolve().parents[2]
    _py_root_str = str(_py_root)
    if _py_root_str not in sys.path:
        sys.path.insert(0, _py_root_str)
    _sdk_src = _py_root / "libs" / "bpeai_creator_sdk" / "src"
    if str(_sdk_src) not in sys.path:
        sys.path.insert(0, str(_sdk_src))
    __package__ = "apps.mixing_agitator_matcher"

import json
import re
from typing import Any, Dict, List, Optional

from bpeai_creator_sdk import CreatorAppBase, EquipmentSelectorOutput

from .prompts import (
    COMMON_DIR_CODES,
    DIR_TEMPLATES,
    EVALUATION_PROMPT,
    SYSTEM_PROMPT,
)


def _normalize_system_key(system_name: str) -> str:
    s = (system_name or "").strip().lower()
    if "resin" in s or "chromatography" in s or "slurry" in s:
        return "chromatography resin slurry"
    if "media" in s or "buffer" in s:
        return "media preparation"
    return "media preparation"


def _validate_dir_code(code: str, requirement_count: int) -> tuple[bool, str]:
    parts = [p.strip() for p in (code or "").split("-") if p.strip()]
    if len(parts) != requirement_count:
        return False, f"Expected {requirement_count} indexes, got {len(parts)}."
    for part in parts:
        if not part.isdigit() or int(part) < 1:
            return False, f"Invalid index '{part}'."
    return True, ""


class MixingAgitatorMatcherAgent(CreatorAppBase):
    app_id = "agitator_duty_impeller_matcher"

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        system_name = str(inputs.get("system_name") or "Media Preparation Vessel").strip()
        application = str(inputs.get("application") or "biopharmaceutical").strip()
        dir_code = str(inputs.get("dir_code") or "").strip()
        phase = str(inputs.get("phase") or "").strip().lower()

        if phase == "dir" or not dir_code:
            return self._dir_requirements(system_name, application)

        return self._evaluate(system_name, application, dir_code)

    def _dir_requirements(self, system_name: str, application: str) -> Dict[str, Any]:
        self.status(f"Preparing design input requirements for {system_name}…")
        key = _normalize_system_key(system_name)
        requirements = DIR_TEMPLATES.get(key) or DIR_TEMPLATES["media preparation"]
        common = COMMON_DIR_CODES.get(key) or COMMON_DIR_CODES["media preparation"]
        return {
            "phase": "dir_requirements",
            "system_name": system_name,
            "application": application,
            "requirements": requirements,
            "common_codes": common,
            "message": (
                f"For {system_name}, reply with a hyphen-separated DIR code "
                f"(e.g. {common[0]}). Assumption: {application} unless specified otherwise."
            ),
        }

    def _evaluate(self, system_name: str, application: str, dir_code: str) -> Dict[str, Any]:
        key = _normalize_system_key(system_name)
        requirements = DIR_TEMPLATES.get(key) or DIR_TEMPLATES["media preparation"]
        ok, err = _validate_dir_code(dir_code, len(requirements))
        if not ok:
            out = self._dir_requirements(system_name, application)
            out["validation_error"] = err
            out["suggested_correction"] = (COMMON_DIR_CODES.get(key) or ["2-1-2-3-1-1"])[0]
            return out

        self.status(f"Validated DIR: {dir_code}")
        self.status("Searching industrial references…")

        search_queries = [
            f"{system_name} mixing agitator biopharmaceutical {application}",
            f"life science media preparation vessel agitator impeller selection",
            f"chromatography resin slurry tank agitator low shear" if "resin" in key else "",
        ]
        snippets: List[Dict[str, str]] = []
        for q in search_queries:
            q = q.strip()
            if not q:
                continue
            for hit in self.serper_search(q, num=5):
                snippets.append(hit)

        search_context = "\n".join(
            f"- {h.get('title', '')}: {h.get('snippet', '')} ({h.get('link', '')})"
            for h in snippets[:12]
        )

        self.status("Generating mixing technology evaluation…")
        user_prompt = (
            f"System: {system_name}\n"
            f"Application: {application}\n"
            f"Validated DIR code: {dir_code}\n\n"
            f"DIR requirement structure:\n{json.dumps(requirements, indent=2)}\n\n"
            f"Industrial search references:\n{search_context or '(no serper results — use engineering judgment)'}\n\n"
            f"{EVALUATION_PROMPT}"
        )
        raw = self.call_openai_json(system=SYSTEM_PROMPT, user=user_prompt)
        raw.setdefault("schema_version", "equipment_selector_v1")
        raw.setdefault("equipment_system", "mixing")
        raw.setdefault(
            "creator_attribution",
            {"display_name": "BPEAI", "app_id": self.app_id},
        )
        if not raw.get("equipment_tag"):
            raw["equipment_tag"] = _suggest_tag(system_name)
        if not raw.get("equipment_name"):
            raw["equipment_name"] = f"{system_name} — {raw.get('selected_model', 'Mixing System')}"

        validated = self.validate_result(raw)
        result = validated.model_dump()
        result["phase"] = "evaluation"
        result["dir_code"] = dir_code
        result["system_name"] = system_name
        result["application"] = application
        return result


def _suggest_tag(system_name: str) -> str:
    words = re.findall(r"[A-Za-z]+", system_name.upper())
    if not words:
        return "MX-101"
    prefix = "".join(w[0] for w in words[:2]) or "MX"
    return f"{prefix}-101"


def run_from_stdio() -> None:
    raw = sys.stdin.read()
    inputs = json.loads(raw) if raw.strip() else {}
    agent = MixingAgitatorMatcherAgent(status_callback=lambda m: print(m, file=sys.stderr))
    result = agent.run(inputs)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_from_stdio()
