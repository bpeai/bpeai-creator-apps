from __future__ import annotations

"""Detect / write knowledge-pack YAML components (draft-for-approval).

Agents call LLM to fill missing files; this module handles filesystem inventory,
shape normalization for draft LLM output, shared structure examples, and seeding
of visual template references (PPTX/PDF) into creator packs.
"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import yaml

from .pack_loader import PACK_FILES, knowledge_root, unwrap_loaded_component

# Core files required by load_knowledge_pack; outlines are strongly recommended.
OPTIONAL_PACK_FILES = (
    "report_outline.yaml",
    "pptx_outline.yaml",
    "search_queries.yaml",
    "README.md",
)

ALL_BOOTSTRAP_FILES = PACK_FILES + OPTIONAL_PACK_FILES

_COMPONENT_NAME_KEYS = frozenset(ALL_BOOTSTRAP_FILES)
_STAMP_KEYS = frozenset(
    {"pack_id", "equipment_system", "version", "approval_status", "description", "label"}
)

DRAFT_BANNER = (
    "# DRAFT — initial version pending SME / platform approval.\n"
    "# Do not treat as production-validated content until approved.\n"
)


class _RoundTripDumper(yaml.SafeDumper):
    """Dump strings so ``safe_load`` can always parse them.

    PyYAML's default plain scalars wrap at ``width`` and then fail to round-trip
    when the text contains ``: `` (e.g. ``Material: 316L stainless``).
    """


def _represent_str(dumper: yaml.SafeDumper, data: str) -> yaml.Node:
    if "\n" in data or ": " in data or data.startswith("{") or data.startswith("["):
        style = "|" if ("\n" in data or ": " in data) else '"'
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_RoundTripDumper.add_representer(str, _represent_str)


def _dump_yaml(content: Mapping[str, Any]) -> str:
    return yaml.dump(
        dict(content),
        Dumper=_RoundTripDumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=100,
    )


_FIT_ALLOWED = ["best", "strong", "conditional", "limited", "add-on", "special-case"]


def pack_dir(
    pack_id: str,
    *,
    py_root: Path | None = None,
    pack_root: Path | None = None,
) -> Path:
    pid = (pack_id or "").strip()
    if not pid:
        raise ValueError("pack_id is required")
    root = Path(pack_root) if pack_root else knowledge_root(py_root)
    return (root / pid).resolve()


def list_missing_pack_files(
    pack_id: str,
    *,
    py_root: Path | None = None,
    pack_root: Path | None = None,
    required: Sequence[str] = PACK_FILES,
    optional: Sequence[str] = OPTIONAL_PACK_FILES,
    include_optional: bool = True,
) -> List[str]:
    """Return filenames that are missing under the pack directory."""
    root = pack_dir(pack_id, py_root=py_root, pack_root=pack_root)
    wanted = list(required)
    if include_optional:
        wanted.extend(optional)
    missing: List[str] = []
    for name in wanted:
        if not (root / name).is_file():
            missing.append(name)
    return missing


def pack_is_loadable(
    pack_id: str,
    *,
    py_root: Path | None = None,
    pack_root: Path | None = None,
) -> bool:
    """True when every core PACK_FILES entry exists (optional files ignored)."""
    return not list_missing_pack_files(
        pack_id,
        py_root=py_root,
        pack_root=pack_root,
        include_optional=False,
    )


def write_pack_file(
    pack_id: str,
    filename: str,
    content: str | Mapping[str, Any],
    *,
    py_root: Path | None = None,
    draft: bool = True,
    overwrite: bool = False,
) -> Path:
    """Write one pack file. Mappings are dumped as YAML with a draft banner."""
    root = pack_dir(pack_id, py_root=py_root)
    root.mkdir(parents=True, exist_ok=True)
    target = root / filename
    if target.is_file() and not overwrite:
        return target

    if isinstance(content, Mapping):
        body = _dump_yaml(content)
        text = (DRAFT_BANNER if draft and not filename.endswith(".md") else "") + body
    else:
        text = str(content)
        if draft and filename.endswith(".md") and "pending" not in text.lower():
            text = (
                "> **DRAFT** — initial version pending SME / platform approval.\n\n" + text
            )
        elif draft and not filename.endswith(".md") and not text.lstrip().startswith("#"):
            text = DRAFT_BANNER + text

    target.write_text(text, encoding="utf-8")
    return target


def stamp_draft_meta(meta: Dict[str, Any], *, pack_id: str, equipment_system: str) -> Dict[str, Any]:
    """Ensure pack.yaml identity + approval_status fields for bootstrapped packs."""
    out = dict(meta)
    out["pack_id"] = pack_id
    out.setdefault("equipment_system", equipment_system or pack_id)
    out.setdefault("version", "0.0.1-draft")
    out["approval_status"] = "draft_pending_sme_approval"
    out.setdefault(
        "description",
        (
            f"Initial auto-generated SME pack for {out['equipment_system']}. "
            "Subject to SME / platform approval before production use."
        ),
    )
    return out


def component_schema_hints() -> Dict[str, str]:
    """Short structural hints for LLM pack-component generation."""
    return {
        "pack.yaml": (
            "FLAT mapping only for this file (never nest other filenames as keys). "
            "Fields: pack_id, equipment_system, version, label, description, "
            "industries (list), default_scenario, default_variant, scenario_aliases "
            "(scenario→list of alias strings), variant_aliases, taxonomy_preparation_ids "
            "(list), prompt_hooks as an object {system_role: string, emphasize: [strings]}."
        ),
        "dir_requirements.yaml": (
            "Emit dir_menus only (list catalog). Do NOT include legacy menus or "
            "scenarios maps — the loader synthesizes those from dir_menus. "
            "dir_menus: ["
            "{menu_id, status (approved|draft_generated), scenario_id, "
            "equipment_system_variant, industry, system_examples, label, summary, "
            "common_codes: [{code, caption}], requirements: [{index, label, "
            "options: [{index, text}]}]}]. "
            "common_codes MUST be hyphen-separated numeric DIR starters that match "
            "requirement length (e.g. 2-1-3), each with a one-line caption — "
            "not mnemonic tags like SIP. "
            "DIR code = hyphen-separated 1-based option indexes."
        ),
        "equipment_options.yaml": (
            "Mapping with options: [{id, name, tags, typical_fit, manufacturers}], "
            "do_not_specify_defaults (list), manufacturers_examples (list)."
        ),
        "validation_rules.yaml": (
            "Mapping where dir_code, application, equipment_option_name, and "
            "selected_model are EACH nested objects (never bare strings). Example: "
            "dir_code: {min_index: 1}, application: {mode: soft, normalize: "
            "lowercase_strip, aliases: {biopharma: biopharmaceutical}}, "
            "equipment_option_name: {mode: soft}, selected_model: {mode: soft}, "
            "fit_enum: {allowed: [best, strong, conditional, limited, add-on, "
            "special-case]}, equipment_system_field: {must_equal: <system>, mode: hard}."
        ),
        "prompt_fragments.yaml": (
            "Mapping with fragments as a flat string map: {role, scope, "
            "evaluation_goals, application_default, workflow, output_style, "
            "depth_requirements, response_outline, exclusions_rule}. Each value is "
            "a string (not nested objects with label/content). Optional calls: map for "
            "per-handshake SME text: dir_generate.{system,instructions}, "
            "evaluate.user_instructions, evaluate_repair.instructions, "
            "pptx.{system_extra,instructions}, pack_bootstrap.system."
        ),
        "report_outline.yaml": (
            "Mapping with required_headings (list of section titles), sections "
            "([{id, heading, description}]), min option count fields as appropriate."
        ),
        "pptx_outline.yaml": (
            "Mapping with slide_count (7), title_prefix, slides ([{index, id, title, ...}]), "
            "style (fonts/colors), reference_decks (list of references/*.pptx paths), notes."
        ),
        "search_queries.yaml": (
            "Mapping with dir_generate.templates (list of query strings with placeholders "
            "{system_name}, {application}, {equipment_system}) and evaluate.templates, "
            "evaluate.slots (placeholder→list of DIR label substrings), evaluate.static "
            "(always-run vendor/domain queries). Domain-specific — do not copy mixing "
            "vendor names into unrelated equipment systems."
        ),
        "README.md": (
            "Markdown describing the pack purpose, draft/approval status, and how to "
            "edit YAML / replace reference PPTX."
        ),
    }


def structure_example_snippet(filename: str, *, py_root: Path | None = None) -> str:
    """Return a truncated structural example from ``_examples/mixing_stub`` (not website packs)."""
    root = Path(py_root) if py_root else knowledge_root().parent
    stub = root / "knowledge" / "_examples" / "mixing_stub" / filename
    if stub.is_file():
        return stub.read_text(encoding="utf-8")[:6000]
    # Optional outlines may be absent from the stub — fall back to pack.yaml shape.
    alt = root / "knowledge" / "_examples" / "mixing_stub" / "pack.yaml"
    if alt.is_file():
        text = alt.read_text(encoding="utf-8")[:4000]
        return f"(mixing_stub/{filename} missing; pack.yaml excerpt for shape only)\n{text}"
    return "(no mixing_stub structure example available)"


def unwrap_component_payload(filename: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Unwrap LLM mistakes that nest content under the target filename key."""
    data = unwrap_loaded_component(filename, dict(payload))
    if not isinstance(data, dict):
        return {}
    if filename in data and isinstance(data[filename], Mapping):
        inner = dict(data[filename])
        other = {
            k: v
            for k, v in data.items()
            if k != filename and k not in _COMPONENT_NAME_KEYS and k not in _STAMP_KEYS
        }
        if not other:
            for k in _STAMP_KEYS:
                if k in data and k not in inner:
                    inner[k] = data[k]
            return inner
    # Drop sibling filename keys that belong in other files.
    cleaned = {k: v for k, v in data.items() if k not in _COMPONENT_NAME_KEYS or k == filename}
    if filename in cleaned and isinstance(cleaned[filename], Mapping) and len(cleaned) == 1:
        return dict(cleaned[filename])
    return cleaned


