from __future__ import annotations

"""Equipment sizing template agent (DIR → size capacity/connections/envelope).

Creator checklist after copying this folder to ``py/apps/equipment_sizing/<your_id>/``:
  1. Rename this class and set ``app_id`` to match folder / manifest ``id``.
  2. Set ``creator_display_name`` (hub attribution).
  3. Set ``knowledge_pack_id`` to the **same** ``app_id`` (1:1 private pack).
     ``equipment_system`` is taxonomy (mixing, filtration, …), not the pack name.
     If the pack is missing locally, the first ``local_chat`` run LLM-bootstraps
     a draft under ``py/knowledge/<app_id>/`` using the creator’s ``.env`` keys
     (not Cursor), including ``references/content/methods.md``, ``assumptions.md``,
     and ``basis.csv``. SME edits in that folder are not overwritten.
  4. Update ``manifest.json`` (slug, label, equipment_system, knowledge_pack = app id).
  5. Local test: ``python py/tools/local_chat.py --app <your_id>``.
     First line: system name and application, e.g. ``CIP return pump, biopharmaceutical``.
  6. SME AI dials: ``prompt_fragments.yaml`` (fragments + calls) and
     ``search_queries.yaml``. Leave JSON schema contracts in this file alone
     unless changing the deliverable (see ``docs/EI_AI_HANDSHAKES.md``).
  7. Review any ``draft_pending_sme_approval`` pack files before production use.
  8. Optional Python helpers: ``creator_tools.py`` (see ``EXTENSIONS.md``).
  9. Prefer Cursor Agent → "Create my EI app" over hand-editing this checklist.

HANDSHAKE: comments tagged ``HANDSHAKE:`` mark links the generic web UI already
understands (phases, ``status()`` → SSE, DIR / evaluation payloads). Do not invent
new SSE events or UI chrome — creators do not edit hub/portal React.
See ``docs/EI_CREATOR_EXTENSIONS.md`` and ``docs/EI_HANDSHAKE.md``.

Local artifacts (gitignored ``./artifacts/``): markdown + Word + Excel; optional PPTX.
Portal hub stores ``datasheet_markdown`` as S3 ``.md`` only (no PDF/PPTX upload).
"""

# Allow `python agent.py` from this folder as well as package imports.
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    _py_root = Path(__file__).resolve().parents[3]
    _py_root_str = str(_py_root)
    if _py_root_str not in sys.path:
        sys.path.insert(0, _py_root_str)
    _sdk_src = _py_root / "libs" / "bpeai_creator_sdk" / "src"
    if str(_sdk_src) not in sys.path:
        sys.path.insert(0, str(_sdk_src))
    __package__ = "apps._templates.equipment_sizing"

import json
import re
from typing import Any, Dict, List

from pydantic import ValidationError

from bpeai_creator_sdk import CreatorAppBase, coerce_string_list_items, validate_output
from bpeai_creator_sdk.output import apply_user_identity
from bpeai_creator_sdk.artifacts import (
    attach_sizing_artifact_name,
    attach_title_hero_image,
    build_evaluation_pptx,
    build_sizing_docx,
    build_sizing_xlsx,
    build_slide_pack_from_evaluation,
    sizing_artifact_stem,
)
from bpeai_creator_sdk.local_run import repo_py_root
from bpeai_creator_sdk.sme import (
    CONTENT_FOLDER_PROMPT,
    DIR_GENERATE_TYPED_HOST_RULES,
    DirMenu,
    KnowledgePack,
    align_pack_to_app,
    append_dir_menu,
    build_content_index,
    check_application,
    check_equipment_option_names,
    component_schema_hints,
    creator_content_prompt_block,
    dir_generate_identity_prompt,
    ensure_creator_pack_assets,
    list_missing_pack_files,
    load_knowledge_pack,
    pack_dir,
    match_dir_menu,
    missing_report_headings,
    normalize_generated_menu,
    optional_bootstrap_files,
    pack_bootstrap_authoring_rules,
    prepare_bootstrapped_component,
    sizing_content_authoring_contract,
    python_dir_alignments,
    resolve_dir_menu,
    resolve_industry,
    resolve_scenario_id,
    resolve_variant_hint,
    resolve_variant_id,
    scenario_id_from_system_name,
    stamp_draft_meta,
    structure_example_snippet,
    extract_sizing_content_texts,
    is_sizing_content_bootstrap_file,
    thin_report_sections,
    validate_dir_code,
    write_pack_file,
    apply_dir_route_decision,
    catalog_summaries,
    unknown_dir_guidance,
)
from bpeai_creator_sdk.sme.dir_catalog import catalog_row_to_dir_menu
from bpeai_creator_sdk.tools import enrich_search_hits_with_excerpts, format_search_context

from . import creator_tools

_DIR_TOPIC_MATCHERS = (
    ("capacity", re.compile(r"\b(volume|capacity|scale|batch size|working volume|liter|litre)\b", re.I)),
    ("application", re.compile(r"\b(application|industry|product|modality|cell culture)\b", re.I)),
    ("materials", re.compile(r"\b(material|moc|316|stainless|single-use|polymeric)\b", re.I)),
    ("selected_model", re.compile(r"\b(agitator|impeller|technology|model|mixer type|entry)\b", re.I)),
    ("design_basis", re.compile(r"\b(duty|basis|mixing objective|suspension|blend)\b", re.I)),
    ("utilities", re.compile(r"\b(utilit|cip|sip|jacket|power)\b", re.I)),
    ("dimensions", re.compile(r"\b(dimension|envelope|height|diameter)\b", re.I)),
    ("connection_sizes", re.compile(r"\b(connection|nozzle|inlet|outlet|port size)\b", re.I)),
)


def _basis_parameter_ids(basis: Any) -> set[str]:
    if not isinstance(basis, dict):
        return set()
    params = basis.get("parameters") if isinstance(basis.get("parameters"), list) else []
    return {
        str(item.get("id") or "")
        for item in params
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }


def requirement_overlaps_inherited(label: str, basis: Any) -> bool:
    ids = _basis_parameter_ids(basis)
    if not ids:
        return False
    text = str(label or "")
    return any(pattern.search(text) and topic_id in ids for topic_id, pattern in _DIR_TOPIC_MATCHERS)


def filter_sizing_requirements(requirements: List[Any], basis: Any) -> tuple[List[Any], List[Any]]:
    kept: List[Any] = []
    inherited: List[Any] = []
    for req in requirements or []:
        label = ""
        if isinstance(req, dict):
            label = str(req.get("label") or "")
        else:
            label = str(getattr(req, "label", "") or "")
        if requirement_overlaps_inherited(label, basis):
            inherited.append(req)
        else:
            kept.append(req)
    return kept, inherited


def inherited_parameters_payload(basis: Any) -> List[Dict[str, Any]]:
    if not isinstance(basis, dict):
        return []
    params = basis.get("parameters") if isinstance(basis.get("parameters"), list) else []
    out: List[Dict[str, Any]] = []
    for item in params:
        if not isinstance(item, dict):
            continue
        value = str(item.get("value") or "").strip()
        if not value:
            continue
        out.append(
            {
                "id": str(item.get("id") or ""),
                "label": str(item.get("label") or item.get("id") or ""),
                "value": value,
                "unit": item.get("unit"),
                "source": str(item.get("source") or "evaluation"),
            }
        )
    return out


def inherited_dir_code(basis: Any, prior_eval: Any = None) -> str:
    if isinstance(basis, dict) and str(basis.get("dir_code") or "").strip():
        return str(basis.get("dir_code") or "").strip()
    if isinstance(prior_eval, dict) and str(prior_eval.get("dir_code") or "").strip():
        return str(prior_eval.get("dir_code") or "").strip()
    return ""


def compact_prior_eval(prior: Any, basis: Any = None) -> Dict[str, Any]:
    prior = prior if isinstance(prior, dict) else {}
    basis = basis if isinstance(basis, dict) else {}
    return {
        "equipment_tag": basis.get("equipment_tag") or prior.get("equipment_tag"),
        "equipment_name": basis.get("equipment_item_name") or prior.get("equipment_name"),
        "equipment_system": prior.get("equipment_system"),
        "selected_model": basis.get("selected_model") or prior.get("selected_model"),
        "dir_code": basis.get("dir_code") or prior.get("dir_code"),
        "application": basis.get("application") or prior.get("application"),
        "design_basis": basis.get("design_basis") or prior.get("design_basis"),
        "key_specs": prior.get("key_specs") or basis.get("parameters") or [],
    }


def shared_basis_from_inputs(inputs: Dict[str, Any], prior_eval: Any = None) -> Dict[str, Any] | None:
    basis = inputs.get("shared_basis")
    if isinstance(basis, dict) and (basis.get("parameters") or basis.get("dir_code") or basis.get("selected_model")):
        return basis
    prior = prior_eval if isinstance(prior_eval, dict) else inputs.get("evaluation_result")
    if not isinstance(prior, dict):
        return None
    compact = compact_prior_eval(prior)
    if not any(compact.get(key) for key in ("dir_code", "selected_model", "equipment_tag")):
        return None
    return {
        **compact,
        "parameters": [
            {"id": "selected_model", "label": "Selected technology", "value": compact.get("selected_model") or "", "source": "evaluation"},
            {"id": "application", "label": "Application", "value": compact.get("application") or "", "source": "evaluation"},
            {"id": "design_basis", "label": "Design basis", "value": compact.get("design_basis") or "", "source": "evaluation"},
        ],
    }


# Template-owned JSON schema contracts (deliverable). SME voice/search live in the pack —
# see docs/EI_AI_HANDSHAKES.md and prompt_fragments.yaml → calls / search_queries.yaml.

DIR_GENERATE_SCHEMA_CONTRACT = (
    """Author a Design Input Requirements (DIR) questionnaire for this equipment case.

Return ONLY JSON:
{
  "label": "short menu title",
  "summary": "1-2 sentence design-scope summary",
  "system_examples": ["alias1", "alias2"],
  "equipment_system_variant": "coarse host-class id for THIS typed host",
  "common_codes": [
    {"code": "2-1-3-1-2", "caption": "One-line decode of this starter selection"},
    {"code": "3-1-2-1-1", "caption": "One-line decode of alternate starter"}
  ],
  "requirements": [
    {
      "index": 1,
      "label": "Requirement name",
      "options": [{"index": 1, "text": "..."}, {"index": 2, "text": "..."}]
    }
  ]
}

Rules:
- 5–8 requirements tailored to system_name + application (not generic boilerplate).
- 3–6 engineering options per requirement, then a FINAL option
  "Unknown / TBD — not yet defined" for inputs the project has not decided yet.
  Indexes start at 1. Python will add Unknown/TBD if it is missing.
- common_codes MUST be hyphen-separated numeric starters matching requirement count,
  each with a caption that decodes the selection in one sentence (GPT style).
  Do not use the Unknown/TBD index in common_codes.
- Do NOT use mnemonic tags (SIP, IT, BPE) as common_codes.
- Prefer industrially realistic options for life-science equipment selection.
- Tailor the questionnaire to THIS typed host (system_name / scenario id hint).
- scenario_id and system_examples must describe this host only. Do not copy
  another catalog row's id or examples (do not put CIP Skid on a standalone
  CIP Return Pump menu; do not put Chromatography Skid on a feed-pump menu).
- The questionnaire may be similar to a sibling host, but requirements must
  match THIS duty (supply vs return, feed vs eluate, vessel vs inline mixer).
""".rstrip()
    + "\n"
    + DIR_GENERATE_TYPED_HOST_RULES
    + "\n"
)

