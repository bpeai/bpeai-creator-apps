from __future__ import annotations

"""Equipment evaluator template agent (DIR → evaluate → optional PPTX).

Creator checklist after copying this folder to ``py/apps/<your_id>/``:
  1. Rename this class and set ``app_id`` to match folder / manifest ``id``.
  2. Set ``creator_display_name`` (hub attribution).
  3. Set ``knowledge_pack_id`` to an existing pack under ``py/knowledge/<id>/``
     (default ``mixing``). Prefer editing pack YAML over this file's prompts.
  4. Update ``manifest.json`` (slug, label, equipment_system, optional knowledge_pack).
  5. Local test: ``python py/tools/local_chat.py --app <your_id>`` then DIR → pptx.
  6. Leave EVALUATION_PROMPT / depth bar alone unless you are changing the
     deliverable contract; pack ``prompt_fragments.yaml`` is the SME dial.

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

from bpeai_creator_sdk import CreatorAppBase, validate_output
from bpeai_creator_sdk.artifacts import (
    build_evaluation_pdf,
    build_evaluation_pptx,
    build_slide_pack_from_evaluation,
)
from bpeai_creator_sdk.local_run import repo_py_root
from bpeai_creator_sdk.sme import (
    KnowledgePack,
    check_application,
    check_equipment_option_names,
    load_knowledge_pack,
    missing_report_headings,
    resolve_scenario_id,
    thin_report_sections,
    validate_dir_code,
)
from bpeai_creator_sdk.tools import enrich_search_hits_with_excerpts, format_search_context

PPTX_SLIDE_PACK_PROMPT = """Convert this mixing evaluation JSON into a presentation slide pack.

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

