"""Prompts for the Agitator Duty & Impeller Matcher (Life Science Mixing Systems Expert)."""

SYSTEM_PROMPT = """You are a senior process design engineer specializing in production-scale life-science mixing systems.

Evaluate mixing technologies for life-science manufacturing applications, including biologics, small molecule, animal health, vaccine, diagnostic, reagent, nutraceutical, and industrial biotech.

Consider all realistic approaches: agitated vessels, impellers, top/bottom/side-entry agitators, magnetic/single-use mixers, inline static/dynamic mixers, loop, jet and eductor mixing, powder induction/wetting, high-shear/rotor-stator mixers, homogenizers when used for mixing, slurry, gas-liquid, solids suspension, low-shear, and hygienic/aseptic systems.

Do not assume the answer must be an in-tank agitator. Do not give detailed recommendations for non-mixing topics except where they directly affect the mixing evaluation.

Prepare a professional preliminary design option evaluation using a minimum-viable DIR workflow. Evaluate realistic industry-used mixing options first, then recommend a basis of design when justified. Consider technical fit, process performance, GMP suitability, cleanability, scale-up risk, cost, schedule, vendor availability, reliability, quality, and implementation complexity.

Communicate in a simplified list style: agitator types, industrial applications, pros and cons for each, and manufacturers. Keep responses clear, concise, and professional.

When producing structured JSON output, follow equipment_selector_v1 exactly."""

DIR_PROMPT = """The user is evaluating a mixing system. Return JSON with this shape:
{
  "phase": "dir_requirements",
  "system_name": "<system name>",
  "application": "<application>",
  "requirements": [
    {
      "index": 1,
      "label": "Working volume",
      "options": [{"index": 1, "text": "..."}, ...]
    }
  ],
  "common_codes": ["2-1-2-3-1-1", "..."],
  "message": "Ask user to reply with hyphen-separated DIR code"
}

Provide 5-6 requirement lines with 4-7 options each, tailored to the system_name. Include 2-3 common starting DIR codes."""

EVALUATION_PROMPT = """Run a full mixing technology evaluation for the validated DIR code.

Return JSON matching equipment_selector_v1:
{
  "schema_version": "equipment_selector_v1",
  "equipment_tag": "AG-101 or MX-101 style tag",
  "selected_model": "Recommended basis of design (generic type, not a single SKU)",
  "equipment_system": "mixing",
  "equipment_name": "Descriptive equipment name",
  "equipment_category": "Mixing",
  "key_specs": [{"key": "power_kw", "value": 15, "unit": "kW"}, ...],
  "rationale": "Why this is the recommended basis",
  "creator_attribution": {"display_name": "BPEAI", "app_id": "agitator_duty_impeller_matcher"},
  "datasheet_markdown": "Markdown report resembling the evaluation PDF",
  "source_basis": ["user_inputs", "serper_search", "industry_references"],
  "mixing_options": [
    {
      "name": "Top-entry low-shear axial hydrofoil agitator",
      "fit": "best|strong|conditional|limited",
      "pros": ["..."],
      "cons": ["..."],
      "manufacturers": ["SPX FLOW Lightnin", "..."]
    }
  ],
  "recommended_basis": "One-line recommendation",
  "manufacturers": ["..."]
}

List strong-fit mixing types first, then pros/cons and manufacturers for each. Mark one option as recommended basis."""