DIR_ROUTE_SCHEMA_CONTRACT = """Decide whether this query reuses an existing DIR catalog row or needs a new scenario.

A DIR scenario is the HOST EQUIPMENT SYSTEM whose design inputs are being collected —
not the process (CIP, TFF, chromatography) and not the evaluated technology type
(pump family, agitator impeller, filter media).

Return ONLY JSON:
{
  "action": "reuse" | "create",
  "menu_id": "existing menu_id when action=reuse, else empty",
  "scenario_id": "existing id when reuse; slug of the typed host when create",
  "alignments": ["one-line notes of spelling, host, or sector alignments"]
}

Rules:
- Reuse spelling variants and synonyms of the SAME host in the same official
  sector (CIP System vs CIP Skid; Media Prep vs Media Preparation Vessel).
- Package + component reuses the package row. If the typed name is an existing
  catalog host plus a component noun (pump, agitator, filter, exchanger, valve),
  reuse that host. Do not create a new scenario for a component of a named
  skid/system (CIP Skid Return Pump → CIP Skid; Chromatography Skid Pump →
  Chromatography Skid; TFF Skid Recirculation Pump → TFF Skid).
- Standalone duty items are distinct hosts. If the typed name is a specific
  equipment item NOT prefixed by that package name, and no catalog row lists it,
  CREATE. Two standalone items with different duties get two scenarios even when
  questionnaires would look similar (CIP Supply Pump vs CIP Return Pump;
  chromatography feed pump vs eluate pump).
- Different packages CREATE (CIP Skid vs chromatography_skid; mixing vessel vs
  TFF skid).
- Different official sector CREATE. Do not invent official sector names; Python
  sets industry.
- scenario_id for create must be a slug of the typed system name
  (cip_return_pump), not an existing package id.
- alignments must mention any fuzzy mapping you applied.
"""

PPTX_SLIDE_SCHEMA_CONTRACT = """Convert this sizing JSON into a presentation slide pack.

Return ONLY JSON with this shape:
{
  "system_name": "...",
  "dir_code": "...",
  "slides": [
    {
      "id": "title",
      "title_lines": ["Line1", "Line2"],
      "subtitle": "one sentence evaluation scope",
      "dir_badge": "Validated DIR: x-x-x-x-x-x",
      "summary_badge": "Project-team summary",
      "hero_tags": ["tag1", "tag2", "tag3"],
      "hero_headline": ["line1", "line2", "line3"],
      "hero_image_prompt": "optional cutaway catalog rendering of THIS equipment, no text in the image"
    },
    {
      "id": "design_basis",
      "eyebrow": "Agitator Selection / <system>",
      "heading": "Design basis from DIR code",
      "cards": [{"label": "WORKING VOLUME", "value": "...", "accent": false}],
      "selection_implication": "2 sentences max"
    },
    {
      "id": "objectives",
      "eyebrow": "Agitator Selection / <system>",
      "heading": "Mixing objectives, constraints and failure modes",
      "process_steps": [{"n": 1, "title": "...", "detail": "..."}],
      "failure_modes": ["...", "..."],
      "target_outcome": "one concise outcome sentence"
    },
    {
      "id": "options",
      "eyebrow": "Agitator Selection / <system>",
      "heading": "Realistic mixing-system options",
      "rows": [{"name": "...", "fit": "best|strong|conditional|limited|add-on|special-case", "notes": "..."}],
      "recommendation_line": "Recommendation: ..."
    },
    {
      "id": "matrix",
      "eyebrow": "Agitator Selection / <system>",
      "heading": "Option evaluation matrix",
      "rows": [{"option":"...","technical_fit":"...","gmp":"...","scale_up_risk":"...","cost_schedule":"...","reliability":"...","rank":1}],
      "decision_logic": "one short paragraph"
    },
    {
      "id": "recommendation",
      "eyebrow": "Agitator Selection / <system>",
      "heading": "Recommended basis and alternate option",
      "recommended": "...",
      "recommended_why": ["...", "..."],
      "pros": ["..."],
      "cons": ["..."],
      "alternate": "...",
      "alternate_note": "..."
    },
    {
      "id": "specs",
      "eyebrow": "Agitator Selection / <system>",
      "heading": "Preliminary specification points / vendors / references",
      "specs": ["..."],
      "manufacturers": ["..."],
      "do_not_specify": ["..."],
      "references": ["..."]
    }
  ]
}

Rules:
- Exactly 7 slides in that order/ids.
- Keep text dense but slide-ready (short labels, no walls of text).
- HARD length limits: title_lines ≤ 4 words each; subtitle ≤ 18 words;
  card values ≤ 8 words; process_steps titles ≤ 5 words; process_steps details ≤ 14 words;
  failure_modes ≤ 12 words each; option notes ≤ 12 words;
  recommended_why / cons ≤ 14 words each; decision_logic ≤ 35 words.
- Title slide title_lines MUST be the sizing deliverable name: first line is
  "{system} {sized_item}" (e.g. "Buffer Preparation Vessel Agitator"),
  second line is exactly "Sizing". Never use "Evaluation" in the title.
- Ground every claim in the sizing JSON (capacity, connections, dimensions,
  key_specs, excel_ready_table) and datasheet_markdown.
- Numerical sizing values from that JSON are allowed and expected; do not
  replace validated numbers with TBD placeholders.
- Use project-team summary tone similar to a professional engineering deck.
- Prefer product-line manufacturer hints when present in the sizing JSON.
- Do NOT invent unsupported claims.
- Prefer denser notes on capacity, connections, envelope, and calculation
  slides when the datasheet supports it — but stay within length limits.
"""

EVALUATION_SCHEMA_CONTRACT = """Run a full technology evaluation for the validated DIR code
(equipment system = the knowledge pack's equipment_system).

Return JSON matching equipment_selector_v1 WITH these GPT-parity fields populated:
{
  "schema_version": "equipment_selector_v1",
  "equipment_tag": "Tag matching the system (e.g. MX-101, FL-101)",
  "selected_model": "Recommended basis of design (generic type, not a single SKU)",
  "equipment_system": "<pack equipment_system>",
  "equipment_name": "Descriptive equipment name",
  "equipment_category": "Category matching the pack (e.g. Mixing, Filtration)",
  "key_specs": [{"key": "…", "value": "…"}, …],
  "rationale": "Multi-paragraph why-best including scale-up and GMP/cleanability",
  "creator_attribution": {"display_name": "…", "app_id": "…"},
  "design_basis": "Selection implication narrative from the DIR (multi-sentence)",
  "dir_summary": "One-paragraph restatement of decoded DIR basis",
  "objectives": ["…"],
  "failure_modes": ["at least 3 concrete failure modes for THIS DIR"],
  "recommended_basis": "One-line recommended basis of design",
  "alternate_basis": "One-line alternate / backup",
  "do_not_specify": ["Technology name: reason not primary for this DIR"],
  "preliminary_specs": ["Material: 316L stainless", "Cleaning: CIP/SIP capable"],
  "evaluation_matrix": [
    {"option": "…", "technical_fit": "Best|Strong|…", "gmp": "High|…",
     "scale_up_risk": "Low|…", "cost_schedule": "Best|…", "reliability": "High|…", "rank": 1}
  ],
  "evaluation_options": [
    {
      "name": "Generic technology option name from the SME catalog when possible",
      "fit": "best|strong|conditional|limited|add-on|special-case",
      "industrial_applications": ["…", "…"],
      "pros": ["…", "…", "…"],
      "cons": ["…", "…"],
      "manufacturers": ["Vendor (product-line hint)", "…"]
    }
  ],
  "mixing_options": [],
  "manufacturers": ["…"],
  "datasheet_markdown": "FULL sectioned markdown report (see required headings)",
  "source_basis": ["user_inputs", "knowledge_pack", "serper_search", "industry_references", "creator_references"],
  "handshake_protocol": "ei_handshake_v1"
}
NOTE: evaluation_options is canonical for all equipment systems. mixing_options may
be returned as an empty array or omitted; the platform mirrors evaluation_options
into mixing_options for older clients.
NOTE: key_specs is the only field that uses {"key", "value"} objects.
preliminary_specs, objectives, failure_modes, do_not_specify, and manufacturers
MUST be arrays of strings (e.g. "Material: 316L stainless"), never objects.

Requirements (depth bar — do not produce thin one-line sections):
- Use the decoded DIR; do not invent a different volume/vessel/duty.
- If a decoded DIR row has "unknown": true (user selected Unknown / TBD), assume
  the most likely industrial case for THIS host and duty. In the Design basis
  markdown table write Selected basis as "Unknown / TBD (assumed: …)" and put
  the consequences if that assumption is wrong in the Implication column.
  Repeat those assumptions in design_basis. Do not treat Unknown as a technology.
- Shortlist 3–5 industry-standard options known to be used or sold for THIS
  application and DIR duty. Aim for at least 3. Five is a good maximum. Include
  more only when additional strong candidates exist. Do not pad with exotic,
  poorly fitting, or unproven types. Mark one as recommended basis (fit=best).
- Per option: >=2 industrial_applications, >=3 pros, >=2 cons/watchouts,
  >=2 manufacturers with product-line hints when known, plus why fit changes for THIS DIR.
- Include qualitative scale-up / performance reasoning appropriate to the equipment system.
- Weave industrial search citations into rationale and datasheet_markdown as (title + URL).
- Include alternate_basis, do_not_specify, preliminary_specs, evaluation_matrix.
- do_not_specify is the "Options not recommended as primary basis" table. Each
  string MUST be "Technology name: reason not primary for this DIR" for catalog
  types that are NOT in the 3–5 evaluation_options shortlist (or were considered
  and rejected as primary). Example: "Rotary-lobe pump: Over-specified for
  low-viscosity CIP return with air." The datasheet Markdown table MUST have
  exactly two columns titled Technology | Reason not primary for this DIR —
  never a single column of colon-separated "Technology: reason" rows. Do not
  put procurement caveats (do not specify manufacturer, model, impeller
  diameter, NPSH, setpoints) in this array; those belong in assumptions or
  preliminary_specs notes.
- preliminary_specs must be strings like "Material: 316L", not {key, value} objects.
- Prefer SME catalog option names and manufacturer product-line hints when appropriate.
- datasheet_markdown MUST include ALL required headings supplied in the user message
  (from the knowledge pack report_outline) with SUBSTANTIVE multi-sentence bodies
  (no one-line stubs).
- objectives[] strings MUST be "Objective name: key control" (colon-separated),
  matching PPTX slide 3 process_steps. Example: "Establish return flow: Meet
  qualified circuit velocity or other approved cleaning criterion."
- The "objectives and failure modes" datasheet section MUST include a Markdown
  table with exactly three columns: Step | Objective | Key control. Step is
  1, 2, 3, … (same numbering as the slides). Objective is the short action
  name; Key control is how it is achieved. Failure modes are a sentence AFTER
  the table, not extra table rows. Do not put DIR basis, exclusions,
  constraints, or failure-mode notes in this table.
"""


