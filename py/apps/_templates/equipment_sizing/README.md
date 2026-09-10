# Equipment sizing template

Canonical starter for **equipment sizing** EI apps (DIR → capacity, connections, envelope).

Copy this folder to ``py/apps/equipment_sizing/<your_id>/``. Do **not** copy
``py/knowledge/_examples/mixing_sizing_stub/`` as a live pack — first
``local_chat`` LLM-bootstraps ``py/knowledge/equipment_sizing/<your_id>/``.

## Repo ownership

This template (and the SDK / `_examples` stubs) ship from `bpeai-creator-apps`.
Live copies under `py/apps/equipment_sizing/<id>/` and
`py/knowledge/equipment_sizing/<id>/` are workspace-local and gitignored.

## Knowledge + DIR catalog

Same match-or-generate DIR catalog as the evaluator family. Sizing then asks
for extra material-balance inputs only when DIR answers are not enough.

Use the committed stub pack for SDK tests: `py/knowledge/_examples/mixing_sizing_stub/`.
Do **not** point this template at evaluator `mixing_stub`.

## Quick start

```powershell
Copy-Item -Recurse py\apps\_templates\equipment_sizing py\apps\equipment_sizing\<your_id>
python py\tools\local_chat.py --app equipment_sizing/<your_id>
```

Rename class / `app_id` / manifest `id` / `knowledge_pack` to the **leaf** id.
Keep `template_family: equipment_sizing` and
`python_entrypoint: apps.equipment_sizing.<your_id>.agent`.

## Phases

| Phase | Trigger | Result |
|-------|---------|--------|
| DIR | no `dir_code`, or `phase=dir` | Match catalog or generate draft questionnaire |
| Sizing gaps | valid `dir_code` without enough inputs | Second DIR-shaped questionnaire (`sizing_inputs`) |
| Size | `dir_code` + optional `sizing_inputs` | `equipment_sizing_v1` + markdown report |
| PPTX | `deliverable=pptx` | 7-slide deck from sizing JSON |

## Reference

- Design: `docs/EI_APP_TEMPLATE_DESIGN.md`
- AI handshakes: `docs/EI_AI_HANDSHAKES.md`
- Local example stub: `py/knowledge/_examples/mixing_sizing_stub/`