EVALUATION_PROMPT = """Run a full mixing technology evaluation for the validated DIR code.

Return JSON matching equipment_selector_v1 WITH these GPT-parity fields populated:
{
  "schema_version": "equipment_selector_v1",
  "equipment_tag": "AG-101 or MX-101 style tag",
  "selected_model": "Recommended basis of design (generic type, not a single SKU)",
  "equipment_system": "<pack equipment_system>",
  "equipment_name": "Descriptive equipment name",
  "equipment_category": "Mixing",
  "key_specs": [{"key": "Working volume", "value": "…"}, …],
  "rationale": "Multi-paragraph why-best including scale-up and GMP/cleanability",
  "creator_attribution": {"display_name": "…", "app_id": "…"},
  "design_basis": "Selection implication narrative from the DIR (multi-sentence)",
  "dir_summary": "One-paragraph restatement of decoded DIR basis",
  "objectives": ["…"],
  "failure_modes": ["at least 3 concrete failure modes for THIS DIR"],
  "recommended_basis": "One-line recommended basis of design",
  "alternate_basis": "One-line alternate / backup",
  "do_not_specify": ["…"],
  "preliminary_specs": ["…"],
  "evaluation_matrix": [
    {"option": "…", "technical_fit": "Best|Strong|…", "gmp": "High|…",
     "scale_up_risk": "Low|…", "cost_schedule": "Best|…", "reliability": "High|…", "rank": 1}
  ],
  "mixing_options": [
    {
      "name": "Top-entry low-shear axial hydrofoil agitator",
      "fit": "best|strong|conditional|limited|add-on|special-case",
      "industrial_applications": ["…", "…"],
      "pros": ["…", "…", "…"],
      "cons": ["…", "…"],
      "manufacturers": ["SPX FLOW Lightnin (A310/A510)", "…"]
    }
  ],
  "manufacturers": ["…"],
  "datasheet_markdown": "FULL sectioned markdown report (see required headings)",
  "source_basis": ["user_inputs", "knowledge_pack", "serper_search", "industry_references"]
}

Requirements (depth bar — do not produce thin one-line sections):
- Use the decoded DIR; do not invent a different volume/vessel/duty.
- List at least 5 realistic options; mark one as recommended basis (fit=best).
- Per option: >=2 industrial_applications, >=3 pros, >=2 cons/watchouts,
  >=2 manufacturers with product-line hints when known, plus why fit changes for THIS DIR.
- Include qualitative scale-up / blend-time / tip-speed / P/V reasoning where applicable.
- Weave industrial search citations into rationale and datasheet_markdown as (title + URL).
- Include alternate_basis, do_not_specify, preliminary_specs, evaluation_matrix.
- Prefer SME catalog option names and manufacturer product-line hints when appropriate.
- datasheet_markdown MUST include these headings with SUBSTANTIVE multi-sentence bodies
  (no one-line stubs): Validated DIR, Design basis, Strong-fit mixing types,
  Recommended basis of design, Option evaluation, Do not specify,
  Preliminary specification, Manufacturers and references.
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


def _dir_aware_queries(
    *,
    system_name: str,
    application: str,
    equipment_system: str,
    decoded: List[Dict[str, Any]],
) -> List[str]:
    by_label = {
        str(d.get("label") or "").lower(): str(d.get("option_text") or "")
        for d in decoded
    }
    volume = by_label.get("working volume", "")
    vessel = next((v for k, v in by_label.items() if "vessel" in k or "format" in k or "tank" in k), "")
    solids = next(
        (v for k, v in by_label.items() if "media" in k or "solids" in k or "resin" in k),
        "",
    )
    duty = next((v for k, v in by_label.items() if "objective" in k or "duty" in k), "")
    powder = next((v for k, v in by_label.items() if "powder" in k or "addition" in k), "")

    queries = [
        f"{system_name} {equipment_system} agitator {application} {volume}".strip(),
        f"{application} media preparation vessel agitator impeller selection {vessel}".strip(),
        f"sanitary {equipment_system} {solids} {duty} {application}".strip(),
        f"biopharmaceutical powder dissolution agitator hydrofoil {volume}".strip(),
        f"inline powder induction eductor media buffer preparation {powder}".strip(),
        f"aseptic magnetic bottom mixer biopharmaceutical {vessel}".strip(),
        # Vendor / product-line discovery (deeper citations)
        f"Lightnin A310 A510 hydrofoil media preparation biopharmaceutical agitator",
        f"Admix Fastfeed Silverson Flashmix powder induction biopharma",
        f"Alfa Laval LeviMag magnetic mixer single use biopharmaceutical",
    ]
    # Deduplicate while preserving order.
    seen: set[str] = set()
    out: List[str] = []
    for q in queries:
        qn = " ".join(q.split())
        if len(qn) < 12 or qn.lower() in seen:
            continue
        seen.add(qn.lower())
        out.append(qn)
    return out[:9]


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

    After copy: rename class, ``app_id``, ``knowledge_pack_id``, ``creator_display_name``.
    """

    app_id = "equipment_evaluator"
    knowledge_pack_id = "mixing"
    creator_display_name = "Your Name"

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        system_name = str(inputs.get("system_name") or "Process Vessel").strip()
        application_raw = str(inputs.get("application") or "biopharmaceutical").strip()
        dir_code = str(inputs.get("dir_code") or "").strip()
        phase = str(inputs.get("phase") or "").strip().lower()
        deliverable = str(inputs.get("deliverable") or "evaluation").strip().lower()

        pack_id = str(
            inputs.get("knowledge_pack") or self.knowledge_pack_id or "mixing"
        ).strip()
        py_root = repo_py_root()
        pack = load_knowledge_pack(pack_id, py_root=py_root)
        scenario_id = resolve_scenario_id(pack, system_name)

        app_check = check_application(pack, application_raw)
        application = app_check.normalized or application_raw

        # PPTX from a prior evaluation payload
        if deliverable == "pptx" or phase == "pptx":
            prior = inputs.get("evaluation_result")
            if isinstance(prior, dict) and prior.get("selected_model"):
                return self._attach_pptx(pack, prior, py_root=py_root)
            if dir_code:
                evaluated = self._evaluate(
                    pack,
                    scenario_id,
                    system_name,
                    application,
                    dir_code,
                    app_warning=app_check.warning,
                )
                if evaluated.get("phase") == "evaluation":
                    return self._attach_pptx(pack, evaluated, py_root=py_root)
                return evaluated
            return {
                "phase": "pptx_error",
                "message": "Provide dir_code or evaluation_result to generate a PPTX.",
            }

        if phase in {"dir", "dir_requirements"} or not dir_code:
            return self._dir_requirements(
                pack,
                scenario_id,
                system_name,
                application,
                warning=app_check.warning,
            )

        result = self._evaluate(
            pack,
            scenario_id,
            system_name,
            application,
            dir_code,
            app_warning=app_check.warning,
        )
        if result.get("phase") == "evaluation":
            md_path = _write_markdown_artifact(result, py_root=py_root)
            artifacts = dict(result.get("artifacts") or {})
            if md_path:
                artifacts["markdown_path"] = str(md_path)
            try:
                self.status("Writing PDF evaluation report…")
                pdf_path = _write_pdf_artifact(result)
                if pdf_path:
                    artifacts["pdf_path"] = str(pdf_path.resolve())
            except Exception as exc:
                self.status(f"PDF export skipped ({exc})")
            result["artifacts"] = artifacts
            result["pptx_prompt"] = "Would you like a presentation-ready PPTX file? Reply pptx or y."
        return result

    def _dir_requirements(
        self,
        pack: KnowledgePack,
        scenario_id: str,
        system_name: str,
        application: str,
        *,
        warning: str = "",
        validation_error: str = "",
        suggested_correction: str = "",
    ) -> Dict[str, Any]:
        self.status(f"Preparing design input requirements for {system_name}…")
        scenario = pack.scenario(scenario_id)
        requirements = scenario.get("requirements") or []
        entries = pack.common_code_entries(scenario_id)
        codes = [e["code"] for e in entries]
        example = codes[0] if codes else "1-1-1"
        out: Dict[str, Any] = {
            "phase": "dir_requirements",
            "system_name": system_name,
            "application": application,
            "knowledge_pack": pack.pack_id,
            "scenario_id": scenario_id,
            "requirements": requirements,
            "common_codes": codes,
            "common_code_details": entries,
            "message": (
                f"For {system_name}, I’ll assume {application} unless you specify otherwise. "
                f"Reply with a hyphen-separated DIR code (e.g. {example})."
            ),
        }
        if warning:
            out["sme_warnings"] = [warning]
        if validation_error:
            out["validation_error"] = validation_error
            out["suggested_correction"] = suggested_correction or (codes[0] if codes else "")
        return out

    def _evaluate(
        self,
        pack: KnowledgePack,
        scenario_id: str,
        system_name: str,
        application: str,
        dir_code: str,
        *,
        app_warning: str = "",
    ) -> Dict[str, Any]:
        scenario = pack.scenario(scenario_id)
        requirements = scenario.get("requirements") or []
        dir_check = validate_dir_code(pack, scenario_id, dir_code)
        if not dir_check.ok:
            return self._dir_requirements(
                pack,
                scenario_id,
                system_name,
                application,
                warning=app_warning,
                validation_error=dir_check.error,
                suggested_correction=dir_check.suggested_correction,
            )

        self.status(f"Validated DIR: {dir_code}")
        self.status("Searching industrial references…")

        queries = _dir_aware_queries(
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

        headings = pack.required_report_headings()
        heading_block = ", ".join(headings) if headings else "(see EVALUATION_PROMPT)"

        self.status(f"Generating {pack.equipment_system} technology evaluation…")
        depth_block = pack.fragment("depth_requirements")
        user_prompt = (
            f"System: {system_name}\n"
            f"Application: {application}\n"
            f"Equipment system / pack: {pack.equipment_system} ({pack.pack_id})\n"
            f"Scenario: {scenario_id}\n"
            f"Validated DIR code: {dir_code}\n"
            f"Decoded DIR:\n{json.dumps(dir_check.decoded, indent=2)}\n\n"
            f"DIR requirement structure:\n{json.dumps(requirements, indent=2)}\n\n"
            f"SME equipment options catalog:\n{_option_catalog_block(pack)}\n\n"
            f"Required datasheet_markdown headings: {heading_block}\n\n"
            f"Depth requirements:\n{depth_block}\n\n"
            f"Industrial search references (snippets + page excerpts):\n"
            f"{search_context or '(no serper results — use engineering judgment)'}\n\n"
            f"{EVALUATION_PROMPT}"
        )
        system_prompt = pack.build_system_prompt()
        raw = self.call_openai_json(system=system_prompt, user=user_prompt)
        raw = self._normalize_raw(raw, pack, system_name)

        # Soft-check option names
        names: List[str] = []
        if raw.get("selected_model"):
            names.append(str(raw["selected_model"]))
        for opt in raw.get("mixing_options") or []:
            if isinstance(opt, dict) and opt.get("name"):
                names.append(str(opt["name"]))
        opt_check = check_equipment_option_names(pack, names)

        allowed_fit = set(
            (pack.validation_rules.get("fit_enum") or {}).get("allowed")
            or ["best", "strong", "conditional", "limited", "add-on", "special-case"]
        )
        # Expand allowed fits used by GPT sample
        allowed_fit |= {"add-on", "special-case", "addon", "special_case"}
        for opt in raw.get("mixing_options") or []:
            if isinstance(opt, dict) and opt.get("fit") not in allowed_fit:
                fit = str(opt.get("fit") or "").lower().replace("_", "-")
                opt["fit"] = fit if fit in allowed_fit else "conditional"

        # Repair missing headings and/or thin sections once if needed
        md_text = str(raw.get("datasheet_markdown") or "")
        missing = missing_report_headings(md_text, headings)
        thin = thin_report_sections(md_text, headings, min_chars=120)
        if missing or thin:
            self.status("Repairing evaluation report depth/sections…")
            repair_user = (
                f"The previous JSON evaluation needs a deeper datasheet_markdown.\n"
                f"Missing headings: {missing or 'none'}.\n"
                f"Thin sections (expand to substantive multi-sentence engineering content): "
                f"{thin or 'none'}.\n"
                f"Also ensure failure_modes has >=3 items, each mixing_options entry meets the "
                f"depth bar, and weave search citations (title + URL) into rationale and markdown.\n"
                f"Return the FULL corrected JSON object (same schema) with a complete "
                f"datasheet_markdown that includes ALL required headings: {heading_block}.\n\n"
                f"Industrial search references:\n{search_context[:20000]}\n\n"
                f"Previous JSON:\n{json.dumps(raw)[:120000]}"
            )
            try:
                repaired = self.call_openai_json(system=system_prompt, user=repair_user)
                repaired = self._normalize_raw(repaired, pack, system_name)
                raw = repaired
            except Exception:
                # Keep original if repair fails
                pass

        validated = validate_output(raw)
        result = validated.model_dump()
        result["phase"] = "evaluation"
        result["dir_code"] = dir_code
        result["system_name"] = system_name
        result["application"] = application
        result["knowledge_pack"] = pack.pack_id
        result["scenario_id"] = scenario_id
        result["decoded_dir"] = dir_check.decoded
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
        # Coerce list-ish fields
        for key in ("objectives", "failure_modes", "do_not_specify", "preliminary_specs", "manufacturers"):
            if isinstance(raw.get(key), str):
                raw[key] = [raw[key]]
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
                "mixing_options": evaluation.get("mixing_options"),
                "evaluation_matrix": evaluation.get("evaluation_matrix"),
                "preliminary_specs": evaluation.get("preliminary_specs"),
                "manufacturers": evaluation.get("manufacturers"),
                "do_not_specify": evaluation.get("do_not_specify"),
                "source_basis": evaluation.get("source_basis"),
                "key_specs": evaluation.get("key_specs"),
                # Full report — preserve failure modes, decision logic, vendor lines
                "datasheet_markdown": evaluation.get("datasheet_markdown") or "",
            }
            raw = self.call_openai_json(
                system=(
                    pack.fragment("role")
                    + "\n\nYou prepare presentation-ready engineering slide content. "
                    "Keep visual density high and wording concise. "
                    "Ground every claim in the evaluation JSON and datasheet_markdown; "
                    "do not invent unsupported claims."
                ),
                user=(
                    PPTX_SLIDE_PACK_PROMPT
                    + "\n\nEvaluation JSON (includes full datasheet_markdown):\n"
                    + json.dumps(compact, ensure_ascii=False)[:180000]
                ),
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
