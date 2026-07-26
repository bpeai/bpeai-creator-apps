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
| **2. Knowledge pack** | Creator (or platform) SME content: DIR menus, options, prompts | Platform seeds: `py/knowledge/<id>/`; creator packs: Postgres (+ S3 snapshots) |
| **3. SDK** | Shared LLM helpers, pack loading, validation, artifacts | `py/libs/bpeai_creator_sdk/` |

**Rule:** If SMEs would debate a list in a meeting, it belongs in a knowledge pack (or shared `bpeai_taxonomy`), not buried in a prompt string.

### Ownership (locked)

- **Creator packs are private** to that creator’s EI apps only (not a marketplace).
- One creator may bind **one pack to many of their apps**.
- **Platform seeds** (e.g. `mixing`) are BPEAI-owned; creators may bind or **clone** into a private pack.
- **Python agent code** stays git PR only — no zip/S3 code upload.

---

## Hybrid transfer

| Asset | Transfer |
|-------|----------|
| Python agent (`py/apps/<id>/`) | git PR → BPEAI mirror → `vendor_api` rebuild |
| SDK + templates + platform seed YAML | git mirror creator-apps → bpeai |
| Creator knowledge pack + DIR menus | Portal API → Postgres (+ versioned S3 YAML snapshot) |
| Shared vocab | `bpeai_taxonomy` in bpeai (git) |

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

### Platform seed packs (`bpeai-creator-apps` → `py/knowledge/<id>/`)

**Production packs:** [`py/knowledge/mixing/`](../py/knowledge/mixing/).  
**Draft packs:** [`py/knowledge/filtration/`](../py/knowledge/filtration/) (`approval_status: draft_pending_sme_approval`).

| File | Purpose |
|------|---------|
| `pack.yaml` | Pack metadata: expertise, alignment, coverage, industries, aliases |
| `dir_requirements.yaml` | DIR menus keyed by **variant × industry × scenario** (+ legacy scenarios) |
| `equipment_options.yaml` | Allowed technology / option catalog |
| `validation_rules.yaml` | Hard/soft rules for DIR codes and LLM field enums |
| `prompt_fragments.yaml` | Injectable SME guidance |
| `report_outline.yaml` / `pptx_outline.yaml` | Report / slide outlines |
| `references/*.pptx` | Style stubs |

If a pack or any of the above components is missing at runtime, the
`equipment_evaluator` template LLM-bootstraps an initial draft (SDK:
`sme.pack_bootstrap`; agent: `_ensure_knowledge_pack`). Drafts are subject to
SME / platform approval before production use.

Future systems: `heat_transfer/`, `chromatography/`, `fluid_transfer/`, `cell_culture/`, …

### DIR selection dimensions

Runtime selects an approved menu with:

`(equipment_system_variant × industry × scenario_id)`

Inputs: `equipment_system_variant`, `industry` (or inferred from `application`), `system_name` → scenario aliases.

---

## Equipment evaluator run model

Phases:

1. **`dir`** — return approved DIR questionnaire (+ common codes)
2. **`evaluate`** — validate DIR → Serper → structured LLM → soft checks → artifacts
3. **`pptx`** (local) — optional deck from evaluation JSON
4. **`generate_dir`** (portal / authoring) — LLM draft menu → creator review → `APPROVED`

Inputs (minimum):

- `system_name` / scenario key
- `application` / `industry`
- `equipment_system_variant` (optional; aliases from system_name)
- `dir_code` (evaluate phase)
- `phase` (`dir` | `evaluate` | `pptx` | `generate_dir`)
- `knowledge_pack` (pack id / slug)

Production evaluate uses **APPROVED** menus only.

---

## SDK modules

```text
bpeai_creator_sdk/
  sme/
    pack_loader.py   # filesystem + DB payload hydrate; resolve_dir_menu
    validate.py      # DIR + option + taxonomy soft checks
  ...
```

Manifest:

- `equipment_system` — portal / hub enum
- optional `knowledge_pack` — defaults to `equipment_system` when omitted

---

## How creators get updates

1. `git pull` on `bpeai-creator-apps` (SDK, templates, platform seeds).
2. Portal `/platform/sdk` shows `CREATOR_SDK_VERSION` + changelog excerpt.
3. Major SDK bumps: email to users with creator access.
4. See [`CHANGELOG.md`](../CHANGELOG.md) and [`CREATOR_PLAYBOOK.md`](../CREATOR_PLAYBOOK.md).

---

## Non-goals

- Desktop (`bpeai-workspace-app`) integration
- Zip / S3 **Python code** upload for creators (git PR only)
- Cross-creator pack sharing / marketplace
- Replacing first-party `eq_list` / solids orchestrator
