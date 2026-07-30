# Equipment evaluator template

Canonical starter for **design option evaluation** EI apps (DIR → recommendation).

Quality bar: match or exceed the **Life Science Mixing Systems Expert** custom GPT
(structured DIR workflow, deep option evaluation, markdown report, optional 7-slide PPTX).

## Repo ownership

This template (and the SDK / `_examples` stubs) are what `bpeai-creator-apps` ships.

Creator apps copied from this template (e.g. a local `vent_filter_expert`) and
creator knowledge packs under `py/knowledge/<id>/` are **workspace-local** and
gitignored — do not commit them. Platform seeds live in **bpeai**
`py/knowledge/`; private packs are portal-managed.

## Knowledge + DIR catalog

SME content comes from a **knowledge pack** (default id: `mixing`). Prefer portal
**Knowledge** for private packs. Do not fork DIR menus into `agent.py`.

DIR menus are a growing **list catalog** (`dir_menus` in `dir_requirements.yaml`)
plus an SME review table `dir_catalog.md`.

Runtime selection uses match-or-generate:

1. Fingerprint: `system_name` + `application`/`industry` + `equipment_system_variant` (+ optional `scenario_id`)
2. Reuse an existing catalog row when it matches
3. Otherwise Serper + LLM generate a new questionnaire with **numeric** starter
   common codes, append it as `draft_generated`, and present it for this run

`common_codes` must be hyphen-separated option indexes with captions
(e.g. `2-1-1` — “250–1,000 L stainless CIP/SIP dissolving dry powder”), not tags like `SIP`.

## Quick start

```powershell
Copy-Item -Recurse py\apps\_templates\equipment_evaluator py\apps\my_equipment_expert
```

Then rename class / `app_id` / manifest fields, set `knowledge_pack_id` /
`equipment_system`, and point `manifest.json` `knowledge_pack` at a pack
(platform seed, private portal pack slug, or let the agent draft a new one on first run).

## Local test

```powershell
python py\tools\local_chat.py --app equipment_evaluator
# > Media prep vessel, biopharma
# > 2-1-1
# > pptx
```

For SDK tests without network, use the committed stub pack:
`py/knowledge/_examples/mixing_stub/`.

Artifacts (markdown + PDF + optional PPTX) write under `./artifacts/` (gitignored).

## Phases

| Phase | Trigger | Result |
|-------|---------|--------|
| DIR | no `dir_code`, or `phase=dir` | Match catalog or generate draft questionnaire + captioned numeric common codes |
| Evaluate | valid `dir_code` | GPT-parity `equipment_selector_v1` + sectioned `datasheet_markdown` (+ `.md` / `.pdf`) |
| PPTX | `pptx` / `y` in local chat, or `deliverable=pptx` | 7-slide deck with auto-fit fonts |
| generate_dir | `phase=generate_dir` | Force catalog generate/persist for the fingerprint |

## Portal vs local formats

- Hub / portal: `datasheet_markdown` → S3 `.md` only
- Local: also writes styled PDF; PPTX is local authoring unless product adds binary upload

## Reference PPTX management

Shared style shells live in `py/knowledge/_templates/references/` (any `*.pptx` /
`*.pdf` name). Bootstrap copies them into each new pack’s `references/`.
Replace private decks in a local (gitignored) pack:

```powershell
python py\tools\manage_pptx_reference.py --pack filtration list
python py\tools\manage_pptx_reference.py --pack filtration replace --src path\to\deck.pptx --name my_vent_filter_style.pptx
```

## Reference

- Design: `docs/EI_APP_TEMPLATE_DESIGN.md`
- Playbook: `CREATOR_PLAYBOOK.md`
- Mixing pack (canonical): `bpeai/py/knowledge/mixing/`
- Local example stub: `py/knowledge/_examples/mixing_stub/`