def _as_mapping(value: Any, default: Dict[str, Any]) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else dict(default)


def _normalize_dir_requirement_rows(reqs_in: Any) -> List[Dict[str, Any]]:
    reqs_out: List[Dict[str, Any]] = []
    if not isinstance(reqs_in, list):
        return reqs_out
    for i, req in enumerate(reqs_in):
        if not isinstance(req, Mapping):
            continue
        r = dict(req)
        r.setdefault("index", i + 1)
        opts_in = r.get("options") or []
        opts_out: List[Dict[str, Any]] = []
        if isinstance(opts_in, list):
            for j, opt in enumerate(opts_in):
                if isinstance(opt, str):
                    opts_out.append({"index": j + 1, "text": opt})
                elif isinstance(opt, Mapping):
                    o = dict(opt)
                    o.setdefault("index", j + 1)
                    if "text" not in o:
                        o["text"] = str(
                            o.get("label") or o.get("name") or o.get("value") or ""
                        )
                    opts_out.append(o)
        r["options"] = opts_out
        reqs_out.append(r)
    return reqs_out


def _normalize_common_codes(codes: Any) -> List[Dict[str, Any]]:
    if not isinstance(codes, list):
        return []
    norm_codes: List[Dict[str, Any]] = []
    for item in codes:
        if isinstance(item, str):
            norm_codes.append({"code": item, "caption": ""})
        elif isinstance(item, Mapping) and item.get("code"):
            c = dict(item)
            if "caption" not in c and "relevance" in c:
                c["caption"] = c.get("relevance")
            norm_codes.append(c)
    return norm_codes