def _suggest_tag(system_name: str, equipment_system: str) -> str:
    words = re.findall(r"[A-Za-z]+", system_name.upper())
    if words:
        prefix = "".join(w[0] for w in words[:2]) or "EQ"
        return f"{prefix}-101"
    prefixes = {
        "mixing": "MX",
        "heat_transfer": "HX",
        "filtration": "FL",
        "chromatography": "CH",
        "fluid_transfer": "FT",
        "cell_culture": "BR",
    }
    return f"{prefixes.get(equipment_system, 'EQ')}-101"


def _option_catalog_block(pack: KnowledgePack) -> str:
    return pack.option_catalog_prompt_block()


def _sizing_artifact_basename(result: Dict[str, Any]) -> str:
    return sizing_artifact_stem(result) or "Vessel Sizing"


def _write_markdown_artifact(result: Dict[str, Any], *, py_root: Path) -> Path | None:  # noqa: ARG001
    md = (result.get("datasheet_markdown") or "").strip()
    if not md:
        return None
    target = Path.cwd() / "artifacts" / f"{_sizing_artifact_basename(result)}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(md, encoding="utf-8")
    return target


def _write_docx_artifact(result: Dict[str, Any]) -> Path | None:
    md = (result.get("datasheet_markdown") or "").strip()
    if not md and not result.get("selected_model") and not result.get("key_specs"):
        return None
    target = Path.cwd() / "artifacts" / f"{_sizing_artifact_basename(result)}.docx"
    return build_sizing_docx(result, output_path=target)


def _write_xlsx_artifact(result: Dict[str, Any]) -> Path | None:
    if not (
        result.get("excel_ready_table")
        or result.get("key_specs")
        or result.get("datasheet_markdown")
        or result.get("capacity")
    ):
        return None
    target = Path.cwd() / "artifacts" / f"{_sizing_artifact_basename(result)}.xlsx"
    return build_sizing_xlsx(result, output_path=target)


def _attach_sizing_file_artifacts(agent: Any, result: Dict[str, Any], *, py_root: Path) -> Dict[str, Any]:
    md_path = _write_markdown_artifact(result, py_root=py_root)
    artifacts = dict(result.get("artifacts") or {})
    if md_path:
        artifacts["markdown_path"] = str(md_path)
    try:
        agent.status("Writing sizing Word report…")
        docx_path = _write_docx_artifact(result)
        if docx_path:
            artifacts["docx_path"] = str(docx_path.resolve())
    except Exception as exc:
        agent.status(f"DOCX export skipped ({exc})")
    try:
        agent.status("Writing sizing Excel workbook…")
        xlsx_path = _write_xlsx_artifact(result)
        if xlsx_path:
            artifacts["xlsx_path"] = str(xlsx_path.resolve())
    except Exception as exc:
        agent.status(f"Excel export skipped ({exc})")
    result["artifacts"] = artifacts
    result["pptx_prompt"] = "Would you like a presentation-ready PPTX file? Reply pptx or y."
    return result


