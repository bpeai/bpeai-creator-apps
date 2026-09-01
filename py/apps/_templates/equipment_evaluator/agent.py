from __future__ import annotations

"""Equipment evaluator template agent (DIR → evaluate → optional PPTX).

Creator checklist after copying this folder to ``py/apps/<your_id>/``:
  1. Rename this class and set ``app_id`` to match folder / manifest ``id``.
  2. Set ``creator_display_name`` (hub attribution).
  3. Set ``knowledge_pack_id`` to the **same** ``app_id`` (1:1 private pack).
     ``equipment_system`` is taxonomy (mixing, filtration, …), not the pack name.
     If the pack is missing locally, the first ``local_chat`` run LLM-bootstraps
     a draft under ``py/knowledge/<app_id>/`` using the creator’s ``.env`` keys
     (not Cursor). Optional SME files go in ``references/content/``.
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

Local artifacts (gitignored ``./artifacts/``): markdown + PDF; optional PPTX.
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
    __package__ = "apps._templates.equipment_evaluator"

import json
import re
from typing import Any, Dict, List

from pydantic import ValidationError

from bpeai_creator_sdk import CreatorAppBase, coerce_string_list_items, validate_output
from bpeai_creator_sdk.artifacts import (
    build_evaluation_pdf,
    build_evaluation_pptx,
    build_slide_pack_from_evaluation,
)
from bpeai_creator_sdk.local_run import repo_py_root
from bpeai_creator_sdk.sme import (
    CONTENT_FOLDER_PROMPT,
    DirMenu,
    KnowledgePack,
    align_pack_to_app,
    append_dir_menu,
    build_content_index,
    check_application,
    check_equipment_option_names,
    component_schema_hints,
    creator_content_prompt_block,
    ensure_creator_pack_assets,
    list_missing_pack_files,
    load_knowledge_pack,
    match_dir_menu,
    missing_report_headings,
    normalize_generated_menu,
    prepare_bootstrapped_component,
    resolve_dir_menu,
    resolve_industry,
    resolve_scenario_id,
    resolve_variant_id,
    stamp_draft_meta,
    structure_example_snippet,
    thin_report_sections,
    validate_dir_code,
    write_pack_file,
)
from bpeai_creator_sdk.sme.dir_catalog import catalog_row_to_dir_menu
from bpeai_creator_sdk.tools import enrich_search_hits_with_excerpts, format_search_context

# Template-owned JSON schema contracts (deliverable). SME voice/search live in the pack —
# see docs/EI_AI_HANDSHAKES.md and prompt_fragments.yaml → calls / search_queries.yaml.

DIR_GENERATE_SCHEMA_CONTRACT = """Author a Design Input Requirements (DIR) questionnaire for this equipment case.