def _normalize_dir_menu_row(
    row: Mapping[str, Any], *, default_sid: str = ""
) -> Dict[str, Any]:
    m = dict(row)
    if "requirements" not in m and isinstance(m.get("dir_requirements"), list):
        m["requirements"] = m.pop("dir_requirements")
    m["requirements"] = _normalize_dir_requirement_rows(m.get("requirements") or [])
    m["common_codes"] = _normalize_common_codes(m.get("common_codes") or [])
    if default_sid:
        m.setdefault("scenario_id", default_sid)
    return m


def dir_requirements_dir_menus_only(data: Dict[str, Any]) -> Dict[str, Any]:
    """Collapse bootstrap/legacy shapes to a single ``dir_menus`` catalog."""
    menus_out: List[Dict[str, Any]] = []
    raw_menus = data.get("dir_menus")
    if isinstance(raw_menus, list) and raw_menus:
        for row in raw_menus:
            if isinstance(row, Mapping):
                menus_out.append(_normalize_dir_menu_row(row))
    elif isinstance(data.get("scenarios"), Mapping) and data["scenarios"]:
        for sid, scen in data["scenarios"].items():
            if isinstance(scen, Mapping):
                menus_out.append(_normalize_dir_menu_row(scen, default_sid=str(sid)))
    elif isinstance(data.get("menus"), list) and data["menus"]:
        for row in data["menus"]:
            if isinstance(row, Mapping):
                menus_out.append(_normalize_dir_menu_row(row))
    data["dir_menus"] = menus_out
    data.pop("menus", None)
    data.pop("scenarios", None)
    return data


