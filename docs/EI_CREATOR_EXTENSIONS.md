# EI Creator Extensions Guide

Status: **beta** (equipment_evaluator)  
Repo: `bpeai-creator-apps` (creators do **not** edit the website / hub UI)  
Related: [EI_HANDSHAKE.md](./EI_HANDSHAKE.md) · [EI_APP_TEMPLATE_DESIGN.md](./EI_APP_TEMPLATE_DESIGN.md)

This doc is the source of truth for **what creators may customize**, how those
changes reach the generic web UI, and what stays platform-owned.

Look for **`HANDSHAKE:`** comments in
`py/apps/_templates/equipment_evaluator/` — they mark UI-visible boundaries.

---

## Three layers (do not collapse them)

| Layer | You customize | Lives in |
|-------|---------------|----------|
| **Template family** | Deliverable phases + output schema contract | `py/apps/_templates/<family>/` → copy to `py/apps/<your_id>/` |
| **Knowledge pack** | SME voice, DIR menus, options, report shape | `py/knowledge/<pack_id>/` (local) → portal Knowledge / zip |
| **SDK** | Shared helpers only — **do not fork** | `py/libs/bpeai_creator_sdk/` |

**Rule:** If SMEs would debate a list in a meeting, put it in the pack (YAML),
not in a hard-coded prompt string in `agent.py`.

---

## 1. Prompt + search dial (prefer pack YAML)

**Full inventory** (when / why / which keys): [EI_AI_HANDSHAKES.md](./EI_AI_HANDSHAKES.md).

### Evaluate system voice — `prompt_fragments.yaml` → `fragments`

| Key | Role |
|-----|------|
| `role` | Who the expert is |
| `scope` | Domain / equipment boundary |
| `application_default` | Default industry / application wording |
| `evaluation_goals` | What “good” evaluation means |
| `workflow` | How to reason through DIR → options |
| `output_style` | Tone and prose style |
| `depth_requirements` | Minimum section depth |
| `response_outline` | Structural expectations for the report |
| `exclusions_rule` | What belongs in `do_not_specify` |

Assembled by `KnowledgePack.build_system_prompt()`. Optional pack meta
`prompt_hooks.emphasize` (list) is appended as “SME emphasis”.

### Per-call instructions — `prompt_fragments.yaml` → `calls`

SME-owned system/instruction text for `dir_generate`, `evaluate`,
`evaluate_repair`, `pptx`, `pack_bootstrap`. See AI handshakes doc for keys.

### Web search — `search_queries.yaml`

Serper query templates + static domain/vendor queries for `dir_generate` and
`evaluate` phases. Non-mixing packs **must** replace mixing-oriented static
queries.

**Safe path:** edit `fragments`, `calls`, and `search_queries.yaml`.  
**Template owns** JSON schema contracts in `agent.py` (`EVALUATION_PROMPT` /
DIR / PPTX shape strings) — do not fork those unless changing the deliverable
contract. Tag: `# AI_HANDSHAKE: <id>`.

Model / provider: portal App Settings and/or local env
(`CREATOR_LLM_PROVIDER`, `CREATOR_LLM_MODEL`, provider API keys). Not a pack file.

---

## 2. Output dial (shape content inside the schema)

Hub / portal expect **`equipment_selector_v1`**. You shape *content*, not a new
schema version.

| Pack file | Effect |
|-----------|--------|
| `report_outline.yaml` | Required headings → `datasheet_markdown` structure |
| `equipment_options.yaml` | Allowed technology / option catalog |
| `validation_rules.yaml` | Hard/soft DIR and field checks |
| `dir_requirements.yaml` | DIR menus / questionnaires (`dir_menus[]`) |
| `pptx_outline.yaml` | Slide structure for local / optional PPTX |

Canonical options field in results: **`evaluation_options`**
(alias `mixing_options` for compatibility). Prefer `evaluation_options`.

**Do not** invent new hub-only schema fields or bump `output_schema_version`
without a platform release that dual-reads the new version.

---

## 3. Handshake contract (UI ↔ Python)

Full wire protocol: [EI_HANDSHAKE.md](./EI_HANDSHAKE.md) (`ei_handshake_v1`).

### Manifest links (must stay coherent)

