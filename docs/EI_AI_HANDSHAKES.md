# EI AI Handshakes (LLM + web search)

Status: **beta** (`equipment_evaluator`)  
Audience: SME creators authoring knowledge packs  
Related: [EI_CREATOR_EXTENSIONS.md](./EI_CREATOR_EXTENSIONS.md) · [EI_HANDSHAKE.md](./EI_HANDSHAKE.md)

This is the inventory of **every AI call** the template makes: when it runs, why,
and which pack keys the SME owns. Look for `# AI_HANDSHAKE: <id>` in
`py/apps/_templates/equipment_evaluator/agent.py`.

## Ownership split

| Owned by SME (knowledge pack) | Owned by template / platform |
|-------------------------------|------------------------------|
| Expert voice (`prompt_fragments.yaml` → `fragments`) | JSON output contracts (`equipment_selector_v1`, DIR menu JSON shape, PPTX slide schema) |
| Per-call instructions (`prompt_fragments.yaml` → `calls`) | Wire protocol `ei_handshake_v1` / UI SSE |
| Search strategy (`search_queries.yaml`) | Excerpt fetch plumbing after Serper |

Do **not** put schema field lists into pack YAML — keep those as template contracts
so the hub stays compatible.

## Inventory

| ID | When | Why | Channel | SME dial |
|----|------|-----|---------|----------|
| `pack_bootstrap` | Missing pack YAML on first local/portal draft | Author draft pack files | LLM | `calls.pack_bootstrap.system` (optional; authoring-time) |
| `dir_search` | DIR catalog miss / `generate_dir` | Research before questionnaire | Serper | `search_queries.yaml` → `dir_generate.templates` |
| `dir_generate` | DIR catalog miss / `generate_dir` | Author DIR questionnaire JSON | LLM | `calls.dir_generate.system` + `calls.dir_generate.instructions` |
| `evaluate_search` | Valid DIR → evaluate | Industrial references | Serper | `search_queries.yaml` → `evaluate.*` |
| `evaluate` | Valid DIR → evaluate | Full `equipment_selector_v1` | LLM | `fragments.*` (system) + `calls.evaluate.user_instructions` |
| `evaluate_repair` | Thin/missing report headings after evaluate | Deepen `datasheet_markdown` | LLM | Same system as evaluate + `calls.evaluate_repair.instructions` |
| `pptx` | `deliverable=pptx` / phase pptx | Slide pack JSON | LLM | `calls.pptx.system_extra` + `calls.pptx.instructions` (+ `fragments.role` fallback) |

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
  evaluate:
    user_instructions: >
      Extra SME text appended in the evaluate user message (before schema contract).
  evaluate_repair:
    instructions: >
      Preamble for the repair pass when sections are thin/missing.
  pptx:
    system_extra: >
      System add-on after role (or replaces default slide wording).
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

```text
run()
  ├─ (optional) pack_bootstrap LLM          ← authoring drafts
  ├─ resolve DIR menu
  │    └─ miss → dir_search (Serper) → dir_generate (LLM)
  ├─ no dir_code → return dir_requirements (no LLM)
  ├─ evaluate_search (Serper) → excerpts
  ├─ evaluate (LLM)  system=build_system_prompt()
  ├─ maybe evaluate_repair (LLM)
  └─ pptx (LLM) when requested
```

## SME checklist

1. Edit `fragments` for evaluate/repair **system** voice.
2. Edit `calls.*` for DIR generate, evaluate extras, repair, PPTX, bootstrap.
3. Edit `search_queries.yaml` so Serper matches **your** equipment system (do not
   leave mixing vendor strings in a filtration pack).
4. Keep `report_outline.yaml` / options / DIR catalogs aligned with the report
   the evaluate call must produce.
5. Local test: `python py/tools/local_chat.py --app <id>`.

## Cursor wizard

When customizing prompts or search, follow
`.cursor/skills/ei-creator-wizard/` and this inventory — prefer pack YAML over
editing hard-coded schema contracts in `agent.py`.