def scenario_ids_from_dir_req(dir_req: Mapping[str, Any]) -> List[str]:
    """Scenario ids from ``dir_menus`` first, then leftover ``scenarios`` keys."""
    ids: List[str] = []
    menus = dir_req.get("dir_menus")
    if isinstance(menus, list):
        for row in menus:
            if not isinstance(row, Mapping):
                continue
            sid = str(row.get("scenario_id") or "").strip()
            if sid and sid not in ids:
                ids.append(sid)
    scenarios = dir_req.get("scenarios") or {}
    if isinstance(scenarios, Mapping):
        for key in scenarios.keys():
            sid = str(key).strip()
            if sid and sid not in ids:
                ids.append(sid)
    return ids


def _normalize_fragment_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("content", "text", "value", "description"):
            if isinstance(value.get(key), str) and value.get(key):
                return str(value[key])
        return yaml.safe_dump(dict(value), sort_keys=False).strip()
    return str(value or "")


def normalize_bootstrapped_component(
    filename: str,
    payload: Mapping[str, Any],
    *,
    pack_id: str = "",
    equipment_system: str = "",
) -> Dict[str, Any]:
    """Coerce common LLM draft mistakes into loader-compatible shapes."""
    data = unwrap_component_payload(filename, payload)

    if filename == "pack.yaml":
        data = stamp_draft_meta(
            data, pack_id=pack_id or str(data.get("pack_id") or ""), equipment_system=equipment_system
        )
        hooks = data.get("prompt_hooks")
        if not isinstance(hooks, Mapping):
            data["prompt_hooks"] = {
                "system_role": str(hooks or f"{equipment_system or pack_id}_expert"),
                "emphasize": ["Draft pack — confirm assumptions with SME before production use"],
            }
        else:
            hooks_d = dict(hooks)
            if not isinstance(hooks_d.get("emphasize"), list):
                hooks_d["emphasize"] = [
                    str(hooks_d.get("emphasize") or "Draft pack pending SME approval")
                ]
            hooks_d.setdefault("system_role", f"{equipment_system or pack_id}_expert")
            data["prompt_hooks"] = hooks_d
        if not isinstance(data.get("industries"), list):
            data["industries"] = ["Biopharmaceuticals"]
        if not isinstance(data.get("scenario_aliases"), dict):
            data["scenario_aliases"] = {}
        return data

    if filename == "validation_rules.yaml":
        data["dir_code"] = _as_mapping(data.get("dir_code"), {"min_index": 1})
        data["dir_code"].setdefault("min_index", 1)
        data["application"] = _as_mapping(
            data.get("application"),
            {
                "mode": "soft",
                "normalize": "lowercase_strip",
                "aliases": {"biopharma": "biopharmaceutical"},
            },
        )
        data["application"].setdefault("mode", "soft")
        data["application"].setdefault("normalize", "lowercase_strip")
        if not isinstance(data["application"].get("aliases"), Mapping):
            data["application"]["aliases"] = {"biopharma": "biopharmaceutical"}
        data["equipment_option_name"] = _as_mapping(
            data.get("equipment_option_name"), {"mode": "soft"}
        )
        data["equipment_option_name"].setdefault("mode", "soft")
        data["selected_model"] = _as_mapping(data.get("selected_model"), {"mode": "soft"})
        fit = _as_mapping(data.get("fit_enum"), {"allowed": list(_FIT_ALLOWED)})
        allowed = fit.get("allowed")
        if not isinstance(allowed, list) or not allowed:
            fit["allowed"] = list(_FIT_ALLOWED)
        data["fit_enum"] = fit
        field = _as_mapping(data.get("equipment_system_field"), {"mode": "hard"})
        field.setdefault("mode", "hard")
        if equipment_system:
            field["must_equal"] = equipment_system
        else:
            field.setdefault("must_equal", pack_id or "equipment")
        data["equipment_system_field"] = field
        return data

    if filename == "dir_requirements.yaml":
        return dir_requirements_dir_menus_only(data)

    if filename == "equipment_options.yaml":
        if "options" not in data and isinstance(data.get("equipment_options"), list):
            data["options"] = data.pop("equipment_options")
        opts = data.get("options")
        if isinstance(opts, list):
            fixed_opts = []
            for opt in opts:
                if not isinstance(opt, Mapping):
                    continue
                o = dict(opt)
                if "name" not in o and o.get("label"):
                    o["name"] = o["label"]
                if "manufacturers" not in o and isinstance(o.get("manufacturer_families"), list):
                    o["manufacturers"] = o["manufacturer_families"]
                fixed_opts.append(o)
            data["options"] = fixed_opts
        return data

    if filename == "prompt_fragments.yaml":
        fragments = data.get("fragments")
        if not isinstance(fragments, Mapping):
            # Whole payload may already be the fragment map.
            fragments = {
                k: v
                for k, v in data.items()
                if k
                not in {
                    "file",
                    "pack_id",
                    "equipment_system",
                    "app",
                    "description",
                    "approval_status",
                }
            }
            data = {"fragments": fragments}
            fragments = data["fragments"]
        # Unwrap fragments: { "prompt_fragments.yaml": { "fragments": {...} } }
        if isinstance(fragments, Mapping) and filename in fragments:
            inner = fragments.get(filename)
            if isinstance(inner, Mapping) and isinstance(inner.get("fragments"), Mapping):
                fragments = inner["fragments"]
            elif isinstance(inner, Mapping):
                fragments = inner
        flat: Dict[str, str] = {}
        if isinstance(fragments, Mapping):
            for key, value in fragments.items():
                if key in _COMPONENT_NAME_KEYS:
                    continue
                flat[str(key)] = _normalize_fragment_value(value)
        data["fragments"] = flat
        return data

    if filename == "report_outline.yaml":
        if not isinstance(data.get("required_headings"), list):
            data["required_headings"] = [
                "Validated DIR",
                "Design basis",
                "Strong-fit equipment types",
                "Recommended basis of design",
                "Option evaluation",
                "Do not specify",
                "Preliminary specification",
                "Manufacturers and references",
            ]
        return data

    if filename == "pptx_outline.yaml":
        # Don't replace a still-wrapped LLM string with placeholder slides.
        if filename in data and isinstance(data.get(filename), str):
            return data
        data.setdefault("slide_count", 7)
        if not isinstance(data.get("slides"), list):
            data["slides"] = [
                {"index": i, "title": f"Slide {i}"} for i in range(1, 8)
            ]
        if not isinstance(data.get("reference_decks"), list):
            data["reference_decks"] = []
        return data

    return data


