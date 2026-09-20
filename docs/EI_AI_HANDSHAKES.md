# EI AI Handshakes (LLM + web search)

Status: **beta** (`equipment_evaluator`, `equipment_sizing`)  
Audience: SME creators authoring knowledge packs  
Related: [EI_CREATOR_EXTENSIONS.md](./EI_CREATOR_EXTENSIONS.md) · [EI_HANDSHAKE.md](./EI_HANDSHAKE.md)

This is the inventory of **every AI call** the template makes: when it runs, why,
and which pack keys the SME owns. Look for `# AI_HANDSHAKE: <id>` in
`py/apps/_templates/equipment_evaluator/agent.py` and
`py/apps/_templates/equipment_sizing/agent.py`.

## Ownership split

| Owned by SME (knowledge pack) | Owned by template / platform |
|-------------------------------|------------------------------|
| Expert voice (`prompt_fragments.yaml` → `fragments`) | JSON output contracts (`equipment_selector_v1`, DIR menu JSON shape, PPTX slide schema) |
| Per-call instructions (`prompt_fragments.yaml` → `calls`) | Wire protocol `ei_handshake_v1` / UI SSE |
| Search strategy (`search_queries.yaml`) | Excerpt fetch plumbing after Serper; creator-content retrieval from `references/content/` |

Do **not** put schema field lists into pack YAML — keep those as template contracts
so the hub stays compatible.

## Inventory

| ID | When | Why | Channel | SME dial |
|----|------|-----|---------|----------|
| `pack_bootstrap` | Missing pack YAML on first local/portal draft | Author draft pack files | LLM | `calls.pack_bootstrap.system` (optional; authoring-time) |
| `dir_search` | DIR catalog miss / `generate_dir` | Research before questionnaire | Serper | `search_queries.yaml` → `dir_generate.templates` |
| `creator_content` | DIR generate + evaluate | Supplemental SME PDFs/docs | Pack index | `references/content/` (does **not** replace Serper) |
| `dir_route` | Python catalog miss (`match_dir_menu`) | Reuse vs create **host** scenario | LLM | optional `calls.dir_route.system` / `instructions` (hints only; template owns the host-identity contract) |
| `dir_generate` | DIR catalog miss / `generate_dir` (after `dir_route` create) | Author DIR questionnaire JSON. Python passes a variant hint only when the typed host matched pack aliases or the caller supplied one — never `default_variant` for an unmatched host. | LLM | `calls.dir_generate.system` + `calls.dir_generate.instructions` |
| `evaluate_search` | Valid DIR → evaluate | Industrial references | Serper | `search_queries.yaml` → `evaluate.*` |
| `evaluate` | Valid DIR → evaluate | Full `equipment_selector_v1` | LLM | `fragments.*` (system) + `calls.evaluate.user_instructions` |
| `evaluate_repair` | Thin/missing report headings after evaluate | Deepen `datasheet_markdown` | LLM | Same system as evaluate + `calls.evaluate_repair.instructions` |
| `pptx` | `deliverable=pptx` / phase pptx | Slide pack JSON | LLM | `calls.pptx.system_extra` + `calls.pptx.instructions` (+ `fragments.role` fallback) |
| `sizing_plan` | Valid DIR, before sizing LLMs | Decide capacity/connection inputs vs DIR | LLM | `calls.sizing_plan.*` |
| `sizing_search` | After plan, when sizing proceeds | Vendor/catalog envelope references | Serper | `search_queries.yaml` → `sizing.*` (falls back to `evaluate.*`) |
| `sizing_capacity` | After plan | Capacity JSON | LLM | `calls.sizing_capacity.*` |
| `sizing_connections` | After capacity | Connection JSON for **this sized item** | LLM | `calls.sizing_connections.*` |
| `sizing_dimensions` | After connections | Envelope JSON | LLM | `calls.sizing_dimensions.*` |
| `sizing_report` | After capacity / connections / envelope | Datasheet markdown + `key_specs` + `excel_ready_table` | LLM | `calls.sizing_report.*` |
| `sizing_repair` | Thin/missing sizing headings after report | Deepen `datasheet_markdown` | LLM | Same system as `sizing_report` + `calls.sizing_repair.instructions` |

Post-search excerpt fetch (`enrich_search_hits_with_excerpts`) is **not** an SME
prompt dial — it only expands Serper hits for the LLM user message.

## Pack files

### `prompt_fragments.yaml`

