from __future__ import annotations

"""Detect / write knowledge-pack YAML components (draft-for-approval).

Agents call LLM to fill missing files; this module handles filesystem inventory
and safe YAML writes with an approval banner.
"""

from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import yaml

from .pack_loader import PACK_FILES, knowledge_root

# Core files required by load_knowledge_pack; outlines are strongly recommended.
OPTIONAL_PACK_FILES = (
    "report_outline.yaml",
    "pptx_outline.yaml",
    "README.md",
)

ALL_BOOTSTRAP_FILES = PACK_FILES + OPTIONAL_PACK_FILES

DRAFT_BANNER = (
    "# DRAFT — initial version pending SME / platform approval.\n"
    "# Do not treat as production-validated content until approved.\n"
)


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
        body = yaml.safe_dump(
            dict(content),
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=100,
        )
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
            "Mapping with pack_id, equipment_system, version, label, description, "
            "industries (list), default_scenario, scenario_aliases (scenario→list of "
            "alias strings), taxonomy_preparation_ids (list), prompt_hooks "
            "(system_role, emphasize list)."
        ),
        "dir_requirements.yaml": (
            "Mapping with scenarios: {scenario_id: {label, common_codes: "
            "[{code, caption}], requirements: [{index, label, options: "
            "[{index, text}]}]}}. DIR code = hyphen-separated 1-based option indexes."
        ),
        "equipment_options.yaml": (
            "Mapping with options: [{id, name, tags, typical_fit, manufacturers}], "
            "do_not_specify_defaults (list), manufacturers_examples (list)."
        ),
        "validation_rules.yaml": (
            "Mapping with dir_code, application, equipment_option_name, selected_model, "
            "fit_enum (allowed list), equipment_system_field.must_equal, repair."
        ),
        "prompt_fragments.yaml": (
            "Mapping with fragments: {role, scope, evaluation_goals, application_default, "
            "workflow, output_style, depth_requirements, response_outline, exclusions_rule}."
        ),
        "report_outline.yaml": (
            "Mapping with required_headings (list of section titles), sections "
            "([{id, heading, description}]), min option count fields as appropriate."
        ),
        "pptx_outline.yaml": (
            "Mapping with slide_count (7), title_prefix, slides ([{index, id, title, ...}]), "
            "style (fonts/colors), reference_decks (list), notes."
        ),
        "README.md": (
            "Markdown describing the pack purpose, draft/approval status, and how to "
            "edit YAML / replace reference PPTX."
        ),
    }