def component_payload_issues(filename: str, payload: Mapping[str, Any]) -> List[str]:
    """Return structural issues that would break the pack loader / DIR flow."""
    issues: List[str] = []
    if not isinstance(payload, Mapping):
        return [f"{filename}: payload is not a mapping"]

    if filename == "pack.yaml":
        if any(k in payload for k in _COMPONENT_NAME_KEYS):
            issues.append("pack.yaml nests other component filenames as keys")
        if not isinstance(payload.get("prompt_hooks"), Mapping):
            issues.append("pack.yaml.prompt_hooks must be a mapping")
    elif filename == "validation_rules.yaml":
        for key in ("application", "dir_code", "equipment_option_name"):
            if not isinstance(payload.get(key), Mapping):
                issues.append(f"validation_rules.yaml.{key} must be a mapping")
        fit = payload.get("fit_enum")
        if not isinstance(fit, Mapping) or not isinstance(fit.get("allowed"), list):
            issues.append("validation_rules.yaml.fit_enum.allowed must be a list")
    elif filename == "dir_requirements.yaml":
        menus = payload.get("dir_menus")
        if not isinstance(menus, list) or not menus:
            issues.append("dir_requirements.yaml.dir_menus must be a non-empty list")
        else:
            for i, row in enumerate(menus):
                if not isinstance(row, Mapping):
                    issues.append(f"dir_menus[{i}] must be a mapping")
                    continue
                reqs = row.get("requirements")
                if not isinstance(reqs, list) or not reqs:
                    issues.append(f"dir_menus[{i}] needs requirements[]")
                    continue
                first = reqs[0]
                if not isinstance(first, Mapping) or not isinstance(first.get("options"), list):
                    issues.append(f"dir_menus[{i}] requirements need options[]")
                elif first.get("options") and not isinstance(first["options"][0], Mapping):
                    issues.append(f"dir_menus[{i}] options must be {{index, text}} objects")
    elif filename == "equipment_options.yaml":
        opts = payload.get("options")
        if not isinstance(opts, list) or not opts:
            issues.append("equipment_options.yaml.options must be a non-empty list")
    elif filename == "prompt_fragments.yaml":
        fr = payload.get("fragments")
        if not isinstance(fr, Mapping) or not fr:
            issues.append("prompt_fragments.yaml.fragments must be a non-empty mapping")
        elif any(isinstance(v, Mapping) for v in fr.values()):
            issues.append("prompt_fragments.yaml.fragments values must be strings")
    return issues