class EquipmentSizingAgent(CreatorAppBase):
    """Pack-backed DIR → size template (capacity, connections, envelope).

    After copy: rename class, ``app_id``, ``knowledge_pack_id`` (same as ``app_id``),
    ``creator_display_name``.
    Missing packs / YAML components are LLM-bootstrapped as draft-for-approval.
    Optional helpers: ``creator_tools.py`` (sizing_report merge / fallback markdown).
    """

    # HANDSHAKE: manifest.id / python_entrypoint / hub routing must match these ids.
    app_id = "equipment_sizing"
    knowledge_pack_id = "equipment_sizing"
    template_family = "equipment_sizing"
    # Hint for pack bootstrap when the pack folder does not exist yet.
    equipment_system = "mixing"
    creator_display_name = "Your Name"

    def _persist_dir_menu_to_platform(self, pack: KnowledgePack, row: Dict[str, Any]) -> None:
        """POST generated DIR menu into the creator's private pack (web runtime)."""
        import json
        import os
        import urllib.error
        import urllib.request

        # Prefer DB slug from payload meta; fall back to pack_id
        pack_key = str(
            pack.meta.get("db_slug") or pack.meta.get("pack_id") or pack.pack_id or ""
        ).strip()
        if not pack_key:
            return
        base = (
            os.environ.get("BPEAI_INTERNAL_BASE_URL")
            or os.environ.get("NEXT_INTERNAL_BASE_URL")
            or "http://web:3000"
        ).rstrip("/")
        # Token optional: Next internal route allows Docker-internal calls when unset.
        token = (
            os.environ.get("INTERNAL_API_TOKEN")
            or os.environ.get("CREATOR_INTERNAL_TOKEN")
            or os.environ.get("VENDOR_API_INTERNAL_TOKEN")
            or ""
        )
        url = f"{base}/api/internal/knowledge-packs/{pack_key}/dir-menus"
        body = json.dumps({"menu": row}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if token:
            headers["x-internal-token"] = token
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                resp.read()
            self.status("Saved generated DIR menu to knowledge pack")
        except urllib.error.HTTPError as exc:
            self.status(f"DIR catalog DB persist failed (HTTP {exc.code})")
        except Exception as exc:
            self.status(f"DIR catalog DB persist failed ({exc})")

    def _creator_content_block(self, pack: KnowledgePack, *query_parts: Any) -> str:
        """Retrieve indexed creator PDFs/docs as a prompt supplement (does not replace Serper)."""
        return creator_content_prompt_block(getattr(pack, "content_index", None), query_parts)

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # HANDSHAKE: UI / local_chat send phase, system_name, application, dir_code,
        # deliverable, evaluation_result. Platform may inject knowledge_pack_payload
        # and LLM overrides — never invent new required UI input keys here.
        system_name = str(
            inputs.get("equipment_system_name") or inputs.get("system_name") or "Process Vessel"
        ).strip()
        self._identity_inputs = inputs
        application_raw = str(inputs.get("application") or "biopharmaceutical").strip()
        industry_raw = str(inputs.get("industry") or "").strip()
        variant_raw = str(inputs.get("equipment_system_variant") or "").strip()
        scenario_raw = str(inputs.get("scenario_id") or "").strip()
        dir_code = str(inputs.get("dir_code") or "").strip()
        sizing_inputs = inputs.get("sizing_inputs")
        prior_eval = inputs.get("evaluation_result")
        if isinstance(prior_eval, dict):
            if not str(inputs.get("system_name") or "").strip():
                system_name = str(prior_eval.get("equipment_name") or prior_eval.get("system_name") or system_name).strip()
            if not str(inputs.get("application") or "").strip() and prior_eval.get("application"):
                application_raw = str(prior_eval.get("application")).strip()
        # HANDSHAKE: phase dispatch — dir | evaluate | pptx | generate_dir
        phase = str(inputs.get("phase") or "").strip().lower()
        deliverable = str(inputs.get("deliverable") or "evaluation").strip().lower()

        pack_id = str(
            inputs.get("knowledge_pack")
            or self.knowledge_pack_id
            or getattr(self, "app_id", "")
            or ""
        ).strip()
        py_root = repo_py_root()
        bootstrap_notes: List[str] = []
        # HANDSHAKE: knowledge_pack_payload is platform-injected on portal/hub runs.
        pack_payload = inputs.get("knowledge_pack_payload")
        if isinstance(pack_payload, dict):
            pack = load_knowledge_pack(pack_id, py_root=py_root, payload=pack_payload)
        else:
            eq_system = str(
                inputs.get("equipment_system")
                or getattr(self, "equipment_system", "")
                or pack_id
            ).strip()
            pack, bootstrap_notes = self._ensure_knowledge_pack(
                pack_id,
                py_root=py_root,
                equipment_system=eq_system,
                system_name=system_name,
                application=application_raw,
            )

        app_check = check_application(pack, application_raw)
        application = app_check.normalized or application_raw
        combined_warning = " | ".join(
            w for w in [app_check.warning, *bootstrap_notes] if w
        )

        force_generate = phase in {"generate_dir"} or bool(inputs.get("force_generate_dir"))
        want_pptx = deliverable == "pptx" or phase == "pptx"
        if want_pptx:
            prior = inputs.get("evaluation_result")
            if isinstance(prior, dict) and (
                prior.get("schema_version") == "equipment_sizing_v1"
                or prior.get("selected_model")
                or prior.get("equipment_tag")
                or prior.get("datasheet_markdown")
            ):
                result = self._attach_pptx(pack, prior, py_root=py_root)
                result.setdefault("template_family", getattr(self, "template_family", "equipment_sizing"))
                return result
        shared_basis = shared_basis_from_inputs(inputs, prior_eval)
        inherited_code = inherited_dir_code(shared_basis, prior_eval)
        reuse_eval_dir = (
            bool(inherited_code)
            and not force_generate
            and phase not in {"generate_dir", "pptx"}
            and not want_pptx
        )
        if reuse_eval_dir:
            if not dir_code:
                dir_code = inherited_code
            if phase in {"dir", "dir_requirements"}:
                return self._inherited_eval_dir_ready(
                    system_name,
                    application,
                    shared_basis,
                    warning=combined_warning,
                )
            result = self._size(
                pack,
                None,
                system_name,
                application,
                dir_code,
                sizing_inputs=sizing_inputs,
                prior_eval=prior_eval if isinstance(prior_eval, dict) else None,
                app_warning=combined_warning,
                equipment_tag=str(inputs.get("equipment_tag") or "").strip(),
                reuse_inherited_dir=True,
            )
            if result.get("phase") == "evaluation":
                result = _attach_sizing_file_artifacts(self, result, py_root=py_root)
            result.setdefault("template_family", getattr(self, "template_family", "equipment_sizing"))
            return result

        menu, gen_notes = self._resolve_or_generate_dir_menu(
            pack,
            system_name=system_name,
            application=application,
            scenario_id=scenario_raw or None,
            equipment_system_variant=variant_raw or None,
            industry=industry_raw or None,
            force_generate=force_generate,
        )
        if gen_notes:
            combined_warning = " | ".join(
                w for w in [combined_warning, *gen_notes] if w
            )

        if phase == "generate_dir" and not dir_code:
            return {
                "phase": "generate_dir",
                "message": (
                    f"DIR menu ready ({menu.lifecycle}). "
                    "Reply with a hyphen-separated DIR code to evaluate."
                ),
                "knowledge_pack": pack.pack_id,
                "scenario_id": menu.scenario_id,
                "menu_id": getattr(menu, "menu_id", "") or "",
                "equipment_system_variant": menu.equipment_system_variant,
                "industry": menu.industry,
                "dir_menu_label": menu.label,
                "dir_lifecycle": menu.lifecycle,
                "requirements": menu.requirements,
                "common_codes": [
                    e["code"] for e in pack._normalize_common_codes(menu.common_codes)
                ],
                "common_code_details": pack._normalize_common_codes(menu.common_codes),
                "template_requirements": menu.requirements,
            }

        # PPTX from a prior evaluation payload
        if deliverable == "pptx" or phase == "pptx":
            prior = inputs.get("evaluation_result")
            if isinstance(prior, dict) and (
                prior.get("schema_version") == "equipment_sizing_v1"
                or prior.get("selected_model")
                or prior.get("equipment_tag")
            ):
                return self._attach_pptx(pack, prior, py_root=py_root)
            if dir_code:
                evaluated = self._size(
                    pack,
                    menu,
                    system_name,
                    application,
                    dir_code,
                    sizing_inputs=sizing_inputs,
                    prior_eval=prior_eval if isinstance(prior_eval, dict) else None,
                    app_warning=combined_warning,
                    equipment_tag=str(inputs.get("equipment_tag") or "").strip(),
                )
                if evaluated.get("phase") == "evaluation":
                    return self._attach_pptx(pack, evaluated, py_root=py_root)
                return evaluated
            return {
                "phase": "pptx_error",
                "message": "Provide dir_code or evaluation_result to generate a PPTX.",
            }

        if phase in {"dir", "dir_requirements"} or not dir_code:
            # HANDSHAKE: return → SSE event "dir_requirements" (questionnaire UI).
            return self._dir_requirements(
                pack,
                menu,
                system_name,
                application,
                warning=combined_warning,
                shared_basis=shared_basis_from_inputs(inputs, prior_eval),
            )

        # HANDSHAKE: size path → SSE "evaluation" / "result" + equipment_sizing_v1.
        result = self._size(
            pack,
            menu,
            system_name,
            application,
            dir_code,
            sizing_inputs=sizing_inputs,
            prior_eval=prior_eval if isinstance(prior_eval, dict) else None,
            app_warning=combined_warning,
            equipment_tag=str(inputs.get("equipment_tag") or "").strip(),
        )
        if result.get("phase") == "evaluation":
            result = _attach_sizing_file_artifacts(self, result, py_root=py_root)
        return result

    def _ensure_knowledge_pack(
        self,
        pack_id: str,
        *,
        py_root: Path,
        equipment_system: str = "",
        system_name: str = "",
        application: str = "",
    ) -> tuple[KnowledgePack, List[str]]:
        """Load pack; LLM-create any missing YAML/README as draft-for-approval.

        Creator-owned pack content is drafted locally (not copied from website packs).
        Style PPTX/PDF shells seed into ``references/style/``. Optional SME documents
        go in ``references/content/`` and are indexed as supplemental LLM context.
        """
        notes: List[str] = []
        app_id = str(getattr(self, "app_id", "") or pack_id).strip() or pack_id
        family = str(getattr(self, "template_family", "") or "").strip()
        align_id = f"{family}/{app_id}" if family and family not in app_id else app_id
        aligned = align_pack_to_app(align_id, py_root=py_root, pack_id=pack_id)
        pack_id = aligned.pack_id
        notes.extend(aligned.notes)
        if aligned.collision:
            self.status(
                f"Knowledge pack name collision for '{app_id}' — using pack '{pack_id}'."
            )

        eq = (equipment_system or getattr(self, "equipment_system", "") or pack_id).strip() or pack_id
        repaired, seeded = ensure_creator_pack_assets(
            pack_id, py_root=py_root, equipment_system=eq
        )
        if repaired:
            notes.append(
                f"Repaired draft pack structure for '{pack_id}': {', '.join(repaired)}."
            )
            self.status(f"Repaired draft pack files for '{pack_id}': {', '.join(repaired)}")
        if seeded:
            notes.append(
                f"Seeded style templates into '{pack_id}/references/style' "
                f"({', '.join(seeded)}). Editable in this workspace."
            )
            self.status(
                f"Seeded style templates for '{pack_id}': {', '.join(seeded)}"
            )

        missing = list_missing_pack_files(
            pack_id,
            py_root=py_root,
            include_optional=True,
            optional=optional_bootstrap_files(template_family=family),
        )
        created: List[str] = []
        if missing:
            self.status(
                f"Knowledge pack '{pack_id}' incomplete ({len(missing)} file(s) missing) — "
                "bootstrapping initial draft components…"
            )
            yaml_missing = [name for name in missing if not is_sizing_content_bootstrap_file(name)]
            content_missing = [name for name in missing if is_sizing_content_bootstrap_file(name)]
            for filename in yaml_missing:
                try:
                    self._bootstrap_pack_component(
                        pack_id,
                        filename,
                        equipment_system=eq,
                        py_root=py_root,
                        system_name=system_name,
                        application=application,
                    )
                    created.append(filename)
                except Exception as exc:
                    notes.append(f"Failed to bootstrap {filename}: {exc}")
                    self.status(f"Bootstrap failed for {filename}: {exc}")
            if content_missing:
                try:
                    created.extend(
                        self._bootstrap_sizing_content(
                            pack_id,
                            content_missing,
                            equipment_system=eq,
                            py_root=py_root,
                            system_name=system_name,
                            application=application,
                        )
                    )
                except Exception as exc:
                    notes.append(f"Failed to bootstrap sizing methods content: {exc}")
                    self.status(f"Bootstrap failed for sizing methods content: {exc}")

            still_missing_core = list_missing_pack_files(
                pack_id, py_root=py_root, include_optional=False
            )
            if still_missing_core:
                raise FileNotFoundError(
                    f"Knowledge pack '{pack_id}' still missing required files after "
                    f"bootstrap: {', '.join(still_missing_core)}. "
                    f"Prior errors: {'; '.join(notes) if notes else 'none'}"
                )

            _, seeded_after = ensure_creator_pack_assets(
                pack_id, py_root=py_root, equipment_system=eq
            )
            if seeded_after:
                notes.append(
                    f"Seeded style templates into '{pack_id}/references/style' "
                    f"({', '.join(seeded_after)})."
                )

            if created:
                notes.append(
                    f"Initial draft knowledge pack components written for '{pack_id}' "
                    f"({', '.join(created)}). Subject to SME/platform approval "
                    f"(approval_status=draft_pending_sme_approval)."
                )
                self.status(
                    f"Wrote draft pack files for '{pack_id}': {', '.join(created)} "
                    "(pending approval)."
                )
                hint = CONTENT_FOLDER_PROMPT.format(pack_id=pack_id)
                notes.append(hint)
                self.status(hint)

        index = build_content_index(pack_id, py_root=py_root)
        pack = load_knowledge_pack(pack_id, py_root=py_root)
        pack.content_index = index or pack.content_index
        n_files = len((index or {}).get("files") or [])
        if n_files:
            self.status(
                f"Indexed {n_files} creator content file(s) from "
                f"'{pack_id}/references/content' (supplemental to web search)."
            )
        return pack, notes

    def _bootstrap_pack_component(
        self,
        pack_id: str,
        filename: str,
        *,
        equipment_system: str,
        py_root: Path,
        overwrite: bool = False,
        system_name: str = "",
        application: str = "",
    ) -> Path:
        """Generate one missing pack file via LLM (or a minimal README fallback)."""
        if is_sizing_content_bootstrap_file(filename):
            written = self._bootstrap_sizing_content(
                pack_id,
                [filename],
                equipment_system=equipment_system,
                py_root=py_root,
                system_name=system_name,
                application=application,
                overwrite=overwrite,
            )
            if not written:
                raise ValueError(f"Sizing content bootstrap produced no text for {filename}")
            return pack_dir(pack_id, py_root=py_root) / filename

        if filename == "README.md":
            md = (
                f"# {pack_id} knowledge pack (DRAFT)\n\n"
                f"Initial auto-generated SME pack for **{equipment_system}**.\n\n"
                "Status: `draft_pending_sme_approval` — review YAML and "
                "`references/content/` (methods.md, assumptions.md, basis.csv) "
                "before production use.\n\n"
                "Design: `docs/EI_APP_TEMPLATE_DESIGN.md`.\n"
            )
            return write_pack_file(
                pack_id, filename, md, py_root=py_root, draft=True, overwrite=overwrite
            )

        self.status(f"Drafting {pack_id}/{filename} with LLM…")
        payload = self._generate_pack_component_llm(
            pack_id,
            filename,
            equipment_system=equipment_system,
            py_root=py_root,
            system_name=system_name,
            application=application,
        )
        payload = prepare_bootstrapped_component(
            filename,
            payload,
            pack_id=pack_id,
            equipment_system=equipment_system,
            system_name=system_name,
            application=application,
        )
        if filename == "pack.yaml":
            payload = stamp_draft_meta(
                payload, pack_id=pack_id, equipment_system=equipment_system
            )
        return write_pack_file(
            pack_id,
            filename,
            payload,
            py_root=py_root,
            draft=True,
            overwrite=overwrite,
        )

    def _bootstrap_sizing_content(
        self,
        pack_id: str,
        filenames: List[str],
        *,
        equipment_system: str,
        py_root: Path,
        system_name: str = "",
        application: str = "",
        overwrite: bool = False,
    ) -> List[str]:
        """LLM-draft methods.md / assumptions.md / basis.csv (missing files only)."""
        wanted = [
            name.replace("\\", "/")
            for name in filenames
            if is_sizing_content_bootstrap_file(name)
        ]
        if not wanted:
            return []
        root = pack_dir(pack_id, py_root=py_root)
        missing = [
            name
            for name in wanted
            if overwrite or not (root / name).is_file()
        ]
        if not missing:
            return []
        self.status("Drafting sizing methods, assumptions, and calculation basis…")
        raw = self._generate_sizing_content_llm(
            pack_id,
            equipment_system=equipment_system,
            py_root=py_root,
            system_name=system_name,
            application=application,
        )
        texts = extract_sizing_content_texts(raw)
        created: List[str] = []
        for filename in missing:
            body = (texts.get(filename) or "").strip()
            if len(body) < 40:
                self.status(f"Sizing content bootstrap skipped thin {filename}")
                continue
            write_pack_file(
                pack_id,
                filename,
                body if body.endswith("\n") else body + "\n",
                py_root=py_root,
                draft=True,
                overwrite=overwrite,
            )
            created.append(filename)
        if created:
            self.status(f"Wrote draft sizing content: {', '.join(created)}")
        return created

    def _generate_sizing_content_llm(
        self,
        pack_id: str,
        *,
        equipment_system: str,
        py_root: Path,
        system_name: str = "",
        application: str = "",
    ) -> Dict[str, Any]:
        """One JSON LLM for draft methods.md, assumptions.md, and basis.csv."""
        # AI_HANDSHAKE: pack_bootstrap — sizing methods/assumptions/basis content.
        sized_item = ""
        try:
            partial = load_knowledge_pack(pack_id, py_root=py_root)
            sized_item = str(getattr(partial, "sized_item", "") or "").strip()
        except Exception:
            pass
        methods_ex = structure_example_snippet(
            "references/content/methods.md",
            py_root=py_root,
            stub_name="mixing_sizing_stub",
        )
        assumptions_ex = structure_example_snippet(
            "references/content/assumptions.md",
            py_root=py_root,
            stub_name="mixing_sizing_stub",
        )
        basis_ex = structure_example_snippet(
            "references/content/basis.csv",
            py_root=py_root,
            stub_name="mixing_sizing_stub",
        )
        system = (
            "You are a senior life-science equipment SME authoring an INITIAL DRAFT "
            "methods pack for a BPEAI equipment_sizing knowledge pack. Return ONLY JSON. "
            "Adapt methods to the sized item and host. Prefer textbook correlations with "
            "named symbols. Do not invent SKUs or guaranteed process performance."
        )
        user = (
            f"Pack `{pack_id}` (equipment_system=`{equipment_system}`), "
            f"app `{getattr(self, 'app_id', pack_id)}`.\n"
            f"Typed host: {system_name or '(unspecified)'}\n"
            f"Application/sector: {application or '(unspecified)'}\n"
            f"sized_item: {sized_item or '(infer from pack_id / host)'}\n\n"
            f"{sizing_content_authoring_contract()}\n\n"
            "Reference shape from mixing_sizing_stub (adapt domain; do not copy "
            "mixing-only formulas into unrelated equipment):\n"
            f"--- methods.md ---\n{methods_ex[:3500]}\n"
            f"--- assumptions.md ---\n{assumptions_ex[:2500]}\n"
            f"--- basis.csv ---\n{basis_ex[:2500]}\n"
        )
        raw = self.call_openai_json(system=system, user=user)
        if not isinstance(raw, dict):
            raise TypeError("LLM sizing content bootstrap was not a JSON object")
        if set(raw.keys()) == {"content"} and isinstance(raw.get("content"), dict):
            return raw["content"]
        return raw

    def _generate_pack_component_llm(
        self,
        pack_id: str,
        filename: str,
        *,
        equipment_system: str,
        py_root: Path,
        system_name: str = "",
        application: str = "",
    ) -> Dict[str, Any]:
        """LLM function: return JSON/YAML-mappable content for one pack file."""
        # AI_HANDSHAKE: pack_bootstrap — authoring-time draft of missing pack YAML.
        hints = component_schema_hints(template_family="equipment_sizing")
        schema_hint = hints.get(filename, "Valid YAML mapping for this pack component.")
        reference = structure_example_snippet(
            filename, py_root=py_root, stub_name="mixing_sizing_stub"
        )
        app_label = getattr(self, "app_id", "equipment_sizing")
        default_system = (
            "You are a senior life-science process / equipment SME authoring an "
            "initial draft knowledge pack for BPEAI equipment_sizing apps. "
            "Return ONLY a JSON object that will be serialized to YAML — no markdown "
            "fences, no commentary. Content must be industrially plausible but clearly "
            "an initial draft for later SME approval. Prefer generic technology names "
            "and real manufacturer families when known; do not invent SKUs. "
            "Never nest other filenames as top-level keys."
        )
        system = default_system
        # Prefer SME override from an already-written prompt_fragments.yaml if present.
        try:
            partial = load_knowledge_pack(pack_id, py_root=py_root)
            system = partial.call_fragment("pack_bootstrap", "system", default=default_system) or default_system
        except Exception:
            frag_path = pack_dir(pack_id, py_root=py_root) / "prompt_fragments.yaml"
            if frag_path.is_file():
                try:
                    import yaml as _yaml

                    raw_pf = _yaml.safe_load(frag_path.read_text(encoding="utf-8")) or {}
                    calls = (raw_pf.get("calls") or {}) if isinstance(raw_pf, dict) else {}
                    boot = calls.get("pack_bootstrap") if isinstance(calls, dict) else {}
                    if isinstance(boot, dict) and str(boot.get("system") or "").strip():
                        system = str(boot["system"]).strip()
                except Exception:
                    pass
        user = (
            f"Create the knowledge-pack file `{filename}` for pack_id=`{pack_id}` "
            f"(equipment_system=`{equipment_system}`), used by app `{app_label}`.\n\n"
            f"Structural requirements:\n{schema_hint}\n\n"
            f"Reference shape from creator-apps `_examples/mixing_sizing_stub` "
            f"(adapt domain content; do not copy mixing-specific options; "
            f"do not copy website/platform pack content):\n"
            f"{reference}\n\n"
            f"{pack_bootstrap_authoring_rules(system_name=system_name, application=application, template_family='equipment_sizing')}"
        )
        raw = self.call_openai_json(system=system, user=user)
        if not isinstance(raw, dict):
            raise TypeError(f"LLM pack component for {filename} was not a JSON object")
        # Allow {"content": {...}} wrappers
        if set(raw.keys()) == {"content"} and isinstance(raw.get("content"), dict):
            return raw["content"]
        if filename.endswith(".yaml") and "fragments" not in raw and filename.startswith(
            "prompt_"
        ):
            return {"fragments": raw}
        return raw

    def _route_dir_menu_llm(
        self,
        pack: KnowledgePack,
        *,
        system_name: str,
        application: str,
        canonical_industry: str,
    ) -> tuple[DirMenu | None, List[str]]:
        summaries = catalog_summaries(pack)
        if not summaries:
            return None, []
        # AI_HANDSHAKE: dir_route — reuse vs create host scenario after Python catalog miss.
        self.status("Checking existing DIR scenarios for a match…")
        sme_route = pack.call_fragment("dir_route", "instructions")
        user = (
            f"Typed host: {system_name}\n"
            f"Typed application/sector: {application}\n"
            f"Official sector: {canonical_industry}\n\n"
            f"Existing DIR catalog:\n{json.dumps(summaries, ensure_ascii=False)[:20000]}\n\n"
        )
        if sme_route:
            user += f"{sme_route}\n\n"
        user += DIR_ROUTE_SCHEMA_CONTRACT
        default_system = (
            "You route DIR questionnaires to existing catalog rows or create a new "
            "host scenario. Return ONLY JSON."
        )
        system = pack.call_fragment("dir_route", "system", default=default_system) or default_system
        try:
            raw = self.call_openai_json(system=system, user=user)
        except Exception as exc:
            return None, [f"DIR match router unavailable ({exc})."]
        menu, alignments = apply_dir_route_decision(
            pack, raw if isinstance(raw, dict) else {}, canonical_industry=canonical_industry
        )
        return menu, alignments

    def _resolve_or_generate_dir_menu(
        self,
        pack: KnowledgePack,
        *,
        system_name: str,
        application: str,
        scenario_id: str | None,
        equipment_system_variant: str | None,
        industry: str | None,
        force_generate: bool = False,
    ) -> tuple[DirMenu, List[str]]:
        """Reuse a catalog hit, LLM-route fuzzy cases, or generate a new host menu."""
        notes: List[str] = []
        canonical = resolve_industry(pack, industry=industry, application=application)
        typed_sector = str(industry or application or "").strip()
        if not force_generate:
            hit = match_dir_menu(
                pack,
                system_name=system_name,
                scenario_id=scenario_id,
                equipment_system_variant=equipment_system_variant,
                industry=canonical,
                application=application,
                allow_draft=True,
            )
            if hit is not None:
                notes.extend(
                    python_dir_alignments(
                        typed_sector=typed_sector,
                        canonical_industry=canonical,
                        system_name=system_name,
                        menu=hit,
                    )
                )
                return hit, notes
            if pack.dir_menus:
                routed, route_notes = self._route_dir_menu_llm(
                    pack,
                    system_name=system_name,
                    application=application,
                    canonical_industry=canonical,
                )
                notes.extend(route_notes)
                if routed is not None:
                    notes.extend(
                        python_dir_alignments(
                            typed_sector=typed_sector,
                            canonical_industry=canonical,
                            system_name=system_name,
                            menu=routed,
                        )
                    )
                    return routed, notes
            if not pack.dir_menus:
                legacy = resolve_dir_menu(
                    pack,
                    system_name=system_name,
                    scenario_id=scenario_id,
                    equipment_system_variant=equipment_system_variant,
                    industry=industry,
                    application=application,
                    require_approved=False,
                )
                if (
                    legacy.requirements
                    and legacy.source in {"menu", "scenario_fallback", "dir_catalog"}
                ):
                    return legacy, notes

        create_sid = (scenario_id or "").strip() or scenario_id_from_system_name(system_name)
        try:
            menu = self._generate_and_persist_dir_menu(
                pack,
                system_name=system_name,
                application=application,
                scenario_id=create_sid,
                equipment_system_variant=equipment_system_variant,
                industry=canonical,
            )
            notes.extend(
                python_dir_alignments(
                    typed_sector=typed_sector,
                    canonical_industry=canonical,
                    system_name=system_name,
                    menu=menu,
                    created=True,
                )
            )
            notes.append(
                f"Generated draft DIR menu '{menu.menu_id or menu.scenario_id}' "
                f"(status={menu.lifecycle}) and appended to pack catalog for SME review."
            )
            return menu, notes
        except Exception as exc:
            notes.append(f"DIR generation failed ({exc}).")
            explicit = (scenario_id or "").strip()
            if explicit:
                fallback = resolve_dir_menu(
                    pack,
                    system_name=system_name,
                    scenario_id=explicit,
                    equipment_system_variant=equipment_system_variant,
                    industry=industry,
                    application=application,
                    require_approved=False,
                )
                if fallback.requirements and fallback.scenario_id == explicit:
                    notes.append(f"Fell back to explicit scenario '{explicit}'.")
                    return fallback, notes
            slug = scenario_id_from_system_name(system_name)
            variant = resolve_variant_id(
                pack,
                system_name,
                equipment_system_variant,
                application=application,
            )
            return (
                DirMenu(
                    scenario_id=slug or "unresolved",
                    equipment_system_variant=variant,
                    industry=canonical,
                    label=f"DIR generation failed for {system_name}",
                    lifecycle="pending",
                    requirements=[],
                    common_codes=[],
                    source="unresolved",
                ),
                notes,
            )

    def _generate_and_persist_dir_menu(
        self,
        pack: KnowledgePack,
        *,
        system_name: str,
        application: str,
        scenario_id: str | None,
        equipment_system_variant: str | None,
        industry: str | None,
    ) -> DirMenu:
        sid = (scenario_id or "").strip() or scenario_id_from_system_name(system_name)
        variant_hint = resolve_variant_hint(
            pack,
            system_name,
            equipment_system_variant,
            application=application,
        )
        ind = resolve_industry(pack, industry=industry, application=application)
        identity = dir_generate_identity_prompt(
            system_name=system_name,
            application=application,
            industry=ind,
            equipment_system=pack.equipment_system,
            scenario_id=sid,
            variant_hint=variant_hint,
        )

        # AI_HANDSHAKE: dir_search — Serper before DIR questionnaire generation.
        self.status("Researching design inputs for DIR questionnaire…")
        queries = pack.build_search_queries(
            "dir_generate",
            system_name=system_name,
            application=application,
            equipment_system=pack.equipment_system,
        )
        snippets: List[Dict[str, str]] = []
        for q in queries:
            for hit in self.serper_search(q, num=5):
                snippets.append(hit)
        search_context = format_search_context(snippets, limit=12)
        creator_block = self._creator_content_block(
            pack, system_name, application, pack.equipment_system, sid, variant_hint or ""
        )

        # AI_HANDSHAKE: dir_generate — LLM authors DIR menu JSON.
        self.status("Generating DIR questionnaire…")
        default_dir_system = (
            "You are a senior life-science process/equipment SME authoring DIR "
            "questionnaires for equipment intelligence apps. Return ONLY JSON."
        )
        system = pack.call_fragment("dir_generate", "system", default=default_dir_system) or default_dir_system
        sme_dir_instructions = pack.call_fragment("dir_generate", "instructions")
        user = (
            f"{identity}"
            f"Industrial search context:\n{search_context or '(none)'}\n\n"
        )
        if creator_block:
            user += f"{creator_block}\n\n"
        if sme_dir_instructions:
            user += f"{sme_dir_instructions}\n\n"
        user += DIR_GENERATE_SCHEMA_CONTRACT
        raw = self.call_openai_json(system=system, user=user)
        if not isinstance(raw, dict):
            raise TypeError("DIR generation did not return a JSON object")

        try:
            row = normalize_generated_menu(
                raw,
                system_name=system_name,
                application=application,
                scenario_id=sid,
                variant=variant_hint or "",
                industry=ind,
            )
        except ValueError as exc:
            self.status("Retrying DIR questionnaire with a stricter schema…")
            repair_user = (
                f"{identity}"
                f"Your previous JSON was unusable ({exc}).\n\n"
                f"{DIR_GENERATE_SCHEMA_CONTRACT}\n"
                "Do not wrap the menu in dir_menus or dir_requirements.yaml."
            )
            raw = self.call_openai_json(system=system, user=repair_user)
            if not isinstance(raw, dict):
                raise TypeError("DIR generation retry did not return a JSON object") from exc
            row = normalize_generated_menu(
                raw,
                system_name=system_name,
                application=application,
                scenario_id=sid,
                variant=variant_hint or "",
                industry=ind,
            )
        # Persist: filesystem packs write YAML; DB-hydrated packs POST to internal API.
        try:
            path_s = str(pack.path)
            if pack.path.exists() and not path_s.startswith("<"):
                append_dir_menu(pack, row, write_markdown=True)
            else:
                menus = pack.dir_requirements.setdefault("dir_menus", [])
                if isinstance(menus, list):
                    menus.append(row)
                if path_s.startswith("<db:"):
                    self._persist_dir_menu_to_platform(pack, row)
        except Exception as exc:
            self.status(f"DIR catalog persist skipped ({exc})")
            menus = pack.dir_requirements.setdefault("dir_menus", [])
            if isinstance(menus, list):
                menus.append(row)

        menu = catalog_row_to_dir_menu(row)
        menu.source = "generated"
        return menu

    def _inherited_eval_dir_ready(
        self,
        system_name: str,
        application: str,
        shared_basis: Dict[str, Any] | None,
        *,
        warning: str = "",
    ) -> Dict[str, Any]:
        prior_code = inherited_dir_code(shared_basis)
        params = inherited_parameters_payload(shared_basis)
        out: Dict[str, Any] = {
            "phase": "dir_requirements",
            "system_name": system_name,
            "application": application,
            "requirements": [],
            "inherited_parameters": params,
            "common_codes": [prior_code] if prior_code else [],
            "common_code_details": (
                [{"code": prior_code, "caption": "Approved evaluation DIR"}] if prior_code else []
            ),
            "suggested_correction": prior_code,
            "reused_evaluation_dir": True,
            "template_family": getattr(self, "template_family", "equipment_sizing"),
            "message": (
                f"Using the approved evaluation DIR {prior_code} for {system_name}. "
                "A new DIR menu was not generated. Run sizing to continue. "
                "Additional material-balance or connection inputs will be requested only if needed."
            ),
        }
        if warning:
            out["sme_warnings"] = [warning]
            align_bits = [w.strip() for w in warning.split(" | ") if w.strip()]
            if align_bits:
                out["dir_alignments"] = align_bits
        self.status(f"Reusing approved evaluation DIR {prior_code}")
        return out

    def _dir_requirements(
        self,
        pack: KnowledgePack,
        menu: DirMenu,
        system_name: str,
        application: str,
        *,
        warning: str = "",
        validation_error: str = "",
        suggested_correction: str = "",
        shared_basis: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        self.status(f"Assembling design input requirements for {system_name}…")
        requirements = list(menu.requirements or [])
        inherited_params = inherited_parameters_payload(shared_basis)
        residual, _skipped = filter_sizing_requirements(requirements, shared_basis)
        prior_code = str((shared_basis or {}).get("dir_code") or "").strip()
        try:
            from bpeai_creator_sdk.sme.dir_catalog import ensure_common_codes_for_requirements

            entries = ensure_common_codes_for_requirements(
                menu.common_codes,
                residual or requirements,
                system_name=system_name,
                application=application,
                min_count=3,
                max_count=4,
            )
        except Exception:
            entries = pack._normalize_common_codes(menu.common_codes)
        codes = [e["code"] for e in entries]
        if prior_code and prior_code not in codes:
            codes = [prior_code, *codes]
            entries = [{"code": prior_code, "caption": "Prior evaluation DIR code"}, *entries]
        example = prior_code or (codes[0] if codes else "-".join("1" for _ in (residual or requirements or [1])))
        if residual:
            message = (
                f"For {system_name} — {menu.label} "
                f"({menu.industry} / {menu.equipment_system_variant} / scenario={menu.scenario_id}), "
                f"I’ll assume {application} unless you specify otherwise. "
                "Questions already answered by evaluation are inherited. "
                f"Reply with a hyphen-separated DIR code (e.g. {example})."
            )
        elif inherited_params:
            message = (
                f"Inherited evaluation basis already covers the DIR questions for {system_name}. "
                f"Reply with the prior DIR code {prior_code or example} to continue, "
                "or a new code if you want to change the basis."
            )
        else:
            message = (
                f"For {system_name} — {menu.label} "
                f"({menu.industry} / {menu.equipment_system_variant} / scenario={menu.scenario_id}), "
                f"I’ll assume {application} unless you specify otherwise. "
                f"Reply with a hyphen-separated DIR code (e.g. {example})."
            )
        # HANDSHAKE: phase=dir_requirements payload fields the generic UI renders.
        out: Dict[str, Any] = {
            "phase": "dir_requirements",
            "system_name": system_name,
            "application": application,
            "knowledge_pack": pack.pack_id,
            "scenario_id": menu.scenario_id,
            "menu_id": getattr(menu, "menu_id", "") or "",
            "equipment_system_variant": menu.equipment_system_variant,
            "industry": menu.industry,
            "dir_menu_label": menu.label,
            "dir_lifecycle": menu.lifecycle,
            "requirements": residual,
            "inherited_parameters": inherited_params,
            "common_codes": codes,
            "common_code_details": entries,
            "message": message,
            "dir_alignments": [],
        }
        if warning:
            out["sme_warnings"] = [warning]
            align_bits = [w.strip() for w in warning.split(" | ") if w.strip()]
            if align_bits:
                out["dir_alignments"] = align_bits
                out["message"] = " ".join(align_bits) + " " + out["message"]
            if not validation_error and "DIR generation failed" in warning:
                validation_error = warning
        if validation_error:
            out["validation_error"] = validation_error
            out["suggested_correction"] = suggested_correction or (codes[0] if codes else "")
        elif prior_code and not residual:
            out["suggested_correction"] = prior_code
        self.status(f"Design input requirements ready for {system_name}")
        return out

    def _size(
        self,
        pack: KnowledgePack,
        menu: DirMenu | None,
        system_name: str,
        application: str,
        dir_code: str,
        *,
        sizing_inputs: Any = None,
        prior_eval: Dict[str, Any] | None = None,
        app_warning: str = "",
        equipment_tag: str = "",
        reuse_inherited_dir: bool = False,
    ) -> Dict[str, Any]:
        shared_basis = shared_basis_from_inputs(getattr(self, "_identity_inputs", {}) or {}, prior_eval)
        if reuse_inherited_dir:
            decoded = list(
                (shared_basis or {}).get("decoded_dir")
                or (prior_eval or {}).get("decoded_dir")
                or []
            )
            dir_code = dir_code or inherited_dir_code(shared_basis, prior_eval)
            menu_scenario = str((prior_eval or {}).get("scenario_id") or "inherited")
        elif menu is None:
            return self._inherited_eval_dir_ready(
                system_name,
                application,
                shared_basis,
                warning=app_warning,
            )
        elif not menu.is_approved:
            return self._dir_requirements(
                pack,
                menu,
                system_name,
                application,
                warning=app_warning,
                validation_error=(
                    f"DIR menu for {menu.industry} / {menu.equipment_system_variant} "
                    f"is '{menu.lifecycle}' — approve before sizing."
                ),
                shared_basis=shared_basis,
            )
        else:
            dir_check = validate_dir_code(
                pack,
                menu.scenario_id,
                dir_code,
                requirements=menu.requirements,
                common_codes=menu.common_codes,
            )
            if not dir_check.ok:
                return self._dir_requirements(
                    pack,
                    menu,
                    system_name,
                    application,
                    warning=app_warning,
                    validation_error=dir_check.error or "Invalid DIR code",
                    suggested_correction=dir_check.suggested or "",
                    shared_basis=shared_basis,
                )
            decoded = list(dir_check.decoded or [])
            menu_scenario = menu.scenario_id
        prior = prior_eval or {}
        tag = equipment_tag or str(prior.get("equipment_tag") or "").strip()
        if not tag:
            tag = _suggest_tag(system_name, pack.equipment_system)
        identity_inputs = getattr(self, "_identity_inputs", None)
        if isinstance(identity_inputs, dict) and str(identity_inputs.get("equipment_tag") or "").strip():
            tag = str(identity_inputs.get("equipment_tag") or "").strip()

        creator_block = self._creator_content_block(
            pack, system_name, application, pack.equipment_system, dir_code
        )
        decoded_text = json.dumps(decoded, indent=2)[:20000]
        sizing_text = json.dumps(sizing_inputs, indent=2)[:12000] if sizing_inputs else ""
        prior_text = json.dumps(compact_prior_eval(prior, shared_basis), indent=2)[:8000]

        # AI_HANDSHAKE: sizing_plan — decide capacity/connection inputs vs DIR.
        self.status("Planning capacity and connection inputs…")
        plan_system = (
            pack.call_fragment("sizing_plan", "system")
            or "You are a senior life-science equipment SME planning what to size. Return ONLY JSON."
        )
        plan_user = (
            f"System: {system_name}\nApplication: {application}\nDIR code: {dir_code}\n"
            f"Decoded DIR:\n{decoded_text}\n"
            f"{unknown_dir_guidance(decoded)}"
            f"Prior evaluation (optional):\n{prior_text}\n"
            f"User sizing_inputs (may be empty):\n{sizing_text or '(none)'}\n"
        )
        sme_plan = pack.call_fragment("sizing_plan", "instructions")
        if sme_plan:
            plan_user += f"\n{sme_plan}\n"
        if creator_block:
            plan_user += f"\n{creator_block[:8000]}\n"
        plan_user += (
            "Return JSON: {\"capacity_parameters\":[string], \"connection_parameters\":[string], "
            "\"minimum_user_inputs\":[string], \"missing_inputs\":[string], "
            "\"dir_sufficient\": bool, \"gap_requirements\": [ "
            "{\"index\":1,\"label\":\"...\",\"options\":[{\"index\":1,\"text\":\"...\"}]} ] }\n"
            "gap_requirements must be a DIR-shaped questionnaire for missing material-balance "
            "or connection inputs only. If DIR already has enough, dir_sufficient=true and "
            "gap_requirements=[]."
        )
        try:
            plan = self.call_openai_json(system=plan_system, user=plan_user)
        except Exception as exc:
            plan = {
                "dir_sufficient": bool(sizing_inputs),
                "missing_inputs": [str(exc)],
                "gap_requirements": [],
            }
        if not isinstance(plan, dict):
            plan = {}

        missing = [str(x) for x in (plan.get("missing_inputs") or []) if str(x).strip()]
        gaps = plan.get("gap_requirements") if isinstance(plan.get("gap_requirements"), list) else []
        dir_sufficient = bool(plan.get("dir_sufficient")) and not missing
        if not dir_sufficient and not sizing_inputs and gaps:
            example = "-".join("1" for _ in gaps) or "1-1"
            self.status("Additional sizing inputs needed")
            return {
                "phase": "dir_requirements",
                "system_name": system_name,
                "application": application,
                "knowledge_pack": pack.pack_id,
                "scenario_id": menu_scenario,
                "dir_menu_label": "Additional sizing inputs",
                "inherited_parameters": inherited_parameters_payload(shared_basis),
                "reused_evaluation_dir": reuse_inherited_dir,
                "template_family": getattr(self, "template_family", "equipment_sizing"),
                "requirements": gaps,
                "common_codes": [example],
                "common_code_details": [
                    {
                        "code": example,
                        "caption": (
                            f"Method code only. Example with numbers: "
                            f"{example}; 12000 L normal, turndown 0.6"
                        ),
                    }
                ],
                "message": (
                    f"DIR {dir_code} is on file. Reply with a hyphen-separated method code "
                    f"(e.g. {example}). Digits are option indexes, not volumes. "
                    f"To supply actual values, append them after a semicolon "
                    f"(e.g. {example}; 12000 L normal, turndown 0.6)."
                ),
                "sme_warnings": [w for w in [app_warning, *missing] if w],
            }

        # AI_HANDSHAKE: sizing_search — vendor catalog / envelope references.
        self.status("Searching vendor catalogs for similar equipment…")
        search_context = ""
        try:
            queries = pack.build_search_queries(
                "sizing",
                system_name=system_name,
                application=application,
                equipment_system=pack.equipment_system,
                decoded=decoded,
            ) or pack.build_search_queries(
                "evaluate",
                system_name=system_name,
                application=application,
                equipment_system=pack.equipment_system,
                decoded=decoded,
            )
            snippets: List[Dict[str, str]] = []
            for q in queries:
                for hit in self.serper_search(q, num=5):
                    snippets.append(hit)
            search_context = format_search_context(
                enrich_search_hits_with_excerpts(snippets),
                limit=12,
            )
        except Exception as exc:
            search_context = f"(search skipped: {exc})"

        # AI_HANDSHAKE: sizing_capacity
        self.status("Sizing capacity…")
        cap_system = pack.call_fragment("sizing_capacity", "system") or plan_system
        cap_user = (
            f"Compute capacity for {system_name} ({application}).\n"
            f"DIR:\n{decoded_text}\nSizing inputs:\n{sizing_text or '(none)'}\n"
            f"Plan: {json.dumps(plan)[:8000]}\n"
            "Return JSON: {\"capacity\":{\"value\":\"\",\"unit\":\"\",\"basis\":\"\"}, "
            "\"inputs_used\":[], \"assumptions\":[], \"notes\":\"\"}\n"
            "capacity.value MUST be a number (with unit separately). Do not return TBD, "
            "Not calculable, or an empty value when a DIR range or pack screening method exists."
        )
        sme_cap = pack.call_fragment("sizing_capacity", "instructions")
        if sme_cap:
            cap_user += f"\n{sme_cap}\n"
        if creator_block:
            cap_user += f"\n{creator_block[:8000]}\n"
        try:
            cap_raw = self.call_openai_json(system=cap_system, user=cap_user)
        except Exception:
            cap_raw = {"capacity": {"value": "", "unit": "", "basis": "DIR"}, "assumptions": []}
        if not isinstance(cap_raw, dict):
            cap_raw = {}

        # AI_HANDSHAKE: sizing_connections
        sized_item = str(getattr(pack, "sized_item", "") or pack.meta.get("sized_item") or "sized item").strip()
        self.status(f"Sizing {sized_item} connections…")
        conn_system = pack.call_fragment("sizing_connections", "system") or plan_system
        conn_user = (
            f"Size connections that belong to this sized item ({sized_item}) for {system_name}. "
            f"Do not size unrelated host-system process nozzles unless the pack instructions say so.\n"
            f"DIR:\n{decoded_text}\nCapacity: {json.dumps(cap_raw.get('capacity'))}\n"
            f"Sizing inputs:\n{sizing_text or '(none)'}\n"
            "Return JSON: {\"connections\":[{\"name\":\"\",\"size\":\"\",\"unit\":\"\","
            "\"service\":\"\",\"basis\":\"\"}], \"utilities\":\"\", \"assumptions\":[]}"
        )
        sme_conn = pack.call_fragment("sizing_connections", "instructions")
        if sme_conn:
            conn_user += f"\n{sme_conn}\n"
        try:
            conn_raw = self.call_openai_json(system=conn_system, user=conn_user)
        except Exception:
            conn_raw = {"connections": [], "utilities": ""}
        if not isinstance(conn_raw, dict):
            conn_raw = {}

        # AI_HANDSHAKE: sizing_dimensions
        self.status("Estimating overall dimensions…")
        dim_system = pack.call_fragment("sizing_dimensions", "system") or plan_system
        dim_user = (
            f"Estimate overall envelope for {system_name} at the sized capacity.\n"
            f"Capacity: {json.dumps(cap_raw.get('capacity'))}\n"
            f"Prefer vendor/catalog search; fall back to geometric scale rules.\n"
            f"Search context:\n{str(search_context)[:20000]}\n"
            "Return JSON: {\"dimensions\":{\"value\":\"\",\"unit\":\"\",\"method\":\"\"}, "
            "\"source_basis\":[], \"notes\":\"\"}"
        )
        if creator_block:
            dim_user += f"\n{creator_block[:8000]}\n"
        sme_dim = pack.call_fragment("sizing_dimensions", "instructions")
        if sme_dim:
            dim_user += f"\n{sme_dim}\n"
        try:
            dim_raw = self.call_openai_json(system=dim_system, user=dim_user)
        except Exception:
            dim_raw = {
                "dimensions": {"value": "", "unit": "", "method": "geometric fallback"},
                "source_basis": ["geometric_scale"],
            }
        if not isinstance(dim_raw, dict):
            dim_raw = {}

        headings = pack.required_report_headings() or list(creator_tools.DEFAULT_SIZING_HEADINGS)
        heading_block = "\n".join(f"- {h}" for h in headings)

        # AI_HANDSHAKE: sizing_report
        self.status("Drafting sizing datasheet…")
        report_system = (
            pack.call_fragment("sizing_report", "system") or pack.build_system_prompt()
        )
        report_user = creator_tools.sizing_report_user_message(
            system_name=system_name,
            application=application,
            dir_code=dir_code,
            decoded_text=decoded_text,
            sizing_text=sizing_text,
            plan=plan if isinstance(plan, dict) else {},
            cap_raw=cap_raw,
            conn_raw=conn_raw,
            dim_raw=dim_raw,
            search_context=str(search_context or ""),
            creator_block=str(creator_block or ""),
            required_headings=headings,
            sized_item=sized_item,
            sme_instructions=pack.call_fragment("sizing_report", "instructions"),
        )
        try:
            report_raw = self.call_openai_json(system=report_system, user=report_user)
        except Exception:
            report_raw = {}
        if not isinstance(report_raw, dict):
            report_raw = {}
        if set(report_raw.keys()) == {"content"} and isinstance(report_raw.get("content"), dict):
            report_raw = report_raw["content"]

        raw: Dict[str, Any] = {
            "schema_version": "equipment_sizing_v1",
            "equipment_tag": tag,
            "equipment_name": str(
                prior.get("equipment_item_name") or prior.get("equipment_name") or system_name
            ),
            "equipment_system": pack.equipment_system,
            "equipment_type": str(prior.get("equipment_system") or pack.equipment_system),
            "capacity": cap_raw.get("capacity") or {},
            "connections": conn_raw.get("connections") or [],
            "dimensions": dim_raw.get("dimensions") or {},
            "utilities": conn_raw.get("utilities") or "",
            "inputs_used": list(cap_raw.get("inputs_used") or []) + [f"dir:{dir_code}"],
            "missing_inputs": missing,
            "assumptions": coerce_string_list_items(
                list(cap_raw.get("assumptions") or [])
                + list(conn_raw.get("assumptions") or [])
            ),
            "source_basis": coerce_string_list_items(dim_raw.get("source_basis") or ["dir", "knowledge_pack"]),
            "datasheet_markdown": "",
            "excel_ready_table": "",
            "creator_attribution": {
                "display_name": self.creator_display_name,
                "app_id": self.app_id,
            },
        }
        raw = creator_tools.merge_sizing_report(raw, report_raw, headings=headings)
        if not str(raw.get("datasheet_markdown") or "").strip():
            raw["datasheet_markdown"] = creator_tools.fallback_sizing_markdown(
                system_name=system_name,
                headings=headings,
                cap_raw=cap_raw,
                conn_raw=conn_raw,
                dim_raw=dim_raw,
                excel_ready_table=str(raw.get("excel_ready_table") or ""),
            )
        apply_user_identity(raw, getattr(self, "_identity_inputs", None))
        if search_context and "serper_search" not in raw["source_basis"]:
            raw["source_basis"].append("serper_search")
        if creator_block and "creator_references" not in raw["source_basis"]:
            raw["source_basis"].append("creator_references")

        md_text = str(raw.get("datasheet_markdown") or "")
        missing_heads = missing_report_headings(md_text, headings)
        thin = thin_report_sections(md_text, headings, min_chars=120)
        if missing_heads or thin:
            # AI_HANDSHAKE: sizing_repair — deepen thin/missing sizing headings.
            self.status("Repairing sizing report depth/sections…")
            default_repair = (
                "The previous sizing JSON needs a deeper datasheet_markdown.\n"
                "Keep supported numbers from capacity, connections, and dimensions JSON.\n"
                "Return JSON with datasheet_markdown (ALL required headings), "
                "selected_model, key_specs, and excel_ready_table "
                "(Item|Method/formula|Result|Unit|Basis)."
            )
            repair_preamble = (
                pack.call_fragment("sizing_repair", "instructions", default=default_repair)
                or default_repair
            )
            repair_user = (
                f"{repair_preamble}\n"
                f"Missing headings: {missing_heads or 'none'}.\n"
                f"Thin sections (expand to substantive multi-sentence engineering content): "
                f"{thin or 'none'}.\n"
                f"Required headings:\n{heading_block}\n\n"
                f"Capacity JSON: {json.dumps(cap_raw)[:12000]}\n"
                f"Connections JSON: {json.dumps(conn_raw)[:12000]}\n"
                f"Dimensions JSON: {json.dumps(dim_raw)[:12000]}\n"
                f"Industrial search references:\n{str(search_context)[:20000]}\n\n"
            )
            if creator_block:
                repair_user += f"{creator_block[:8000]}\n\n"
            repair_user += f"Previous sizing JSON:\n{json.dumps(raw)[:120000]}"
            try:
                repaired = self.call_openai_json(system=report_system, user=repair_user)
                if isinstance(repaired, dict):
                    if set(repaired.keys()) == {"content"} and isinstance(
                        repaired.get("content"), dict
                    ):
                        repaired = repaired["content"]
                    raw = creator_tools.merge_sizing_report(raw, repaired, headings=headings)
            except Exception:
                pass

        merge_warnings = [
            str(item).strip()
            for item in (raw.get("sme_warnings") or [])
            if str(item).strip()
        ]
        validated = validate_output(raw)
        result = validated.model_dump()
        result["phase"] = "evaluation"
        result["dir_code"] = dir_code
        result["system_name"] = system_name
        result["equipment_system_name"] = system_name
        result["application"] = application
        result["knowledge_pack"] = pack.pack_id
        # HANDSHAKE: artifact_stem / sized_item — pack.yaml sized_item + system name.
        attach_sizing_artifact_name(result, pack=pack)
        result["decoded_dir"] = decoded
        result["template_family"] = getattr(self, "template_family", "equipment_sizing")
        result["reused_evaluation_dir"] = reuse_inherited_dir
        warnings = list(result.get("sme_warnings") or [])
        warnings.extend(merge_warnings)
        if app_warning:
            warnings.append(app_warning)
        if warnings:
            result["sme_warnings"] = warnings
        return result

    def _build_pptx_slide_pack(self, pack: KnowledgePack, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM for slide-ready content; fall back to deterministic packing."""
        fallback = build_slide_pack_from_evaluation(evaluation)
        try:
            self.status("Drafting PPTX slide content with LLM…")
            compact = {
                "system_name": evaluation.get("system_name"),
                "application": evaluation.get("application"),
                "dir_code": evaluation.get("dir_code"),
                "decoded_dir": evaluation.get("decoded_dir"),
                "selected_model": evaluation.get("selected_model"),
                "capacity": evaluation.get("capacity"),
                "connections": evaluation.get("connections"),
                "dimensions": evaluation.get("dimensions"),
                "utilities": evaluation.get("utilities"),
                "assumptions": evaluation.get("assumptions"),
                "missing_inputs": evaluation.get("missing_inputs"),
                "source_basis": evaluation.get("source_basis"),
                "key_specs": evaluation.get("key_specs"),
                "excel_ready_table": evaluation.get("excel_ready_table") or "",
                "datasheet_markdown": evaluation.get("datasheet_markdown") or "",
            }
            # AI_HANDSHAKE: pptx — slide JSON from sizing result (schema contract in template).
            default_pptx_extra = (
                "You prepare presentation-ready engineering slide content. "
                "Keep visual density high and wording concise. "
                "Ground every claim in the sizing JSON (capacity, connections, "
                "dimensions, excel_ready_table) and datasheet_markdown. "
                "Numerical sizing values from that JSON are allowed and expected; "
                "do not replace validated numbers with TBD placeholders."
            )
            pptx_extra = (
                pack.call_fragment("pptx", "system_extra", default=default_pptx_extra)
                or default_pptx_extra
            )
            pptx_instructions = pack.call_fragment("pptx", "instructions")
            pptx_user = PPTX_SLIDE_SCHEMA_CONTRACT
            if pptx_instructions:
                pptx_user = f"{pptx_instructions}\n\n{pptx_user}"
            pptx_user += (
                "\n\nSizing JSON (includes full datasheet_markdown):\n"
                + json.dumps(compact, ensure_ascii=False)[:180000]
            )
            raw = self.call_openai_json(
                system=(pack.fragment("role") + "\n\n" + pptx_extra).strip(),
                user=pptx_user,
            )
            if not isinstance(raw, dict) or not isinstance(raw.get("slides"), list):
                return fallback
            # Ensure required identity fields
            raw.setdefault("system_name", fallback.get("system_name"))
            raw.setdefault("dir_code", fallback.get("dir_code"))
            if len(raw["slides"]) < 7:
                # pad from fallback
                fb_slides = fallback.get("slides") or []
                slides = list(raw["slides"])
                for i in range(len(slides), 7):
                    slides.append(fb_slides[i])
                raw["slides"] = slides
            return raw
        except Exception:
            self.status("LLM slide draft unavailable — using structured fallback pack…")
            return fallback

    def _attach_pptx(
        self,
        pack: KnowledgePack,
        evaluation: Dict[str, Any],
        *,
        py_root: Path,
    ) -> Dict[str, Any]:
        self.status("Building presentation-ready PPTX (reference visual style)…")
        attach_sizing_artifact_name(evaluation, pack=pack)
        slide_pack = self._build_pptx_slide_pack(pack, evaluation)
        try:
            self.status("Rendering title-slide equipment image…")
            attach_title_hero_image(
                evaluation,
                slide_pack,
                output_path=Path.cwd() / "artifacts" / f"{_sizing_artifact_basename(evaluation)} hero.png",
            )
        except Exception as exc:
            self.status(f"Title-slide image skipped ({exc})")
        out_path = Path.cwd() / "artifacts" / f"{_sizing_artifact_basename(evaluation)}.pptx"
        path = build_evaluation_pptx(
            evaluation,
            outline=pack.pptx_outline,
            output_path=out_path,
            slide_pack=slide_pack,
            pack_path=pack.path,
        )
        result = dict(evaluation)
        artifacts = dict(result.get("artifacts") or {})
        artifacts["pptx_path"] = str(path.resolve())
        if slide_pack.get("hero_image_path"):
            artifacts["hero_image_path"] = str(slide_pack["hero_image_path"])
        result["artifacts"] = artifacts
        result["pptx_slide_pack"] = slide_pack
        result["phase"] = "evaluation"
        result["deliverable"] = "pptx"
        note = ""
        if path.resolve() != out_path.resolve():
            note = (
                " (original file was locked — likely open in PowerPoint; "
                "wrote a timestamped copy instead)"
            )
        result["message"] = f"Wrote PPTX: {path}{note}"
        return result


def run_from_stdio() -> None:
    if sys.stdin.isatty():
        print(
            "Pipe JSON inputs into this script, e.g.:\n"
            "  '{\"system_name\":\"Media Prep Vessel\",\"application\":\"biopharma\"}' "
            "| python agent.py",
            file=sys.stderr,
        )
        raise SystemExit(2)

    raw = sys.stdin.buffer.read().decode("utf-8-sig")
    inputs = json.loads(raw) if raw.strip() else {}
    agent = EquipmentSizingAgent(status_callback=lambda m: print(m, file=sys.stderr))
    result = agent.run(inputs)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_from_stdio()