Return ONLY JSON:
{
  "label": "short menu title",
  "summary": "1-2 sentence design-scope summary",
  "system_examples": ["alias1", "alias2"],
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
- 4–7 options per requirement; indexes start at 1.
- common_codes MUST be hyphen-separated numeric starters matching requirement count,
  each with a caption that decodes the selection in one sentence (GPT style).
- Do NOT use mnemonic tags (SIP, IT, BPE) as common_codes.
- Prefer industrially realistic options for life-science equipment selection.
"""

PPTX_SLIDE_SCHEMA_CONTRACT = """Convert this evaluation JSON into a presentation slide pack.

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
      "hero_headline": ["line1", "line2", "line3"]
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
  card values ≤ 8 words; failure_modes ≤ 12 words each; option notes ≤ 12 words;
  recommended_why / cons ≤ 14 words each; decision_logic ≤ 35 words.
- Align strictly with the evaluation content (DIR, options, recommendation).
- Use project-team summary tone similar to a professional engineering deck.
- Prefer product-line manufacturer hints when present in the evaluation.
- Preserve failure modes, decision logic, vendor/product lines from the evaluation
  and from datasheet_markdown; do NOT invent unsupported claims.
- Prefer denser notes on slides 3 (objectives/failure modes), 5 (matrix/decision),
  and 6 (recommendation) when the report supports it — but stay within length limits.
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
  "do_not_specify": ["…"],
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
- List at least 5 realistic options; mark one as recommended basis (fit=best).
- Per option: >=2 industrial_applications, >=3 pros, >=2 cons/watchouts,
  >=2 manufacturers with product-line hints when known, plus why fit changes for THIS DIR.
- Include qualitative scale-up / performance reasoning appropriate to the equipment system.
- Weave industrial search citations into rationale and datasheet_markdown as (title + URL).
- Include alternate_basis, do_not_specify, preliminary_specs, evaluation_matrix.
- preliminary_specs must be strings like "Material: 316L", not {key, value} objects.
- Prefer SME catalog option names and manufacturer product-line hints when appropriate.
- datasheet_markdown MUST include ALL required headings supplied in the user message
  (from the knowledge pack report_outline) with SUBSTANTIVE multi-sentence bodies
  (no one-line stubs).
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
    lines: List[str] = []
    for opt in pack.option_catalog():
        name = opt.get("name") or ""
        mfrs = opt.get("manufacturers") or []
        mfr_s = ", ".join(str(m) for m in mfrs[:6]) if isinstance(mfrs, list) else ""
        lines.append(f"- {name}" + (f" | vendors: {mfr_s}" if mfr_s else ""))
    defaults = pack.equipment_options.get("do_not_specify_defaults") or []
    if defaults:
        lines.append("Default exclusions (adapt to DIR):")
        lines.extend(f"- {d}" for d in defaults)
    return "\n".join(lines)


def _write_markdown_artifact(result: Dict[str, Any], *, py_root: Path) -> Path | None:  # noqa: ARG001
    md = (result.get("datasheet_markdown") or "").strip()
    if not md:
        return None
    system = re.sub(r"[^\w\-]+", "_", str(result.get("system_name") or "evaluation")).strip("_")
    target = Path.cwd() / "artifacts" / f"{system or 'evaluation'}_evaluation.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(md, encoding="utf-8")
    return target


def _write_pdf_artifact(result: Dict[str, Any]) -> Path | None:
    md = (result.get("datasheet_markdown") or "").strip()
    if not md and not result.get("selected_model"):
        return None
    system = re.sub(r"[^\w\-]+", "_", str(result.get("system_name") or "evaluation")).strip("_")
    target = Path.cwd() / "artifacts" / f"{system or 'evaluation'}_evaluation.pdf"
    return build_evaluation_pdf(result, output_path=target)


class EquipmentEvaluatorAgent(CreatorAppBase):
    """Pack-backed DIR → evaluate template (custom-GPT parity).

    After copy: rename class, ``app_id``, ``knowledge_pack_id`` (same as ``app_id``),
    ``creator_display_name``.
    Missing packs / YAML components are LLM-bootstrapped as draft-for-approval.
    Optional helpers: ``creator_tools.py`` (not imported by default).
    """

    # HANDSHAKE: manifest.id / python_entrypoint / hub routing must match these ids.
    app_id = "equipment_evaluator"
    knowledge_pack_id = "equipment_evaluator"
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
        system_name = str(inputs.get("system_name") or "Process Vessel").strip()
        application_raw = str(inputs.get("application") or "biopharmaceutical").strip()
        industry_raw = str(inputs.get("industry") or "").strip()
        variant_raw = str(inputs.get("equipment_system_variant") or "").strip()
        scenario_raw = str(inputs.get("scenario_id") or "").strip()
        dir_code = str(inputs.get("dir_code") or "").strip()
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
            )

        app_check = check_application(pack, application_raw)
        application = app_check.normalized or application_raw
        combined_warning = " | ".join(
            w for w in [app_check.warning, *bootstrap_notes] if w
        )

        force_generate = phase in {"generate_dir"} or bool(inputs.get("force_generate_dir"))
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
            if isinstance(prior, dict) and prior.get("selected_model"):
                return self._attach_pptx(pack, prior, py_root=py_root)
            if dir_code:
                evaluated = self._evaluate(
                    pack,
                    menu,
                    system_name,
                    application,
                    dir_code,
                    app_warning=combined_warning,
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
            )

        # HANDSHAKE: evaluate path → SSE "evaluation" / "result" + equipment_selector_v1.
        result = self._evaluate(
            pack,
            menu,
            system_name,
            application,
            dir_code,
            app_warning=combined_warning,
        )
        if result.get("phase") == "evaluation":
            md_path = _write_markdown_artifact(result, py_root=py_root)
            artifacts = dict(result.get("artifacts") or {})
            if md_path:
                artifacts["markdown_path"] = str(md_path)
            try:
                # HANDSHAKE: self.status(...) → SSE event "status" (progress line).
                self.status("Writing PDF evaluation report…")
                pdf_path = _write_pdf_artifact(result)
                if pdf_path:
                    artifacts["pdf_path"] = str(pdf_path.resolve())
            except Exception as exc:
                self.status(f"PDF export skipped ({exc})")
            result["artifacts"] = artifacts
            result["pptx_prompt"] = "Would you like a presentation-ready PPTX file? Reply pptx or y."
        return result

    def _ensure_knowledge_pack(
        self,
        pack_id: str,
        *,
        py_root: Path,
        equipment_system: str = "",
    ) -> tuple[KnowledgePack, List[str]]:
        """Load pack; LLM-create any missing YAML/README as draft-for-approval.

        Creator-owned pack content is drafted locally (not copied from website packs).
        Style PPTX/PDF shells seed into ``references/style/``. Optional SME documents
        go in ``references/content/`` and are indexed as supplemental LLM context.
        """
        notes: List[str] = []
        app_id = str(getattr(self, "app_id", "") or pack_id).strip() or pack_id
        aligned = align_pack_to_app(app_id, py_root=py_root, pack_id=pack_id)
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

        missing = list_missing_pack_files(pack_id, py_root=py_root, include_optional=True)
        created: List[str] = []
        if missing:
            self.status(
                f"Knowledge pack '{pack_id}' incomplete ({len(missing)} file(s) missing) — "
                "bootstrapping initial draft components…"
            )
            for filename in missing:
                try:
                    self._bootstrap_pack_component(
                        pack_id,
                        filename,
                        equipment_system=eq,
                        py_root=py_root,
                    )
                    created.append(filename)
                except Exception as exc:
                    notes.append(f"Failed to bootstrap {filename}: {exc}")
                    self.status(f"Bootstrap failed for {filename}: {exc}")

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
    ) -> Path:
        """Generate one missing pack file via LLM (or a minimal README fallback)."""
        if filename == "README.md":
            md = (
                f"# {pack_id} knowledge pack (DRAFT)\n\n"
                f"Initial auto-generated SME pack for **{equipment_system}**.\n\n"
                "Status: `draft_pending_sme_approval` — review and edit YAML before "
                "production use.\n\n"
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
        )
        payload = prepare_bootstrapped_component(
            filename,
            payload,
            pack_id=pack_id,
            equipment_system=equipment_system,
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

    def _generate_pack_component_llm(
        self,
        pack_id: str,
        filename: str,
        *,
        equipment_system: str,
        py_root: Path,
    ) -> Dict[str, Any]:
        """LLM function: return JSON/YAML-mappable content for one pack file."""
        # AI_HANDSHAKE: pack_bootstrap — authoring-time draft of missing pack YAML.
        hints = component_schema_hints()
        schema_hint = hints.get(filename, "Valid YAML mapping for this pack component.")
        reference = structure_example_snippet(filename, py_root=py_root)
        app_label = getattr(self, "app_id", "equipment_evaluator")
        default_system = (
            "You are a senior life-science process / equipment SME authoring an "
            "initial draft knowledge pack for BPEAI equipment_evaluator apps. "
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
            frag_path = py_root / "knowledge" / pack_id / "prompt_fragments.yaml"
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
            f"Reference shape from creator-apps `_examples/mixing_stub` "
            f"(adapt domain content; do not copy mixing-specific options; "
            f"do not copy website/platform pack content):\n"
            f"{reference}\n\n"
            "Rules:\n"
            "- For dir_requirements.yaml emit dir_menus only (5–7 DIR requirements "
            "and 2+ numeric common_codes with hyphenated indexes + captions; not "
            "SIP/IT tags). Do not include menus or scenarios keys.\n"
            "- Include at least 5 equipment options when writing equipment_options.yaml.\n"
            "- fit_enum.allowed must include best, strong, conditional, limited, "
            "add-on, special-case.\n"
            "- report_outline required_headings must include: Validated DIR, Design basis, "
            "Strong-fit mixing types (or domain equivalent such as Strong-fit filter types), "
            "Recommended basis of design, Option evaluation, Do not specify, "
            "Preliminary specification, Manufacturers and references.\n"
            "- pptx_outline should define 7 slides with a domain-appropriate title_prefix.\n"
            "- Include search_queries.yaml with domain-appropriate Serper templates "
            "(no unrelated vendor brand names).\n"
            "- Mark draft intent via label/description wording where appropriate.\n"
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
        """Reuse catalog match, or Serper+LLM generate and append a draft menu."""
        notes: List[str] = []
        if not force_generate:
            hit = match_dir_menu(
                pack,
                system_name=system_name,
                scenario_id=scenario_id,
                equipment_system_variant=equipment_system_variant,
                industry=industry,
                application=application,
                allow_draft=True,
            )
            if hit is not None:
                return hit, notes
            # Legacy resolve (menus[] / scenarios) when list catalog has no hit
            legacy = resolve_dir_menu(
                pack,
                system_name=system_name,
                scenario_id=scenario_id,
                equipment_system_variant=equipment_system_variant,
                industry=industry,
                application=application,
                require_approved=False,
            )
            # If legacy came from dir_catalog via resolve_dir_menu, use it.
            if legacy.source == "dir_catalog":
                return legacy, notes
            authored_legacy = bool(pack.menus) or bool(
                pack.dir_requirements.get("scenarios")
            )
            # Reuse only YAML-authored menus/scenarios — not synthesized dir_menus copies.
            if (
                authored_legacy
                and legacy.requirements
                and legacy.source in {"menu", "scenario_fallback"}
            ):
                # Prefer authored pack questionnaires (scenarios / menus) over LLM
                # regenerate. List-catalog miss alone must not invent a parallel DIR
                # when fingerprint aliases already resolved a real scenario.
                if legacy.source == "scenario_fallback":
                    return legacy, notes
                if legacy.scenario_id and legacy.scenario_id not in {"", "default"}:
                    return legacy, notes
                if not pack.dir_menus:
                    return legacy, notes

        try:
            menu = self._generate_and_persist_dir_menu(
                pack,
                system_name=system_name,
                application=application,
                scenario_id=scenario_id,
                equipment_system_variant=equipment_system_variant,
                industry=industry,
            )
            notes.append(
                f"Generated draft DIR menu '{menu.menu_id or menu.scenario_id}' "
                f"(status={menu.lifecycle}) and appended to pack catalog for SME review."
            )
            return menu, notes
        except Exception as exc:
            notes.append(f"DIR generation failed ({exc}); falling back to pack menu.")
            fallback = resolve_dir_menu(
                pack,
                system_name=system_name,
                scenario_id=scenario_id,
                equipment_system_variant=equipment_system_variant,
                industry=industry,
                application=application,
                require_approved=False,
            )
            return fallback, notes

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
        sid = (scenario_id or "").strip() or resolve_scenario_id(
            pack, system_name, application=application
        )
        # Mint a scenario id from the system name so catalogs grow per case.
        # Use the slug as-is (bioreactor), not a "_dir" suffix.
        if not scenario_id and sid == pack.default_scenario:
            slug = re.sub(r"[^a-z0-9]+", "_", system_name.strip().lower()).strip("_")
            if slug and slug not in {"process_vessel", "process"}:
                sid = slug
        variant = resolve_variant_id(
            pack,
            system_name,
            equipment_system_variant,
            application=application,
        )
        ind = resolve_industry(pack, industry=industry, application=application)

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
            pack, system_name, application, pack.equipment_system, sid, variant
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
            f"System name: {system_name}\n"
            f"Application / industry: {application} / {ind}\n"
            f"Equipment system: {pack.equipment_system}\n"
            f"Scenario id hint: {sid}\n"
            f"Variant hint: {variant}\n\n"
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

        row = normalize_generated_menu(
            raw,
            system_name=system_name,
            application=application,
            scenario_id=sid,
            variant=variant,
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
    ) -> Dict[str, Any]:
        self.status(f"Assembling design input requirements for {system_name}…")
        requirements = menu.requirements
        try:
            from bpeai_creator_sdk.sme.dir_catalog import ensure_common_codes_for_requirements

            entries = ensure_common_codes_for_requirements(
                menu.common_codes,
                requirements,
                system_name=system_name,
                application=application,
                min_count=3,
                max_count=4,
            )
        except Exception:
            entries = pack._normalize_common_codes(menu.common_codes)
        codes = [e["code"] for e in entries]
        example = codes[0] if codes else "-".join("1" for _ in (requirements or [1]))
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
            "requirements": requirements,
            "common_codes": codes,
            "common_code_details": entries,
            "message": (
                f"For {system_name} — {menu.label} "
                f"({menu.industry} / {menu.equipment_system_variant} / scenario={menu.scenario_id}), "
                f"I’ll assume {application} unless you specify otherwise. "
                f"Reply with a hyphen-separated DIR code (e.g. {example})."
            ),
        }
        if warning:
            out["sme_warnings"] = [warning]
        if validation_error:
            out["validation_error"] = validation_error
            out["suggested_correction"] = suggested_correction or (codes[0] if codes else "")
        self.status(f"Design input requirements ready for {system_name}")
        return out

    def _evaluate(
        self,
        pack: KnowledgePack,
        menu: DirMenu,
        system_name: str,
        application: str,
        dir_code: str,
        *,
        app_warning: str = "",
    ) -> Dict[str, Any]:
        if not menu.is_approved:
            return self._dir_requirements(
                pack,
                menu,
                system_name,
                application,
                warning=app_warning,
                validation_error=(
                    f"DIR menu for {menu.industry} / {menu.equipment_system_variant} "
                    f"is '{menu.lifecycle}' — approve before evaluate."
                ),
            )
        requirements = menu.requirements
        dir_check = validate_dir_code(
            pack,
            menu.scenario_id,
            dir_code,
            requirements=requirements,
            common_codes=menu.common_codes,
        )
        if not dir_check.ok:
            return self._dir_requirements(
                pack,
                menu,
                system_name,
                application,
                warning=app_warning,
                validation_error=dir_check.error,
                suggested_correction=dir_check.suggested_correction,
            )

        self.status(f"Validated DIR: {dir_code}")
        # AI_HANDSHAKE: evaluate_search — Serper industrial references for evaluate.
        self.status("Searching industrial references…")

        queries = pack.build_search_queries(
            "evaluate",
            system_name=system_name,
            application=application,
            equipment_system=pack.equipment_system,
            decoded=dir_check.decoded,
        )
        snippets: List[Dict[str, str]] = []
        for q in queries:
            for hit in self.serper_search(q, num=5):
                snippets.append(hit)

        # Deduplicate by link before excerpt fetch
        deduped: List[Dict[str, Any]] = []
        seen_links: set[str] = set()
        for h in snippets:
            link = str(h.get("link") or "").strip()
            key = link or f"{h.get('title')}|{h.get('snippet')}"
            if key in seen_links:
                continue
            seen_links.add(key)
            deduped.append(h)

        self.status("Fetching page excerpts for top industrial references…")
        enriched = enrich_search_hits_with_excerpts(deduped)
        search_context = format_search_context(enriched, limit=18)
        creator_block = self._creator_content_block(
            pack,
            system_name,
            application,
            pack.equipment_system,
            dir_code,
            json.dumps(dir_check.decoded),
        )

        headings = pack.required_report_headings()
        heading_block = ", ".join(headings) if headings else "(see EVALUATION_SCHEMA_CONTRACT)"

        # AI_HANDSHAKE: evaluate — system from fragments; user includes SME calls + schema.
        self.status(f"Generating {pack.equipment_system} technology evaluation…")
        depth_block = pack.fragment("depth_requirements")
        sme_eval_extra = pack.call_fragment("evaluate", "user_instructions")
        user_prompt = (
            f"System: {system_name}\n"
            f"Application: {application}\n"
            f"Equipment system / pack: {pack.equipment_system} ({pack.pack_id})\n"
            f"Scenario: {menu.scenario_id}\n"
            f"Industry: {menu.industry}\n"
            f"Equipment system variant: {menu.equipment_system_variant}\n"
            f"Validated DIR code: {dir_code}\n"
            f"Decoded DIR:\n{json.dumps(dir_check.decoded, indent=2)}\n\n"
            f"DIR requirement structure:\n{json.dumps(requirements, indent=2)}\n\n"
            f"SME equipment options catalog:\n{_option_catalog_block(pack)}\n\n"
            f"Required datasheet_markdown headings: {heading_block}\n\n"
            f"Depth requirements:\n{depth_block}\n\n"
            f"Industrial search references (snippets + page excerpts):\n"
            f"{search_context or '(no serper results — use engineering judgment)'}\n\n"
        )
        if creator_block:
            user_prompt += f"{creator_block}\n\n"
        if sme_eval_extra:
            user_prompt += f"{sme_eval_extra}\n\n"
        user_prompt += EVALUATION_SCHEMA_CONTRACT
        system_prompt = pack.build_system_prompt()
        raw = self.call_openai_json(system=system_prompt, user=user_prompt)
        raw = self._normalize_raw(raw, pack, system_name)

        # Soft-check option names (evaluation_options canonical; mixing_options alias)
        opts = raw.get("evaluation_options")
        if not isinstance(opts, list) or not opts:
            opts = raw.get("mixing_options") if isinstance(raw.get("mixing_options"), list) else []
        raw["evaluation_options"] = opts
        raw["mixing_options"] = opts
        names: List[str] = []
        if raw.get("selected_model"):
            names.append(str(raw["selected_model"]))
        for opt in opts:
            if isinstance(opt, dict) and opt.get("name"):
                names.append(str(opt["name"]))
        opt_check = check_equipment_option_names(pack, names)

        allowed_fit = set(
            (pack.validation_rules.get("fit_enum") or {}).get("allowed")
            or ["best", "strong", "conditional", "limited", "add-on", "special-case"]
        )
        # Expand allowed fits used by GPT sample
        allowed_fit |= {"add-on", "special-case", "addon", "special_case"}
        for opt in opts:
            if isinstance(opt, dict) and opt.get("fit") not in allowed_fit:
                fit = str(opt.get("fit") or "").lower().replace("_", "-")
                opt["fit"] = fit if fit in allowed_fit else "conditional"

        # Repair missing headings and/or thin sections once if needed
        md_text = str(raw.get("datasheet_markdown") or "")
        missing = missing_report_headings(md_text, headings)
        thin = thin_report_sections(md_text, headings, min_chars=120)
        if missing or thin:
            # AI_HANDSHAKE: evaluate_repair — deepen thin/missing report sections.
            self.status("Repairing evaluation report depth/sections…")
            default_repair = (
                "The previous JSON evaluation needs a deeper datasheet_markdown.\n"
                "Also ensure failure_modes has >=3 items, each evaluation_options entry meets the "
                "depth bar, and weave search citations (title + URL) into rationale and markdown.\n"
                "Return the FULL corrected JSON object (same schema) with a complete "
                "datasheet_markdown that includes ALL required headings."
            )
            repair_preamble = (
                pack.call_fragment("evaluate_repair", "instructions", default=default_repair)
                or default_repair
            )
            repair_user = (
                f"{repair_preamble}\n"
                f"Missing headings: {missing or 'none'}.\n"
                f"Thin sections (expand to substantive multi-sentence engineering content): "
                f"{thin or 'none'}.\n"
                f"Required headings: {heading_block}.\n\n"
                f"Industrial search references:\n{search_context[:20000]}\n\n"
            )
            if creator_block:
                repair_user += f"{creator_block[:12000]}\n\n"
            repair_user += f"Previous JSON:\n{json.dumps(raw)[:120000]}"
            try:
                repaired = self.call_openai_json(system=system_prompt, user=repair_user)
                repaired = self._normalize_raw(repaired, pack, system_name)
                raw = repaired
            except Exception:
                # Keep original if repair fails
                pass

        # HANDSHAKE: validated equipment_selector_v1 + phase=evaluation for hub/portal.
        validated = self._validate_evaluation_json(raw, pack, system_name, system_prompt)
        result = validated.model_dump()
        result["phase"] = "evaluation"
        result["dir_code"] = dir_code
        result["system_name"] = system_name
        result["application"] = application
        result["knowledge_pack"] = pack.pack_id
        result["scenario_id"] = menu.scenario_id
        result["industry"] = menu.industry
        result["equipment_system_variant"] = menu.equipment_system_variant
        result["decoded_dir"] = dir_check.decoded
        basis = list(result.get("source_basis") or [])
        if creator_block and "creator_references" not in basis:
            basis.append("creator_references")
            result["source_basis"] = basis
        warnings = [w for w in [app_warning, *opt_check.warnings] if w]
        still_missing = missing_report_headings(
            str(result.get("datasheet_markdown") or ""),
            headings,
        )
        still_thin = thin_report_sections(
            str(result.get("datasheet_markdown") or ""),
            headings,
            min_chars=120,
        )
        if still_missing:
            warnings.append(f"Report missing headings: {', '.join(still_missing)}")
        if still_thin:
            warnings.append(f"Report thin sections: {', '.join(still_thin)}")
        if warnings:
            result["sme_warnings"] = warnings
            basis = list(result.get("source_basis") or [])
            basis.extend(warnings)
            result["source_basis"] = basis
        return result

    def _validate_evaluation_json(
        self,
        raw: Dict[str, Any],
        pack: KnowledgePack,
        system_name: str,
        system_prompt: str,
    ):
        """Validate equipment_selector_v1; one LLM repair pass on schema errors."""
        try:
            return validate_output(raw)
        except ValidationError as exc:
            self.status("Repairing evaluation JSON schema…")
            repair_user = (
                "The previous JSON failed equipment_selector_v1 validation.\n"
                "Return the FULL corrected JSON object using the same schema.\n"
                "preliminary_specs, objectives, failure_modes, do_not_specify, and "
                "manufacturers MUST be arrays of strings "
                '(e.g. "Material: 316L stainless"). Never emit {key, value} objects '
                "except in key_specs.\n"
                f"Validation errors:\n{exc}\n\n"
                f"Previous JSON:\n{json.dumps(raw)[:120000]}"
            )
            try:
                repaired = self.call_openai_json(system=system_prompt, user=repair_user)
                repaired = self._normalize_raw(repaired, pack, system_name)
                return validate_output(repaired)
            except Exception:
                raise exc

    def _normalize_raw(
        self,
        raw: Dict[str, Any],
        pack: KnowledgePack,
        system_name: str,
    ) -> Dict[str, Any]:
        raw.setdefault("schema_version", "equipment_selector_v1")
        raw.setdefault("equipment_system", pack.equipment_system)
        raw.setdefault(
            "creator_attribution",
            {"display_name": self.creator_display_name, "app_id": self.app_id},
        )
        if not raw.get("equipment_tag"):
            raw["equipment_tag"] = _suggest_tag(system_name, pack.equipment_system)
        if not raw.get("equipment_name"):
            raw["equipment_name"] = (
                f"{system_name} — {raw.get('selected_model', pack.meta.get('label', 'Equipment'))}"
            )
        if not raw.get("rationale") and raw.get("recommended_basis"):
            raw["rationale"] = str(raw["recommended_basis"])
        if not raw.get("selected_model") and raw.get("recommended_basis"):
            raw["selected_model"] = str(raw["recommended_basis"])
        for key in (
            "objectives",
            "failure_modes",
            "do_not_specify",
            "preliminary_specs",
            "manufacturers",
            "source_basis",
        ):
            if key in raw and raw[key] is not None:
                raw[key] = coerce_string_list_items(raw[key])
        return raw

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
                "dir_summary": evaluation.get("dir_summary"),
                "design_basis": evaluation.get("design_basis"),
                "objectives": evaluation.get("objectives"),
                "failure_modes": evaluation.get("failure_modes"),
                "recommended_basis": evaluation.get("recommended_basis"),
                "alternate_basis": evaluation.get("alternate_basis"),
                "rationale": evaluation.get("rationale"),
                "selected_model": evaluation.get("selected_model"),
                "evaluation_options": evaluation.get("evaluation_options")
                or evaluation.get("mixing_options"),
                "mixing_options": evaluation.get("evaluation_options")
                or evaluation.get("mixing_options"),
                "evaluation_matrix": evaluation.get("evaluation_matrix"),
                "preliminary_specs": evaluation.get("preliminary_specs"),
                "manufacturers": evaluation.get("manufacturers"),
                "do_not_specify": evaluation.get("do_not_specify"),
                "source_basis": evaluation.get("source_basis"),
                "key_specs": evaluation.get("key_specs"),
                # Full report — preserve failure modes, decision logic, vendor lines
                "datasheet_markdown": evaluation.get("datasheet_markdown") or "",
            }
            # AI_HANDSHAKE: pptx — slide JSON from evaluation (schema contract in template).
            default_pptx_extra = (
                "You prepare presentation-ready engineering slide content. "
                "Keep visual density high and wording concise. "
                "Ground every claim in the evaluation JSON and datasheet_markdown; "
                "do not invent unsupported claims."
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
                "\n\nEvaluation JSON (includes full datasheet_markdown):\n"
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
        slide_pack = self._build_pptx_slide_pack(pack, evaluation)
        system = re.sub(r"[^\w\-]+", "_", str(evaluation.get("system_name") or "evaluation")).strip("_")
        out_path = Path.cwd() / "artifacts" / f"{system or 'evaluation'}_evaluation.pptx"
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
    agent = EquipmentEvaluatorAgent(status_callback=lambda m: print(m, file=sys.stderr))
    result = agent.run(inputs)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_from_stdio()