| Field | Role |
|-------|------|
| `id` | Stable app id = folder name = `app_id` |
| `slug` | Hub URL segment |
| `equipment_system` | Taxonomy / routing |
| `knowledge_pack` | Pack folder / bound private pack |
| `python_entrypoint` | `apps.<id>.agent` |
| `required_inputs` | UI + validation keys (e.g. `system_name`) |
| `output_schema_version` | `equipment_selector_v1` |
| `handshake_protocol` | `ei_handshake_v1` (optional; platform defaults) |

### Phases creators may use

| Phase / trigger | Meaning |
|-----------------|---------|
| `dir` / `dir_requirements` / no `dir_code` | Return DIR questionnaire |
| `evaluate` / valid `dir_code` | Return evaluation result |
| `pptx` / `deliverable=pptx` | Attach / build PPTX from evaluation |
| `generate_dir` | Force DIR catalog generate/persist |

### SSE events the generic UI understands

| Event | Meaning |
|-------|---------|
| `heartbeat` | Keepalive |
| `status` | Progress line from `self.status("…")` |
| `dir_requirements` | Questionnaire JSON ready |
| `evaluation` / `result` | Evaluation or phase payload |
| `error` | Fatal |
| `done` | Terminal |

Platform injects `knowledge_pack_payload` and LLM overrides — never trust the
client for those.

**Do not** invent new SSE event names expecting the hub to render them.
Custom UI chrome requires a **platform** change.

---

## 4. Web UI capability matrix

Creators ship Python + packs. The beta hub uses the generic
`CreatorAppRunner` (BPEAI website). You **cannot** edit that React code.

| UI capability | Template support today | Creator action |
|---------------|------------------------|----------------|
| Run DIR questionnaire | Yes (`phase: dir`) | Customize via pack menus / generate |
| Enter DIR code + evaluate | Yes (`phase: evaluate`) | Pack prompts + options |
| Status progress lines | Yes (`status()` → SSE `status`) | Call `self.status(...)` from custom code |
| Download markdown report | Yes (`datasheet_markdown`) | Shape via outline / evaluation result |
| Generate PPTX | Partial (local + optional hub path) | Use SDK artifacts; do not invent new UI |
| Q&A / ask about app | UI may show chat entry | **Platform-owned** — do not assume custom chat tools appear |
| Insert into equipment list / project | Hub actions on evaluation result | Keep valid `equipment_selector_v1` |
| Custom buttons / panels / new SSE events | Not in generic runner | **Platform request** — unsupported for creators |
| Legacy custom UI (`MixingAgitatorMatcher`) | First-party only | Do not copy |

---

## 5. Optional Python tools / helpers

For creators comfortable with Python, add helpers next to your agent
(template ships `creator_tools.py` as an optional stub).

### Allowed patterns

1. Pure helpers in `creator_tools.py` (or similar) imported from `run()` /
   phase methods.
2. Use SDK: `self.call_llm_json`, `self.serper_search`, `self.status`,
   `validate_output`.
3. Post-process validated `equipment_selector_v1` fields **before** return
   (still must validate).
4. Stay inside existing phases and known result shapes.

### Forbidden / unsupported

- Editing hub, portal, or `CreatorAppRunner` React.
- New SSE events or phases the generic UI does not handle.
- Forking `bpeai_creator_sdk` instead of `git pull`.
- Binding platform seed packs at runtime (clone into a **private** pack).
- Committing `.env`, secrets, `artifacts/`, or treating gitignored apps as
  platform seeds.

### HANDSHAKE comment convention

In template / app Python, mark UI-visible boundaries:

```python
# HANDSHAKE: phase dispatch — UI sends phase / dir_code / deliverable
# HANDSHAKE: status() → SSE "status"
# HANDSHAKE: return phase=dir_requirements → SSE dir_requirements
# HANDSHAKE: return phase=evaluation + equipment_selector_v1 → SSE evaluation/result
```

---

## 6. Recommended customization order

1. Copy `equipment_evaluator` → `py/apps/<your_id>/` (or use the Cursor wizard).
2. Set identity in `agent.py` + `manifest.json`.
3. Author / bind a private knowledge pack (prompts + catalogs + outlines).
4. Local test: `python py/tools/local_chat.py --app <your_id>`.
5. Optionally add `creator_tools.py` helpers inside existing phases.
6. Upload → portal Test → Submit → admin Publish.

Primary onboarding path: open this repo in **Cursor** → Agent chat →
“Create my EI app” (see [AGENTS.md](../AGENTS.md) and `.cursor/skills/ei-creator-wizard/`).
