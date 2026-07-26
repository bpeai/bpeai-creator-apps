# Vent Filter Expert

DIR → design option evaluation for sterile vent / tank-breather filtration.

Starter from `py/apps/_templates/equipment_evaluator`. SME content uses the
**filtration** platform pack — canonical location is the **bpeai** deploy repo
(`py/knowledge/filtration/`, draft pending SME approval). Bind/clone on the portal.

If pack YAML is missing locally, the agent LLM-bootstraps a draft via
`_ensure_knowledge_pack` (subject to SME/platform approval). Do not commit a
full filtration pack into creator-apps.

## Identity (must match portal)

| Concept | Value |
|---------|--------|
| Folder / `app_id` / manifest `id` | `vent_filter_expert` |
| Portal slug | `vent-filter-expert` |
| Python module | `apps.vent_filter_expert.agent` |
| Agent class | `VentFilterExpertAgent` |
| Creator | `redcaad` / Redcaad |
| Knowledge pack | `filtration` |

## Local test

Prefer portal pack payload / sync, or bootstrap on first run:

```powershell
python py\tools\local_chat.py --app vent_filter_expert
# > Buffer hold tank vent filter, biopharma
# > 2-1-2-3-1-1
# > pptx
```

Artifacts (markdown + PDF + optional PPTX) write under `./artifacts/` (gitignored).

## Phases

| Phase | Trigger | Result |
|-------|---------|--------|
| DIR | no `dir_code`, or `phase=dir` | Questionnaire + captioned common codes from pack |
| Evaluate | valid `dir_code` | GPT-parity `equipment_selector_v1` + sectioned `datasheet_markdown` (+ `.md` / `.pdf`) |
| PPTX | `pptx` / `y` in local chat, or `deliverable=pptx` | 7-slide deck with auto-fit fonts |

## Portal vs local formats

- Hub / portal: `datasheet_markdown` → S3 `.md` only
- Local: also writes styled PDF; PPTX is local authoring unless product adds binary upload

## Reference

- Design: `docs/EI_APP_TEMPLATE_DESIGN.md`
- Playbook: `CREATOR_PLAYBOOK.md`
- Pack (canonical): `bpeai/py/knowledge/filtration/` (draft — pending approval)