def prepare_bootstrapped_component(
    filename: str,
    payload: Mapping[str, Any],
    *,
    pack_id: str = "",
    equipment_system: str = "",
) -> Dict[str, Any]:
    """Normalize LLM JSON and raise if still structurally unusable."""
    normalized = normalize_bootstrapped_component(
        filename,
        payload,
        pack_id=pack_id,
        equipment_system=equipment_system,
    )
    issues = component_payload_issues(filename, normalized)
    if issues:
        raise ValueError(
            f"Bootstrapped {filename} failed structural checks: " + "; ".join(issues)
        )
    return normalized


def repair_existing_pack_components(
    pack_id: str,
    *,
    py_root: Path | None = None,
    equipment_system: str = "",
) -> List[str]:
    """Normalize on-disk draft YAML in place; return filenames rewritten."""
    root = pack_dir(pack_id, py_root=py_root)
    if not root.is_dir():
        return []
    repaired: List[str] = []
    eq = equipment_system or pack_id
    for filename in ALL_BOOTSTRAP_FILES:
        if filename == "README.md":
            continue
        path = root / filename
        if not path.is_file():
            continue
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if not isinstance(raw, Mapping):
            continue
        before_issues = component_payload_issues(filename, raw)
        normalized = normalize_bootstrapped_component(
            filename, raw, pack_id=pack_id, equipment_system=eq
        )
        after_issues = component_payload_issues(filename, normalized)
        if before_issues or after_issues != before_issues or normalized != dict(raw):
            if not after_issues:
                write_pack_file(
                    pack_id,
                    filename,
                    normalized,
                    py_root=py_root,
                    draft=True,
                    overwrite=True,
                )
                repaired.append(filename)
    return repaired


