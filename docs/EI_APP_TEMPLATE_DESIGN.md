# EI App Template Architecture

Status: **beta locked** (2026-07-24)  
Owner: BPEAI platform / creator SDK  
Repos: `bpeai-creator-apps` (authoring) → mirror into main `bpeai` on deploy

## Workspace guidance

| Repo | Keep in workspace? | Why |
|------|--------------------|-----|
| **bpeai-creator-apps** | **Yes — primary** | Templates, SDK, knowledge packs, local test tools |
| **bpeai** | **Yes — required** | Runtime (`vendor_api`), portal docs, mirrored `py/apps` + packs, EI hub |
| **bpeai-workspace-app** | Optional | Desktop only; not on the critical path for template/SDK work |

Day-to-day edits for this initiative land first in **bpeai-creator-apps**, then mirror contracts into **bpeai** when schemas/runtime/docs change.

---

## Three-way split (locked)

| Layer | Responsibility | Lives in |
|-------|----------------|----------|
| **1. Template family** | Deliverable / output contract + run phases | `py/apps/_templates/<family>/` (`equipment_evaluator` shipped) |
| **2. Knowledge pack** | Equipment system × application SME content (YAML) | `py/knowledge/<system>/` |
| **3. SDK** | Shared LLM helpers, pack loading, validation, artifacts | `py/libs/bpeai_creator_sdk/` |

**Rule:** If SMEs would debate a list in a meeting, it belongs in a knowledge pack (or shared `bpeai_taxonomy`), not buried in a prompt string.

---

## Template families (by deliverable)

Build **one family at a time**. First family is the evaluator.

| Family id | Primary hub deliverables | Output schema | Priority |
|-----------|--------------------------|---------------|----------|
| `equipment_evaluator` | Design option evaluation, Technology recommendation, DIR | `equipment_selector_v1` | **P0 — shipped (beta)** |
| `datasheet` | Equipment datasheet | `datasheet_v1` | P1 |
| `specification_urs` | Specification / URS | `urs_v1` / `spec_v1` | P1 |
| `pid` | P&ID / drawing package | `pid_v1` | P2 |
| `test_protocol` | Test / qualification protocol | `protocol_v1` | P2 |

Do **not** fork a new Python template per equipment system (mixing vs heat transfer). Systems differ by **pack**, not by template family.

**Local artifacts (creator machine):** sectioned markdown + styled PDF + optional 7-slide PPTX under `./artifacts/`.  
**Portal hub:** still stores **`datasheet_markdown` as `.md`** only (no PDF/PPTX upload in beta).

---

## Shared vs pack-local taxonomy

### Shared (`bpeai` → `bpeai_taxonomy`)

Cross-app controlled vocabularies already used by solids / vendor flows:

- `applications.yaml`
- `preparations.yaml`
- `equipment_items.yaml`
- `regions.yaml`

SDK may load these when available and fall back gracefully for creator-only clones.

### Pack-local (`bpeai-creator-apps` → `py/knowledge/<system>/`)

**Production packs:** [`py/knowledge/mixing/`](../py/knowledge/mixing/).  
**Draft packs:** [`py/knowledge/filtration/`](../py/knowledge/filtration/) (`approval_status: draft_pending_sme_approval`).

| File | Purpose |
|------|---------|
| `pack.yaml` | Pack metadata: system id, industries, default prep keys, prompt hooks |
| `dir_requirements.yaml` | DIR questionnaires keyed by scenario / preparation |
| `equipment_options.yaml` | Allowed technology / option catalog for validation |
| `validation_rules.yaml` | Hard/soft rules for DIR codes and LLM field enums |
| `prompt_fragments.yaml` | Injectable SME guidance (includes depth bar) |
| `report_outline.yaml` | Required report headings for markdown / PDF |
| `pptx_outline.yaml` | Slide outline + `reference_decks` |
| `references/*.pptx` | Style stubs (replace private decks via `manage_pptx_reference.py`) |

If a pack or any of the above components is missing at runtime, the
`equipment_evaluator` template LLM-bootstraps an initial draft (SDK:
`sme.pack_bootstrap`; agent: `_ensure_knowledge_pack`). Drafts are subject to
SME / platform approval before production use.

Future systems: `heat_transfer/`, `chromatography/`, `fluid_transfer/`, `cell_culture/`, …

---

## Equipment evaluator run model (P0)

Phases:

1. **`dir`** — return SME DIR questionnaire (+ common starter codes)
2. **`evaluate`** — validate DIR → Serper (+ page excerpts) → structured LLM → soft checks → markdown + PDF artifacts
3. **`pptx`** (local) — optional 7-slide deck from evaluation JSON + `datasheet_markdown`

Inputs (minimum):

- `system_name` / scenario key
- `application` (prefer values from shared applications catalog)
- `dir_code` (evaluate phase)
- `phase` (`dir` | `evaluate` | `pptx`)
- `knowledge_pack` (default from manifest / agent `knowledge_pack_id`)

---

## SDK modules (shipped)

```text
bpeai_creator_sdk/
  base.py                 # CreatorAppBase + default_creator_model
  output.py               # equipment_selector_v1 (+ GPT-parity fields)
  tools.py                # Serper + page excerpts
  sme/
    pack_loader.py        # load py/knowledge/<system>/*.yaml
    validate.py           # DIR + option soft checks
    report.py             # heading / thin-section checks
  artifacts/
    pptx_eval.py          # 7-slide deck + auto-fit fonts
    pdf_eval.py           # local PDF from datasheet_markdown
    reference_decks.py    # list / replace pack reference PPTX
  local_*.py              # local_chat helpers
```

Manifest:

- `equipment_system` — pack selection / portal enum
- optional `knowledge_pack` — defaults to `equipment_system` when omitted

---

## Build order

1. Design + mixing pack YAML — **done**
2. SDK pack loader + DIR validation — **done**
3. `equipment_evaluator` template + GPT-parity — **done**
4. Local PDF + PPTX autofit + reference-deck tooling — **done**
5. Mirror SDK/template/pack into `bpeai` for deploy; sync portal `/sdk` docs — **this lock-in**
6. Wire or retire legacy mixing matcher example (marked do-not-copy)
7. Second pack (`heat_transfer`) after mixing docs stay consistent
8. Second template family (`datasheet` / `specification_urs`) later

---

## Acceptance criteria (P0 evaluator template)

- Creator copies evaluator template, points at an existing pack, and gets DIR → evaluate without editing SDK code.
- DIR options and common codes come from YAML, not Python dicts.
- LLM options can be soft-checked against `equipment_options.yaml`.
- Local chat / JSON pipe works via `local_chat.py` / `agent.py` stdio.
- Evaluation quality meets or exceeds the Life Science Mixing Systems Expert custom GPT bar: design basis, ranked options, exclusions, sectioned markdown, local PDF, optional 7-slide PPTX.

---

## Non-goals (for now)

- Desktop (`bpeai-workspace-app`) integration
- Zip / S3 **code** upload for creators (git PR only)
- Portal multi-turn DIR UI + hub storage of PDF/PPTX binaries
- Cloning PPTX slide masters from reference decks (renderer recreates style in code)
- Replacing first-party `eq_list` / solids orchestrator
- Shipping five deliverable schemas before evaluator packs are proven
