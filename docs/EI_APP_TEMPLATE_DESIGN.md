# EI App Template Architecture

Status: **hybrid knowledge packs** (2026-07-26)  
Owner: BPEAI platform / creator SDK  
Repos: `bpeai-creator-apps` (authoring) → mirror into main `bpeai` on deploy  
SDK version: see [`CREATOR_SDK_VERSION`](../CREATOR_SDK_VERSION) / [`CHANGELOG.md`](../CHANGELOG.md)

## Workspace guidance

| Repo | Keep in workspace? | Why |
|------|--------------------|-----|
| **bpeai-creator-apps** | **Yes — primary** | Templates, SDK, platform seed packs, local test tools |
| **bpeai** | **Yes — required** | Runtime (`vendor_api`), portal, Postgres knowledge packs, EI hub |
| **bpeai-workspace-app** | Optional | Desktop only; not on the critical path for template/SDK work |

Day-to-day edits for templates/SDK/seeds land first in **bpeai-creator-apps**, then mirror into **bpeai**. Creator-owned pack **content** is portal-managed (not git).

---

## Three-way split (locked)

| Layer | Responsibility | Lives in |
|-------|----------------|----------|
| **1. Template family** | Deliverable / output contract + run phases | `py/apps/_templates/<family>/` |
| **2. Knowledge pack** | Creator (or platform) SME content: DIR menus, options, prompts | Platform seeds: **bpeai** `py/knowledge/<id>/`; creator packs: Postgres (+ S3 snapshots); this repo: `_examples/` stubs only |
| **3. SDK** | Shared LLM helpers, pack loading, validation, artifacts | `py/libs/bpeai_creator_sdk/` |

**Rule:** If SMEs would debate a list in a meeting, it belongs in a knowledge pack (or shared `bpeai_taxonomy`), not buried in a prompt string.

### Ownership (locked)

- **Creator packs are private** to that creator’s EI apps only (not a marketplace).
- **Creator apps are 1:1 with a private pack of the same name** (`py/apps/<id>/` ↔ `py/knowledge/<id>/`).
- **Platform seeds** (e.g. `mixing`) are BPEAI-owned; first-party apps may share them. Creators **do not** bind seeds — they bootstrap a private pack named after the app.
- **Python agent code** ships via **portal zip upload** / `upload_creator_bundle.py` (primary). See [EI_HANDSHAKE.md](./EI_HANDSHAKE.md).

---

## Hybrid transfer

| Asset | Transfer |
|-------|----------|
| Python agent (`py/apps/<id>/`) | Portal zip / CLI → S3 + `creator_runtime` → `vendor_api` load by `app_id` |
| SDK + templates + platform seed YAML | git mirror creator-apps → bpeai (BPEAI deploy) |
| Creator knowledge pack + DIR menus | Upload zip / Portal API → Postgres (+ versioned S3 YAML snapshot) |
| Shared vocab | `bpeai_taxonomy` in bpeai (git) |
| Run wire protocol | `ei_handshake_v1` (SSE + durable `ei_runtime_runs`) |

---

## Template families (by deliverable)

| Family id | Primary hub deliverables | Output schema | Priority |
|-----------|--------------------------|---------------|----------|
| `equipment_evaluator` | Design option evaluation, Technology recommendation, DIR | `equipment_selector_v1` | **shipped** |
| `datasheet` | Equipment datasheet | `datasheet_v1` | P1 |
| `specification_urs` | Specification / URS | `urs_v1` / `spec_v1` | P1 |
| `pid` | P&ID / drawing package | `pid_v1` | P2 |
| `test_protocol` | Test / qualification protocol | `protocol_v1` | P2 |

Do **not** fork a new Python template per equipment system. Systems differ by **pack**, not by template family. Pack identity is **not** only `equipment_system` — packs also carry expertise keys, alignment category, and coverage scope.

**Local artifacts:** sectioned markdown + PDF + optional PPTX under `./artifacts/`.  
**Portal hub:** `datasheet_markdown` as S3 `.md` only (no PDF/PPTX upload in beta).

---

## Shared vs pack-local taxonomy

### Shared (`bpeai` → `bpeai_taxonomy`)

- `applications.yaml`, `preparations.yaml`, `equipment_items.yaml`, `regions.yaml`

SDK may load these when available and fall back gracefully for creator-only clones.

### Platform seed packs (`bpeai` deploy → `py/knowledge/<id>/`)

Canonical seeds live in the **website deploy repo**, not here:

- Production: `bpeai/py/knowledge/mixing/`
- Draft: `bpeai/py/knowledge/filtration/` (`approval_status: draft_pending_sme_approval`)

This authoring repo only ships **example stubs**: [`py/knowledge/_examples/`](../py/knowledge/_examples/).

| File | Purpose |
|------|---------|
| `pack.yaml` | Pack metadata: expertise, alignment, coverage, industries, aliases |
| `dir_requirements.yaml` | SME-readable **list catalog** `dir_menus[]` (legacy `menus`/`scenarios` accepted at load time only) |
| `dir_catalog.md` | Auto-generated Markdown review table for SMEs |
| `equipment_options.yaml` | Allowed technology / option catalog |
| `validation_rules.yaml` | Hard/soft rules for DIR codes and LLM field enums |
| `prompt_fragments.yaml` | Injectable SME guidance (`fragments` + optional `calls`) |
| `search_queries.yaml` | Serper query templates / static domain queries (optional; see [EI_AI_HANDSHAKES.md](./EI_AI_HANDSHAKES.md)) |
| `report_outline.yaml` / `pptx_outline.yaml` | Report / slide outlines |
| `references/content/*` | Optional creator SME PDFs/md/txt (LLM input; indexed to `content_index.yaml`) |
| `references/style/*.pptx` / `*.pdf` | Style shells (seeded from `py/knowledge/_templates/references/`) |

