# Equipment evaluator template

Canonical starter for **design option evaluation** EI apps (DIR → recommendation).

Quality bar: match or exceed the **Life Science Mixing Systems Expert** custom GPT
(structured DIR workflow, deep option evaluation, markdown report, optional 7-slide PPTX).

SME content comes from a **knowledge pack** (default seed: `mixing`). Prefer portal **Knowledge** for private packs and DIR CRUD; do not fork DIR menus into `agent.py`. Point the app at a pack id and bind it on the portal.

DIR menus resolve by `(equipment_system_variant × industry × scenario)`. Inputs: `industry`, `equipment_system_variant`, `application`, `system_name`.

If the target pack (or any YAML component) is missing, the agent LLM-bootstraps an
**initial draft** under `py/knowledge/<id>/` with
`approval_status: draft_pending_sme_approval`. Review before production use.

## Quick start

```powershell
Copy-Item -Recurse py\apps\_templates\equipment_evaluator py\apps\mixing_system_expert
```

Then rename class / `app_id` / manifest fields, set `knowledge_pack_id` /
`equipment_system`, and point `manifest.json` `knowledge_pack` at an existing pack
(platform seed, private portal pack slug, or let the agent draft a new one on first run).

## Local test

```powershell
python py\tools\local_chat.py --app equipment_evaluator
# > Media prep vessel, biopharma
# > 2-1-2-3-1-1
# > pptx
```

Artifacts (markdown + PDF + optional PPTX) write under `./artifacts/` (gitignored).

## Phases

| Phase | Trigger | Result |
|-------|---------|--------|
| DIR | no `dir_code`, or `phase=dir` | Questionnaire + captioned common codes from pack YAML |
| Evaluate | valid `dir_code` | GPT-parity `equipment_selector_v1` + sectioned `datasheet_markdown` (+ `.md` / `.pdf`) |
| PPTX | `pptx` / `y` in local chat, or `deliverable=pptx` | 7-slide deck with auto-fit fonts |

## Portal vs local formats

- Hub / portal: `datasheet_markdown` → S3 `.md` only
- Local: also writes styled PDF; PPTX is local authoring unless product adds binary upload

## Reference PPTX management

Public-repo `references/*.pptx` are **style stubs**. Replace private decks:

```powershell
python py\tools\manage_pptx_reference.py --pack mixing list
python py\tools\manage_pptx_reference.py --pack mixing replace --src path\to\deck.pptx --name media_preparation_vessel_mixing_evaluation.pptx
```

## Reference

- Design: `docs/EI_APP_TEMPLATE_DESIGN.md`
- Playbook: `CREATOR_PLAYBOOK.md`
- Mixing pack: `py/knowledge/mixing/`