def _folder_has_style_templates(path: Path) -> bool:
    try:
        return path.is_dir() and (
            any(path.glob("*.pptx")) or any(path.glob("*.pdf"))
        )
    except OSError:
        return False


def template_references_root(py_root: Path | None = None) -> Path | None:
    """Locate shared PPTX/PDF style templates for seeding new creator packs.

    Preference order:
      1. ``BPEAI_TEMPLATE_REFERENCES_ROOT`` / ``BPEAI_REFERENCES_ROOT``
      2. Committed ``py/knowledge/_templates/references/`` (this repo)
      3. Website staging ``website/references`` / platform mixing pack references

    Creator pack *YAML* is never copied from platform packs. Only visual template
    documents (any ``*.pptx`` / ``*.pdf`` in the chosen folder) are seeded.
    Filenames need not be standardized.
    """
    for key in ("BPEAI_TEMPLATE_REFERENCES_ROOT", "BPEAI_REFERENCES_ROOT"):
        env = (os.getenv(key) or "").strip()
        if env:
            p = Path(env)
            if _folder_has_style_templates(p):
                return p.resolve()

    candidates: List[Path] = []
    if py_root is not None:
        base = Path(py_root).resolve()
        # Preferred: committed shared shells in creator-apps (no bpeai clone needed).
        candidates.append(base / "knowledge" / "_templates" / "references")
        candidates.extend(
            [
                base.parent.parent / "bpeai" / "website" / "references",
                base.parent.parent.parent / "bpeai" / "website" / "references",
                base.parent.parent / "website" / "references",
                Path.home() / "bpeai" / "website" / "references",
            ]
        )
        for rel in (
            ("bpeai", "py", "knowledge", "mixing", "references"),
            ("website", "bpeai", "py", "knowledge", "mixing", "references"),
        ):
            candidates.append(base.parent.parent.joinpath(*rel))
            candidates.append(base.parent.parent.parent.joinpath(*rel))
        candidates.append(
            Path.home()
            / "bpeai"
            / "website"
            / "bpeai"
            / "py"
            / "knowledge"
            / "mixing"
            / "references"
        )

    for cand in candidates:
        if _folder_has_style_templates(cand):
            return cand.resolve()
    return None