```yaml
fragments:
  role: …
  scope: …
  # … used by KnowledgePack.build_system_prompt() for evaluate / repair system

calls:
  dir_generate:
    system: >
      System prompt for DIR questionnaire generation.
    instructions: >
      SME guidance (domain emphasis). Template appends the JSON schema contract.
      Ask for ONE menu JSON with a top-level requirements[] array — not
      dir_requirements.yaml and not a dir_menus wrapper.
  dir_route:
    system: >
      Optional domain voice for reuse vs create. Template appends the
      host-identity contract (package vs qualified component vs standalone
      duty item vs synonym).
    instructions: >
      Optional pack illustrations of the template policy (example host names).
      Do not replace the template reuse/create rules with CIP-only ids.
  evaluate:
    user_instructions: >
      Extra SME text appended in the evaluate user message (before schema contract).
      Evaluator family only — do not emit on sizing packs.
  evaluate_repair:
    instructions: >
      Preamble for the repair pass when sections are thin/missing.
      Evaluator family only.
  sizing_plan:
    system: >
      Decide which capacity/connection inputs are still needed.
    instructions: >
      Prefer DIR answers; only request extra material-balance inputs when needed.
  sizing_capacity:
    system: >
      Size capacity from DIR. Return ONLY JSON.
    instructions: >
      Domain method (working volume, flow, membrane area, column volume, …).
  sizing_connections:
    system: >
      Size interfaces that belong to pack.yaml sized_item.
    instructions: >
      Do not size unrelated host nozzles unless this pack says so.
  sizing_dimensions:
    system: >
      Estimate overall envelope from vendor catalogs when possible.
  sizing_report:
    system: >
      Draft the sizing datasheet from capacity/connections/envelope JSON.
    instructions: >
      Required headings plus Item|Method/formula|Result|Unit|Basis table.
  sizing_repair:
    instructions: >
      Restore missing or thin sizing headings without changing supported numbers.
  pptx:
    system_extra: >
      System add-on after role (or replaces default slide wording).
      Sizing decks must include numerical results from the sizing JSON.
    instructions: >
      Optional domain emphasis for slides.
  pack_bootstrap:
    system: >
      Optional override when LLM-drafting missing pack YAML files.
```

### `search_queries.yaml`

```yaml
dir_generate:
  templates:
    - "{system_name} {equipment_system} design requirements {application}"

evaluate:
  templates:
    - "{system_name} {equipment_system} {application} {working_volume}"
  slots:
    working_volume: ["working volume"]
    vessel_format: ["vessel", "format", "tank"]
  static:
    - "domain or vendor discovery query (SME-owned)"

sizing:
  templates:
    - "{system_name} {working_volume} sanitary dimensions catalog {application}"
  slots:
    working_volume: ["working volume"]
  static:
    - "domain or vendor envelope query (SME-owned)"
```

**Placeholders** (string `.format` / safe substitute):

| Key | Source |
|-----|--------|
| `system_name`, `application`, `equipment_system` | Run inputs / pack |
| Slot names (`working_volume`, …) | Decoded DIR labels matched via `evaluate.slots` substrings |

Missing file or empty section → **domain-neutral template fallbacks** in the SDK
(no vendor brand names). Put vendor/product-line discovery queries in pack
`evaluate.static`.

## Flow (runtime)

Evaluator family (`equipment_evaluator`):

```text
run()
  ├─ (optional) pack_bootstrap LLM          ← authoring drafts
  ├─ resolve DIR menu
  │    ├─ Python match_dir_menu (strict keywords + aliases)
  │    └─ miss → dir_route (LLM reuse vs create host scenario)
  │         reuse → existing catalog row
  │         create → dir_search (Serper) → dir_generate (LLM)
  ├─ no dir_code → return dir_requirements (no LLM)
  ├─ evaluate_search (Serper) → excerpts
  ├─ creator content retrieve (references/content index; supplemental)
  ├─ evaluate (LLM)  system=build_system_prompt()
  ├─ maybe evaluate_repair (LLM)
  └─ pptx (LLM) when requested
```

Sizing family (`equipment_sizing`):

```text
run()
  ├─ (optional) pack_bootstrap LLM          ← sizing-family draft YAML
  ├─ resolve DIR menu (same match-or-generate as evaluator)
  ├─ no dir_code → return dir_requirements (no LLM)
  ├─ sizing_plan (LLM)
  ├─ maybe sizing_inputs questionnaire
  ├─ sizing_search (Serper) → excerpts  (+ creator_content)
  ├─ sizing_capacity (LLM)
  ├─ sizing_connections (LLM)   ← sized item interfaces, not host nozzles
  ├─ sizing_dimensions (LLM)
  ├─ sizing_report (LLM)        → datasheet_markdown, key_specs, excel_ready_table
  ├─ maybe sizing_repair (LLM)
  ├─ Python artifacts: .md / .docx / .xlsx
  └─ pptx (LLM) when requested  ← numbers from sizing JSON allowed
```

## SME checklist

1. Edit `fragments` for evaluate/repair **or** sizing-report **system** voice.
2. Edit `calls.*` for the family you copied: evaluator uses `evaluate` /
   `evaluate_repair`; sizing uses `sizing_plan` / `sizing_capacity` /
   `sizing_connections` / `sizing_dimensions` / `sizing_report` / `sizing_repair`.
   Both families use DIR generate, optional DIR route, PPTX, and bootstrap.
3. Edit `search_queries.yaml` so Serper matches **your** equipment system (do not
   leave mixing vendor strings in a filtration pack). Sizing packs need
   `sizing.templates` (evaluate templates remain a fallback).
4. Keep `report_outline.yaml` / options / DIR catalogs aligned with the report
   the evaluate **or** sizing_report call must produce.
5. Optional: add SME PDFs/md/txt to `py/knowledge/<id>/references/content/` and re-run
   `local_chat` so they are indexed. Creator files **supplement** web search; they do
   not replace Serper.
6. Local test: `python py/tools/local_chat.py --app <id>`.

## Cursor wizard

When customizing prompts or search, follow
`.cursor/skills/ei-creator-wizard/` and this inventory — prefer pack YAML over
editing hard-coded schema contracts in `agent.py`.
