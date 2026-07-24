from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import yaml

from ..local_run import repo_py_root

PACK_FILES = (
    "pack.yaml",
    "dir_requirements.yaml",
    "equipment_options.yaml",
    "validation_rules.yaml",
    "prompt_fragments.yaml",
)


def knowledge_root(py_root: Path | None = None) -> Path:
    """Return ``py/knowledge`` for the creator-apps (or mirrored) tree."""
    root = py_root or repo_py_root()
    return (root / "knowledge").resolve()


def _load_yaml(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Knowledge pack file missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if data is not None else {}


@dataclass
class KnowledgePack:
    """Loaded SME knowledge pack for one equipment system."""

    pack_id: str
    path: Path
    meta: Dict[str, Any]
    dir_requirements: Dict[str, Any]
    equipment_options: Dict[str, Any]
    validation_rules: Dict[str, Any]
    prompt_fragments: Dict[str, Any] = field(default_factory=dict)
    report_outline: Dict[str, Any] = field(default_factory=dict)
    pptx_outline: Dict[str, Any] = field(default_factory=dict)

    @property
    def equipment_system(self) -> str:
        return str(self.meta.get("equipment_system") or self.pack_id)

    @property
    def default_scenario(self) -> str:
        return str(self.meta.get("default_scenario") or "default")

    @property
    def scenarios(self) -> Dict[str, Any]:
        raw = self.dir_requirements.get("scenarios") or {}
        return raw if isinstance(raw, dict) else {}

    def scenario(self, scenario_id: str) -> Dict[str, Any]:
        scen = self.scenarios.get(scenario_id)
        if not isinstance(scen, dict):
            raise KeyError(f"Unknown scenario '{scenario_id}' in pack '{self.pack_id}'")
        return scen

    def option_catalog(self) -> List[Dict[str, Any]]:
        opts = self.equipment_options.get("options") or []
        return [o for o in opts if isinstance(o, dict)]

    def option_names(self) -> List[str]:
        names: List[str] = []
        for opt in self.option_catalog():
            name = str(opt.get("name") or "").strip()
            if name:
                names.append(name)
        return names

    def common_code_entries(self, scenario_id: str) -> List[Dict[str, str]]:
        """Normalize common_codes to [{code, caption}, ...]."""
        scenario = self.scenario(scenario_id)
        raw = scenario.get("common_codes") or []
        out: List[Dict[str, str]] = []
        if not isinstance(raw, list):
            return out
        for item in raw:
            if isinstance(item, str):
                out.append({"code": item, "caption": ""})
            elif isinstance(item, Mapping) and item.get("code"):
                out.append(
                    {
                        "code": str(item["code"]),
                        "caption": str(item.get("caption") or ""),
                    }
                )
        return out

    def common_codes(self, scenario_id: str) -> List[str]:
        return [e["code"] for e in self.common_code_entries(scenario_id)]

    def fragment(self, key: str, default: str = "") -> str:
        fragments = self.prompt_fragments.get("fragments") or {}
        if not isinstance(fragments, Mapping):
            return default
        value = fragments.get(key)
        return str(value).strip() if value is not None else default

    def required_report_headings(self) -> List[str]:
        headings = self.report_outline.get("required_headings") or []
        return [str(h) for h in headings] if isinstance(headings, list) else []

    def build_system_prompt(self) -> str:
        parts = [
            self.fragment("role"),
            self.fragment("scope"),
            self.fragment("application_default"),
            self.fragment("evaluation_goals"),
            self.fragment("workflow"),
            self.fragment("output_style"),
            self.fragment("depth_requirements"),
            self.fragment("response_outline"),
            self.fragment("exclusions_rule"),
            "When producing structured JSON output, follow equipment_selector_v1 exactly "
            "and populate all GPT-parity fields (design_basis, objectives, failure_modes, "
            "evaluation_matrix, alternate_basis, do_not_specify, preliminary_specs, "
            "mixing_options, datasheet_markdown).",
        ]
        emphasize = (self.meta.get("prompt_hooks") or {}).get("emphasize") or []
        if isinstance(emphasize, list) and emphasize:
            parts.append("SME emphasis:\n" + "\n".join(f"- {e}" for e in emphasize))
        return "\n\n".join(p for p in parts if p)


def resolve_scenario_id(pack: KnowledgePack, system_name: str) -> str:
    """Map free-text system_name to a scenario id using pack aliases."""
    text = (system_name or "").strip().lower()
    aliases = pack.meta.get("scenario_aliases") or {}
    if isinstance(aliases, dict):
        # Longer aliases first so "media preparation" beats "media".
        scored: list[tuple[int, str]] = []
        for scenario_id, terms in aliases.items():
            if not isinstance(terms, list):
                continue
            for term in terms:
                t = str(term).strip().lower()
                if t and t in text:
                    scored.append((len(t), str(scenario_id)))
        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            return scored[0][1]
    if pack.default_scenario in pack.scenarios:
        return pack.default_scenario
    if pack.scenarios:
        return next(iter(pack.scenarios.keys()))
    raise KeyError(f"Pack '{pack.pack_id}' has no scenarios")


def load_knowledge_pack(
    pack_id: str,
    *,
    py_root: Path | None = None,
    pack_root: Path | None = None,
) -> KnowledgePack:
    """Load ``py/knowledge/<pack_id>/`` YAML set."""
    pid = (pack_id or "").strip()
    if not pid:
        raise ValueError("pack_id is required")
    root = Path(pack_root) if pack_root else knowledge_root(py_root)
    path = (root / pid).resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"Knowledge pack not found: {path}")

    meta = _load_yaml(path / "pack.yaml")
    if not isinstance(meta, dict):
        raise TypeError(f"pack.yaml must be a mapping: {path / 'pack.yaml'}")

    declared = str(meta.get("pack_id") or pid).strip()
    if declared != pid:
        # Allow folder name to win; warn via inconsistency only if empty declared.
        meta["pack_id"] = pid

    dir_req = _load_yaml(path / "dir_requirements.yaml")
    if not isinstance(dir_req, dict):
        raise TypeError("dir_requirements.yaml must be a mapping")

    options = _load_yaml(path / "equipment_options.yaml")
    if not isinstance(options, dict):
        raise TypeError("equipment_options.yaml must be a mapping")

    rules = _load_yaml(path / "validation_rules.yaml")
    if not isinstance(rules, dict):
        raise TypeError("validation_rules.yaml must be a mapping")

    fragments_path = path / "prompt_fragments.yaml"
    fragments: Dict[str, Any] = {}
    if fragments_path.is_file():
        raw_frag = _load_yaml(fragments_path)
        if isinstance(raw_frag, dict):
            fragments = raw_frag

    report_outline: Dict[str, Any] = {}
    report_path = path / "report_outline.yaml"
    if report_path.is_file():
        raw_report = _load_yaml(report_path)
        if isinstance(raw_report, dict):
            report_outline = raw_report

    pptx_outline: Dict[str, Any] = {}
    pptx_path = path / "pptx_outline.yaml"
    if pptx_path.is_file():
        raw_pptx = _load_yaml(pptx_path)
        if isinstance(raw_pptx, dict):
            pptx_outline = raw_pptx

    return KnowledgePack(
        pack_id=pid,
        path=path,
        meta=meta,
        dir_requirements=dir_req,
        equipment_options=options,
        validation_rules=rules,
        prompt_fragments=fragments,
        report_outline=report_outline,
        pptx_outline=pptx_outline,
    )