def seed_template_references(
    pack_id: str,
    *,
    py_root: Path | None = None,
    template_root: Path | None = None,
) -> List[str]:
    """Copy shared style PPTX/PDF templates into ``<pack>/references/`` when missing.

    Copies every ``*.pptx`` / ``*.pdf`` from :func:`template_references_root`.
    Filenames are preserved and need not follow a fixed naming convention.
    Does not overwrite creator-edited files. Returns relative paths that were copied.
    """
    root = pack_dir(pack_id, py_root=py_root)
    root.mkdir(parents=True, exist_ok=True)
    dest = root / "references"
    dest.mkdir(parents=True, exist_ok=True)

    src_root = Path(template_root) if template_root else template_references_root(py_root)
    if src_root is None or not src_root.is_dir():
        return []

    copied: List[str] = []
    for pattern in ("*.pptx", "*.pdf"):
        for src in sorted(src_root.glob(pattern)):
            target = dest / src.name
            if target.is_file():
                continue
            shutil.copy2(src, target)
            copied.append(f"references/{src.name}")

    # Register PPTX decks in pptx_outline.yaml when present.
    outline_path = root / "pptx_outline.yaml"
    if outline_path.is_file() and copied:
        try:
            raw = yaml.safe_load(outline_path.read_text(encoding="utf-8")) or {}
            if isinstance(raw, dict):
                decks = raw.get("reference_decks")
                if not isinstance(decks, list):
                    decks = []
                existing = {str(x).replace("\\", "/").lower() for x in decks}
                changed = False
                for rel in copied:
                    if rel.lower().endswith(".pptx") and rel.lower() not in existing:
                        decks.append(rel)
                        changed = True
                if changed:
                    raw["reference_decks"] = decks
                    write_pack_file(
                        pack_id,
                        "pptx_outline.yaml",
                        raw,
                        py_root=py_root,
                        draft=True,
                        overwrite=True,
                    )
        except Exception:
            pass
    return copied


def align_pack_meta_with_scenarios(
    pack_id: str,
    *,
    py_root: Path | None = None,
) -> bool:
    """Ensure pack.yaml default_scenario / aliases point at real DIR scenarios."""
    root = pack_dir(pack_id, py_root=py_root)
    pack_path = root / "pack.yaml"
    dir_path = root / "dir_requirements.yaml"
    if not pack_path.is_file() or not dir_path.is_file():
        return False
    meta = yaml.safe_load(pack_path.read_text(encoding="utf-8")) or {}
    dir_req = yaml.safe_load(dir_path.read_text(encoding="utf-8")) or {}
    if not isinstance(meta, Mapping) or not isinstance(dir_req, Mapping):
        return False
    scenario_ids = scenario_ids_from_dir_req(dir_req)
    if not scenario_ids:
        return False
    # Preserve YAML order (first dir_menus scenario is the preferred default).
    scenario_set = set(scenario_ids)
    changed = False
    meta_out = dict(meta)
    default = str(meta_out.get("default_scenario") or "")
    if default not in scenario_set:
        meta_out["default_scenario"] = scenario_ids[0]
        changed = True
    aliases = meta_out.get("scenario_aliases")
    if isinstance(aliases, Mapping):
        kept = {str(k): v for k, v in aliases.items() if str(k) in scenario_set}
        if kept != dict(aliases):
            meta_out["scenario_aliases"] = kept
            changed = True
    if not isinstance(meta_out.get("scenario_aliases"), Mapping) or not meta_out.get(
        "scenario_aliases"
    ):
        primary = str(meta_out.get("default_scenario") or scenario_ids[0])
        meta_out["scenario_aliases"] = {
            primary: [
                "vent filter",
                "tank vent",
                "hold tank",
                "buffer",
                "bioreactor vent",
                "sterile vent",
            ]
        }
        changed = True
    if not changed:
        return False
    write_pack_file(
        pack_id, "pack.yaml", meta_out, py_root=py_root, draft=True, overwrite=True
    )
    return True


def ensure_creator_pack_assets(
    pack_id: str,
    *,
    py_root: Path | None = None,
    equipment_system: str = "",
) -> Tuple[List[str], List[str]]:
    """Repair draft YAML shapes and seed template references.

    Returns ``(repaired_files, seeded_reference_paths)``.
    """
    repaired = repair_existing_pack_components(
        pack_id, py_root=py_root, equipment_system=equipment_system
    )
    if align_pack_meta_with_scenarios(pack_id, py_root=py_root):
        if "pack.yaml" not in repaired:
            repaired.append("pack.yaml")
    seeded = seed_template_references(pack_id, py_root=py_root)
    return repaired, seeded