Creators manage private packs on the portal. If a pack is missing locally, the
`equipment_evaluator` template may LLM-bootstrap a draft under `py/knowledge/<id>/`
(SDK: `sme.pack_bootstrap`). Those creator packs are **gitignored** in this repo —
only `_examples/` stubs are committed.

Future systems: `heat_transfer/`, `chromatography/`, `fluid_transfer/`, `cell_culture/`, …

### DIR selection dimensions (match-or-generate)

A technology pack may hold **many** DIR questionnaires. SMEs cannot pre-author every
case; the template **reuses** a catalog hit or **generates** a new draft for the run.

Fingerprint:

`(equipment_system_variant × industry × scenario_id)` plus `system_name` / `application` aliases

Flow:

1. Lookup `dir_menus[]` (approved first, then prior `draft_generated` for same fingerprint)
2. On miss → Serper research + LLM questionnaire (5–8 requirements, numeric starter codes)
3. Append draft to the local pack catalog + refresh `dir_catalog.md`
4. Present DIR to the user; evaluate may use `draft_generated` for that local run
5. SME reviews the catalog and promotes `status: approved` for reuse

`common_codes` must be hyphen-separated numeric starters with captions (not tags like `SIP`).

Legacy packs without `dir_menus[]` still resolve via `menus[]` / `scenarios`.

---

## Equipment evaluator run model

Phases:

1. **`dir`** — match catalog or generate draft questionnaire (+ numeric common codes)
2. **`evaluate`** — validate DIR → Serper → structured LLM → soft checks → artifacts
3. **`pptx`** (local) — optional deck from evaluation JSON
4. **`generate_dir`** — force generate/persist a draft menu for the fingerprint

Inputs (minimum):

- `system_name` / scenario key
- `application` / `industry`
- `equipment_system_variant` (optional; aliases from system_name)
- `dir_code` (evaluate phase)
- `phase` (`dir` | `evaluate` | `pptx` | `generate_dir`)
- `knowledge_pack` (pack id / slug)

Creator apps copied from the template are local/gitignored; do not commit them.

---

## SDK modules

```text
bpeai_creator_sdk/
  sme/
    pack_loader.py   # filesystem + DB payload hydrate; resolve_dir_menu
    dir_catalog.py   # list catalog match/append + dir_catalog.md
    validate.py      # DIR + option + taxonomy soft checks
  ...
```

Manifest:

- optional `template_family` — deliverable contract family; legacy manifests default to `equipment_evaluator`
- `equipment_system` — portal / hub enum (taxonomy; not the pack name)
- `knowledge_pack` — must match `id` / `app_id` for creator apps
- `input_ports[]` / `output_ports[]` — typed workflow connections (`id`, `label`,
  `schema_ref`, short compatibility `data_type`, `required`, `cardinality`, `kind`)
- `required_inputs` remains supported; the SDK derives value input ports for old
  manifests that do not declare `input_ports`

### Generic result contract

New composition-aware runtimes may wrap template payloads in
`ei_result_manifest_v1`:

```json
{
  "schema_version": "ei_result_manifest_v1",
  "template_family": "equipment_evaluator",
  "run": {},
  "inputs": {},
  "result": { "schema_version": "equipment_selector_v1" },
  "outputs": [{
    "port_id": "equipment_selection",
    "label": "Equipment selection",
    "schema_ref": "https://bpeai.com/schemas/equipment-selector/v1",
    "value": { "schema_version": "equipment_selector_v1" }
  }],
  "artifacts": {}
}
```

`result` (and the typed output value when present) remains the complete
`equipment_selector_v1` payload. The SDK
`wrap_evaluator_result` / `unwrap_evaluator_result` adapters bridge wrapped and
bare results; `validate_output` accepts both. Existing agents may continue to
return bare payloads.

---

## How creators get updates

1. `git pull` on `bpeai-creator-apps` (SDK, templates, platform seeds).
2. Portal `/platform/sdk` shows `CREATOR_SDK_VERSION` + changelog excerpt.
3. Major SDK bumps: email to users with creator access.
4. See [`CHANGELOG.md`](../CHANGELOG.md) and [`CREATOR_PLAYBOOK.md`](../CREATOR_PLAYBOOK.md).
5. Creator customization dials + UI capability matrix: [`EI_CREATOR_EXTENSIONS.md`](./EI_CREATOR_EXTENSIONS.md).
6. Preferred onboarding: open this repo in Cursor → Agent → **Create my EI app** (`AGENTS.md` / `.cursor/skills/ei-creator-wizard`).

---

## Non-goals

- Desktop (`bpeai-workspace-app`) integration
- Cross-creator pack sharing / marketplace
- Replacing first-party `eq_list` / solids orchestrator
- Requiring creators to edit the website deploy repo to ship an app
