from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Sequence


def format_dir_text(result: Mapping[str, Any]) -> str:
    """Render a DIR questionnaire phase for local chat."""
    lines: list[str] = []
    system = result.get("system_name") or "—"
    application = result.get("application") or "—"
    lines.append("Design Input Requirements")
    lines.append("─" * 40)
    lines.append(f"System:      {system}")
    lines.append(f"Application: {application}")

    err = (result.get("validation_error") or "").strip()
    if err:
        lines.append("")
        lines.append(f"Validation:  {err}")
        suggested = result.get("suggested_correction")
        if suggested:
            lines.append(f"Try code:   {suggested}")

    message = (result.get("message") or "").strip()
    if message:
        lines.append("")
        lines.append(message)

    requirements = result.get("requirements") or []
    if isinstance(requirements, list) and requirements:
        lines.append("")
        lines.append(f"Design Input Requirements — {system}")
        lines.append("─" * 40)
        for req in requirements:
            if not isinstance(req, Mapping):
                continue
            idx = req.get("index") or "?"
            label = req.get("label") or "Requirement"
            lines.append(f"{idx}. {label}")
            for opt in req.get("options") or []:
                if not isinstance(opt, Mapping):
                    continue
                oidx = opt.get("index") or "?"
                text = opt.get("text") or ""
                lines.append(f"   {oidx}) {text}")

    details = result.get("common_code_details") or []
    codes = result.get("common_codes") or []
    lines.append("")
    lines.append("Common starting DIR codes")
    lines.append("─" * 40)
    if isinstance(details, list) and details:
        for entry in details:
            if not isinstance(entry, Mapping):
                continue
            code = entry.get("code") or ""
            caption = (entry.get("caption") or "").strip()
            lines.append(f"  • {code}")
            if caption:
                lines.append(f"    {caption}")
    elif isinstance(codes, list):
        for code in codes:
            lines.append(f"  • {code}")

    lines.append("")
    lines.append("Reply with the closest code to evaluate realistic mixing options.")
    return "\n".join(lines).rstrip() + "\n"


