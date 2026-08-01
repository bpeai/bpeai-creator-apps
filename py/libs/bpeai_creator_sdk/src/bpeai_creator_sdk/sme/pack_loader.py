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

APPROVED_LIFECYCLES = frozenset({"approved", "APPROVED"})


def knowledge_root(py_root: Path | None = None) -> Path:
    """Return ``py/knowledge`` for the creator-apps (or mirrored) tree."""
    root = py_root or repo_py_root()
    return (root / "knowledge").resolve()


def _load_yaml(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Knowledge pack file missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if data is not None else {}


def _norm(s: str) -> str:
    return (s or "").strip().lower()


@dataclass
class DirMenu:
    """Resolved DIR questionnaire for variant × industry × scenario."""

    scenario_id: str
    equipment_system_variant: str
    industry: str
    label: str
    lifecycle: str
    requirements: List[Dict[str, Any]]
    common_codes: List[Any]
    source: str = "menu"  # dir_catalog | menu | scenario_fallback
    menu_id: str = ""
    summary: str = ""

    @property
    def is_approved(self) -> bool:
        """True when menu may be used for evaluate (approved, draft_generated, or legacy fallback)."""
        life = _norm(self.lifecycle)
        if life in {"approved"}:
            return True
        if life in {"draft_generated"} and self.source in {"dir_catalog", "generated"}:
            return True
        return self.source == "scenario_fallback"


@dataclass
class KnowledgePack:
    """Loaded SME knowledge pack (filesystem or hydrated from DB/API)."""

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
    def default_variant(self) -> str:
        return str(self.meta.get("default_variant") or "general_mixing")

    @property
    def scenarios(self) -> Dict[str, Any]:
        raw = self.dir_requirements.get("scenarios") or {}
        base = dict(raw) if isinstance(raw, dict) else {}
        # Synthesize scenario keys from list catalog so aliases can resolve.
        for row in self.dir_menus:
            sid = str(row.get("scenario_id") or "").strip()
            if sid and sid not in base:
                base[sid] = {
                    "label": row.get("label") or sid,
                    "common_codes": row.get("common_codes") or [],
                    "requirements": row.get("requirements") or [],
                }
        return base

    @property
    def menus(self) -> List[Dict[str, Any]]:
        raw = self.dir_requirements.get("menus") or []
        return [m for m in raw if isinstance(m, dict)] if isinstance(raw, list) else []

    @property
    def dir_menus(self) -> List[Dict[str, Any]]:
        raw = self.dir_requirements.get("dir_menus") or []
        return [m for m in raw if isinstance(m, dict)] if isinstance(raw, list) else []

    def scenario(self, scenario_id: str) -> Dict[str, Any]:
        """Return legacy scenario mapping, or synthesize from a dir_menus row."""
        scen = self.scenarios.get(scenario_id)
        if isinstance(scen, dict):
            return scen
        for row in self.dir_menus:
            if _norm(str(row.get("scenario_id") or "")) == _norm(scenario_id):
                return {
                    "label": row.get("label") or scenario_id,
                    "common_codes": row.get("common_codes") or [],
                    "requirements": row.get("requirements") or [],
                }
        raise KeyError(f"Unknown scenario '{scenario_id}' in pack '{self.pack_id}'")

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

    def _normalize_common_codes(self, raw: Any) -> List[Dict[str, str]]:
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

    def common_code_entries(self, scenario_id: str) -> List[Dict[str, str]]:
        """Normalize common_codes to [{code, caption}, ...]."""
        scenario = self.scenario(scenario_id)
        return self._normalize_common_codes(scenario.get("common_codes") or [])

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

    def _menu_payload(self, menu: Mapping[str, Any], scenario_id: str) -> DirMenu:
        scenario = self.scenario(scenario_id)
        requirements = menu.get("requirements")
        if not isinstance(requirements, list) or not requirements:
            requirements = scenario.get("requirements") or []
        common = menu.get("common_codes")
        if common is None:
            common = scenario.get("common_codes") or []
        return DirMenu(
            scenario_id=scenario_id,
            equipment_system_variant=str(menu.get("equipment_system_variant") or self.default_variant),
            industry=str(menu.get("industry") or ""),
            label=str(menu.get("label") or scenario.get("label") or scenario_id),
            lifecycle=str(menu.get("lifecycle") or "approved"),
            requirements=[r for r in requirements if isinstance(r, dict)],
            common_codes=list(common) if isinstance(common, list) else [],
            source="menu",
        )


def _alias_match_text(*parts: str | None) -> str:
    """Join free-text fields used for scenario / variant alias matching."""
    return " ".join(str(p or "").strip() for p in parts if str(p or "").strip()).lower()


def _best_alias_match(aliases: Mapping[str, Any], text: str, *, allowed_ids: set[str] | None = None) -> str | None:
    """Return id whose alias term is the longest substring match in ``text``."""
    if not text or not isinstance(aliases, Mapping):
        return None
    scored: list[tuple[int, str]] = []
    for raw_id, terms in aliases.items():
        if not isinstance(terms, list):
            continue
        sid = str(raw_id)
        if allowed_ids is not None and sid not in allowed_ids:
            continue
        for term in terms:
            t = str(term).strip().lower()
            if t and t in text:
                scored.append((len(t), sid))
    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def resolve_scenario_id(
    pack: KnowledgePack,
    system_name: str,
    *,
    application: str | None = None,
) -> str:
    """Map system_name (+ optional application) to a scenario id via pack aliases.

    Alias matching uses the combined free text so packs can distinguish equipment
    roles (e.g. bioreactor vent vs buffer hold tank vent) within one technology pack.
    """
    text = _alias_match_text(system_name, application)
    aliases = pack.meta.get("scenario_aliases") or {}
    matched = _best_alias_match(
        aliases if isinstance(aliases, dict) else {},
        text,
        allowed_ids=set(pack.scenarios.keys()),
    )
    if matched:
        return matched
    if pack.default_scenario in pack.scenarios:
        return pack.default_scenario
    if pack.scenarios:
        return next(iter(pack.scenarios.keys()))
    raise KeyError(f"Pack '{pack.pack_id}' has no scenarios")


def resolve_variant_id(
    pack: KnowledgePack,
    system_name: str,
    variant: str | None = None,
    *,
    application: str | None = None,
) -> str:
    """Resolve equipment_system_variant from explicit input or system/application aliases."""
    explicit = (variant or "").strip()
    if explicit:
        return explicit
    text = _alias_match_text(system_name, application)
    aliases = pack.meta.get("variant_aliases") or {}
    matched = _best_alias_match(aliases if isinstance(aliases, dict) else {}, text)
    if matched:
        return matched
    return pack.default_variant


def resolve_industry(pack: KnowledgePack, industry: str | None = None, application: str | None = None) -> str:
    """Pick an industry key for DIR menu selection."""
    candidates = pack.meta.get("industries") or []
    if not isinstance(candidates, list):
        candidates = []
    cand_norm = {_norm(str(c)): str(c) for c in candidates}

    for raw in (industry, application):
        text = _norm(str(raw or ""))
        if not text:
            continue
        if text in cand_norm:
            return cand_norm[text]
        for key, label in cand_norm.items():
            if text in key or key in text:
                return label
        # Common short aliases
        if "biopharm" in text or text in {"biopharma", "biopharmaceutical"}:
            for key, label in cand_norm.items():
                if "biopharm" in key:
                    return label
        if "industrial" in text and "biotech" in text:
            for key, label in cand_norm.items():
                if "industrial" in key:
                    return label
        if "small molecule" in text or "pharma" in text:
            for key, label in cand_norm.items():
                if "small molecule" in key or "pharmaceutical" in key:
                    return label
        if text == "food" or "food" in text:
            for key, label in cand_norm.items():
                if "food" in key:
                    return label

    if candidates:
        return str(candidates[0])
    return "Biopharmaceuticals"


def resolve_dir_menu(
    pack: KnowledgePack,
    *,
    system_name: str = "",
    scenario_id: str | None = None,
    equipment_system_variant: str | None = None,
    industry: str | None = None,
    application: str | None = None,
    require_approved: bool = True,
) -> DirMenu:
    """Select DIR menu by (variant × industry × scenario); fall back to legacy scenario.

    Prefer list catalog ``dir_menus[]`` when present. Otherwise score legacy
    ``menus[]``, then fall back to ``scenarios[scenario_id]``.
    """
    # List catalog (SME-readable) — preferred
    from .dir_catalog import match_dir_menu

    catalog_hit = match_dir_menu(
        pack,
        system_name=system_name,
        scenario_id=scenario_id,
        equipment_system_variant=equipment_system_variant,
        industry=industry,
        application=application,
        allow_draft=not require_approved,
    )
    # When require_approved=True, still allow draft_generated for creator local runs
    # if it is the best fingerprint match (evaluate gate uses DirMenu.is_approved).
    if catalog_hit is None and require_approved:
        catalog_hit = match_dir_menu(
            pack,
            system_name=system_name,
            scenario_id=scenario_id,
            equipment_system_variant=equipment_system_variant,
            industry=industry,
            application=application,
            allow_draft=True,
        )
    if catalog_hit is not None:
        return catalog_hit

    sid = (scenario_id or "").strip() or resolve_scenario_id(
        pack, system_name, application=application
    )
    variant = resolve_variant_id(
        pack,
        system_name,
        equipment_system_variant,
        application=application,
    )
    ind = resolve_industry(pack, industry=industry, application=application)

    menus = pack.menus
    if menus:
        def score(m: Mapping[str, Any]) -> int:
            s = 0
            if _norm(str(m.get("scenario_id") or "")) == _norm(sid):
                s += 100
            if _norm(str(m.get("equipment_system_variant") or "")) == _norm(variant):
                s += 40
            if _norm(str(m.get("industry") or "")) == _norm(ind):
                s += 40
            lifecycle = _norm(str(m.get("lifecycle") or "approved"))
            if require_approved and lifecycle not in {"approved"}:
                return -1
            return s

        ranked = [(score(m), m) for m in menus]
        ranked = [(sc, m) for sc, m in ranked if sc >= 100]
        ranked.sort(key=lambda x: x[0], reverse=True)
        if ranked:
            best = ranked[0][1]
            return pack._menu_payload(best, str(best.get("scenario_id") or sid))

        # Same scenario + variant, any industry; then scenario-only approved menus
        for prefer_variant in (True, False):
            for m in menus:
                if _norm(str(m.get("scenario_id") or "")) != _norm(sid):
                    continue
                lifecycle = _norm(str(m.get("lifecycle") or "approved"))
                if require_approved and lifecycle not in {"approved"}:
                    continue
                if prefer_variant and _norm(str(m.get("equipment_system_variant") or "")) != _norm(variant):
                    continue
                return pack._menu_payload(m, sid)

    # Legacy scenario fallback (treated as approved for local/filesystem seeds)
    scenario = pack.scenario(sid)
    return DirMenu(
        scenario_id=sid,
        equipment_system_variant=variant,
        industry=ind,
        label=str(scenario.get("label") or sid),
        lifecycle="approved",
        requirements=[r for r in (scenario.get("requirements") or []) if isinstance(r, dict)],
        common_codes=list(scenario.get("common_codes") or [])
        if isinstance(scenario.get("common_codes"), list)
        else [],
        source="scenario_fallback",
    )


def knowledge_pack_from_dict(
    pack_id: str,
    payload: Mapping[str, Any],
    *,
    path: Path | None = None,
) -> KnowledgePack:
    """Hydrate a KnowledgePack from a DB/API JSON payload."""
    meta = dict(payload.get("meta") or payload.get("pack") or {})
    meta.setdefault("pack_id", pack_id)
    dir_req = payload.get("dir_requirements") or {}
    if not isinstance(dir_req, dict):
        dir_req = {}
    # DB-shaped menus list → dir_requirements.menus
    if "menus" in payload and isinstance(payload["menus"], list):
        dir_req = {**dir_req, "menus": payload["menus"]}
    content = payload.get("content") or {}
    if isinstance(content, dict):
        equipment_options = content.get("equipment_options") or payload.get("equipment_options") or {}
        validation_rules = content.get("validation_rules") or payload.get("validation_rules") or {}
        prompt_fragments = content.get("prompt_fragments") or payload.get("prompt_fragments") or {}
        report_outline = content.get("report_outline") or payload.get("report_outline") or {}
        pptx_outline = content.get("pptx_outline") or payload.get("pptx_outline") or {}
        if content.get("meta") and isinstance(content["meta"], dict):
            meta = {**meta, **content["meta"]}
        # Prefer full uploaded dir_requirements (incl. dir_menus) from content blob
        content_dir = content.get("dir_requirements")
        if isinstance(content_dir, dict):
            merged = {**dir_req, **content_dir}
            # Keep non-empty list catalogs from either side
            for key in ("dir_menus", "menus"):
                left = dir_req.get(key) if isinstance(dir_req.get(key), list) else []
                right = content_dir.get(key) if isinstance(content_dir.get(key), list) else []
                merged[key] = right or left
            dir_req = merged
    else:
        equipment_options = payload.get("equipment_options") or {}
        validation_rules = payload.get("validation_rules") or {}
        prompt_fragments = payload.get("prompt_fragments") or {}
        report_outline = payload.get("report_outline") or {}
        pptx_outline = payload.get("pptx_outline") or {}

    # Normalize: if menus present but dir_menus empty, mirror for list-catalog matchers
    menus = dir_req.get("menus") if isinstance(dir_req.get("menus"), list) else []
    dir_menus = dir_req.get("dir_menus") if isinstance(dir_req.get("dir_menus"), list) else []
    if menus and not dir_menus:
        dir_req = {**dir_req, "dir_menus": menus}
    elif dir_menus and not menus:
        dir_req = {**dir_req, "menus": dir_menus}

    return KnowledgePack(
        pack_id=str(meta.get("pack_id") or pack_id),
        path=path or Path(f"<db:{pack_id}>"),
        meta=meta if isinstance(meta, dict) else {},
        dir_requirements=dir_req,
        equipment_options=equipment_options if isinstance(equipment_options, dict) else {},
        validation_rules=validation_rules if isinstance(validation_rules, dict) else {},
        prompt_fragments=prompt_fragments if isinstance(prompt_fragments, dict) else {},
        report_outline=report_outline if isinstance(report_outline, dict) else {},
        pptx_outline=pptx_outline if isinstance(pptx_outline, dict) else {},
    )


def load_knowledge_pack(
    pack_id: str,
    *,
    py_root: Path | None = None,
    pack_root: Path | None = None,
    payload: Mapping[str, Any] | None = None,
) -> KnowledgePack:
    """Load pack from ``payload`` (DB/API) or ``py/knowledge/<pack_id>/`` YAML set."""
    pid = (pack_id or "").strip()
    if not pid:
        raise ValueError("pack_id is required")
    if payload is not None:
        return knowledge_pack_from_dict(pid, payload)

    root = Path(pack_root) if pack_root else knowledge_root(py_root)
    path = (root / pid).resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"Knowledge pack not found: {path}")

    meta = _load_yaml(path / "pack.yaml")
    if not isinstance(meta, dict):
        raise TypeError(f"pack.yaml must be a mapping: {path / 'pack.yaml'}")

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