# DIR templates keyed by normalized system name fragment
DIR_TEMPLATES: dict[str, list[dict]] = {
    "media preparation": [
        {"index": 1, "label": "Working volume", "options": [
            {"index": 1, "text": "50–250 L"}, {"index": 2, "text": "250–1,000 L"},
            {"index": 3, "text": "1,000–5,000 L"}, {"index": 4, "text": "5,000–15,000 L"},
            {"index": 5, "text": "> 15,000 L"},
        ]},
        {"index": 2, "label": "Vessel format", "options": [
            {"index": 1, "text": "Stainless fixed CIP/SIP vessel"},
            {"index": 2, "text": "Stainless portable vessel"},
            {"index": 3, "text": "Single-use mixer / bag system"},
            {"index": 4, "text": "Hybrid stainless + single-use fluid path"},
            {"index": 5, "text": "Inline / batch-loop preparation"},
        ]},
        {"index": 3, "label": "Media type / solids challenge", "options": [
            {"index": 1, "text": "Mostly liquid concentrates, low solids"},
            {"index": 2, "text": "Dry powder media, readily soluble"},
            {"index": 3, "text": "Difficult wetting or floating solids"},
            {"index": 4, "text": "High-salt / high-osmolality media"},
            {"index": 5, "text": "Shear/foam-sensitive components"},
            {"index": 6, "text": "Slurry-like or poorly soluble components"},
        ]},
        {"index": 4, "label": "Sterility / bioburden control", "options": [
            {"index": 1, "text": "Non-sterile prep followed by filtration"},
            {"index": 2, "text": "Low-bioburden closed processing"},
            {"index": 3, "text": "CIP/SIP hygienic stainless system"},
            {"index": 4, "text": "Single-use closed system"},
            {"index": 5, "text": "Aseptic additions / sterile hold"},
        ]},
        {"index": 5, "label": "Primary mixing objective", "options": [
            {"index": 1, "text": "Dissolve dry media powder"},
            {"index": 2, "text": "Blend liquid concentrates"},
            {"index": 3, "text": "Wet and disperse powders rapidly"},
            {"index": 4, "text": "Maintain homogeneity during transfer"},
            {"index": 5, "text": "Minimize foam and air entrainment"},
            {"index": 6, "text": "Fast batch turnaround"},
        ]},
        {"index": 6, "label": "Powder addition method", "options": [
            {"index": 1, "text": "Manual top-charge"},
            {"index": 2, "text": "Bag dump / charging port"},
            {"index": 3, "text": "Powder transfer system"},
            {"index": 4, "text": "Inline powder induction / eductor"},
            {"index": 5, "text": "Pre-slurry or concentrate addition"},
            {"index": 6, "text": "Not applicable, liquid-only"},
        ]},
    ],
    "chromatography resin slurry": [
        {"index": 1, "label": "Working volume", "options": [
            {"index": 1, "text": "50–250 L"}, {"index": 2, "text": "250–1,000 L"},
            {"index": 3, "text": "1,000–5,000 L"}, {"index": 4, "text": "> 5,000 L"},
        ]},
        {"index": 2, "label": "Vessel format", "options": [
            {"index": 1, "text": "Stainless fixed CIP/SIP slurry tank"},
            {"index": 2, "text": "Single-use slurry preparation"},
            {"index": 3, "text": "Portable stainless vessel"},
        ]},
        {"index": 3, "label": "Resin / solids challenge", "options": [
            {"index": 1, "text": "Standard chromatography resin slurry"},
            {"index": 2, "text": "High-density resin, settling risk"},
            {"index": 3, "text": "Shear-sensitive resin"},
        ]},
        {"index": 4, "label": "Primary mixing objective", "options": [
            {"index": 1, "text": "Maintain uniform resin suspension"},
            {"index": 2, "text": "Minimize resin damage / fines"},
            {"index": 3, "text": "Rapid homogenization before transfer"},
        ]},
        {"index": 5, "label": "Hold / transfer requirement", "options": [
            {"index": 1, "text": "Batch hold with intermittent mixing"},
            {"index": 2, "text": "Continuous low-shear suspension"},
            {"index": 3, "text": "Transfer to column packing skid"},
        ]},
    ],
}

COMMON_DIR_CODES = {
    "media preparation": ["2-1-2-3-1-1", "3-1-3-3-3-4", "2-3-2-4-1-1"],
    "chromatography resin slurry": ["2-1-1-3-1-1", "2-2-1-3-2-1"],
}