def _listish(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if value:
        return [str(value)]
    return []


def format_selector_text(result: Mapping[str, Any]) -> str:
    """Render GPT-parity evaluation as readable terminal text."""
    lines: list[str] = []
    tag = result.get("equipment_tag") or ""
    model = result.get("selected_model") or ""
    system = result.get("system_name") or result.get("equipment_name") or "—"
    application = result.get("application") or ""
    dir_code = result.get("dir_code") or ""
    name = result.get("equipment_name") or ""
    category = result.get("equipment_category") or ""

    lines.append("Mixing technology evaluation")
    lines.append("─" * 40)
    if tag:
        lines.append(f"Tag:        {tag}")
    if model:
        lines.append(f"Model:      {model}")
    if name:
        lines.append(f"Name:       {name}")
    lines.append(f"System:     {system}")
    if category:
        lines.append(f"Category:   {category}")
    if application:
        lines.append(f"Application: {application}")
    if dir_code:
        lines.append(f"Validated DIR: {dir_code}")

    specs = result.get("key_specs") or []
    if specs and not result.get("mixing_options"):
        lines.append("")
        lines.append("Key specs")
        lines.append("─" * 40)
        for spec in specs:
            if not isinstance(spec, Mapping):
                continue
            key = spec.get("key") or "?"
            value = spec.get("value")
            unit = spec.get("unit")
            value_s = f"{value} {unit}".strip() if unit else str(value)
            lines.append(f"  • {key}: {value_s}")

    dir_summary = (result.get("dir_summary") or "").strip()
    if dir_summary:
        lines.append("")
        lines.append(dir_summary)

    design_basis = (result.get("design_basis") or "").strip()
    if design_basis:
        lines.append("")
        lines.append("Design basis")
        lines.append("─" * 40)
        lines.append(design_basis)

    options = result.get("mixing_options") or []
    if isinstance(options, list) and options:
        lines.append("")
        lines.append("Strong-fit mixing types")
        lines.append("─" * 40)
        for i, opt in enumerate(options, start=1):
            if not isinstance(opt, Mapping):
                continue
            name = opt.get("name") or "?"
            fit = opt.get("fit") or ""
            mark = " — recommended basis" if str(fit).lower() == "best" else ""
            lines.append(f"{i}. {name} ({fit}){mark}")

    recommended = (result.get("recommended_basis") or result.get("selected_model") or "").strip()
    if recommended:
        lines.append("")
        lines.append("Recommended basis of design")
        lines.append("─" * 40)
        lines.append(recommended)
    rationale = (result.get("rationale") or "").strip()
    if rationale:
        lines.append(rationale)

    alternate = (result.get("alternate_basis") or "").strip()
    if alternate:
        lines.append("")
        lines.append(f"Alternate: {alternate}")

    if isinstance(options, list) and options:
        lines.append("")
        lines.append("Option evaluation")
        lines.append("─" * 40)
        for opt in options:
            if not isinstance(opt, Mapping):
                continue
            lines.append(f"{opt.get('name') or '?'} — {opt.get('fit') or ''}")
            apps = opt.get("industrial_applications") or []
            if apps:
                lines.append("  Industrial applications: " + "; ".join(str(a) for a in apps))
            for label, key in (("Pros", "pros"), ("Cons / watchouts", "cons")):
                vals = opt.get(key) or []
                if vals:
                    lines.append(f"  {label}")
                    for v in vals:
                        lines.append(f"    • {v}")
            mfrs = opt.get("manufacturers") or []
            if mfrs:
                lines.append("  Manufacturers: " + ", ".join(str(m) for m in mfrs))
            lines.append("")

    exclusions = _listish(result.get("do_not_specify"))
    if exclusions:
        lines.append("Do not specify")
        lines.append("─" * 40)
        for item in exclusions:
            lines.append(f"  • {item}")

    specs = _listish(result.get("preliminary_specs"))
    if specs:
        lines.append("")
        lines.append("Preliminary specification")
        lines.append("─" * 40)
        for item in specs:
            lines.append(f"  • {item}")

    mfrs = _listish(result.get("manufacturers"))
    if mfrs:
        lines.append("")
        lines.append("Manufacturers: " + ", ".join(mfrs))

    attribution = result.get("creator_attribution") or {}
    if isinstance(attribution, Mapping) and attribution:
        display = attribution.get("display_name") or ""
        app_id = attribution.get("app_id") or ""
        lines.append("")
        lines.append(f"Attribution: {display} ({app_id})".strip())

    source = result.get("source_basis") or []
    if source and not result.get("mixing_options"):
        lines.append(f"Source basis: {', '.join(str(s) for s in source)}")

    artifacts = result.get("artifacts") or {}
    if isinstance(artifacts, Mapping):
        if artifacts.get("markdown_path"):
            lines.append("")
            lines.append(f"Markdown report: {artifacts['markdown_path']}")
        if artifacts.get("pptx_path"):
            lines.append(f"PPTX deck: {artifacts['pptx_path']}")

    prompt = (result.get("pptx_prompt") or "").strip()
    if prompt and not (isinstance(artifacts, Mapping) and artifacts.get("pptx_path")):
        lines.append("")
        lines.append(prompt)

    warnings = result.get("sme_warnings") or []
    if warnings:
        lines.append("")
        lines.append("SME warnings")
        lines.append("─" * 40)
        for w in warnings:
            lines.append(f"  • {w}")

    return "\n".join(lines).rstrip() + "\n"


def format_result_text(result: Mapping[str, Any]) -> str:
    """Format DIR or selector payloads for local chat."""
    phase = str(result.get("phase") or "").strip().lower()
    if phase in {"dir_requirements", "dir"} or (
        "requirements" in result and not result.get("schema_version")
    ):
        return format_dir_text(result)
    return format_selector_text(result)


def format_selector_json(result: Dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2) + "\n"
