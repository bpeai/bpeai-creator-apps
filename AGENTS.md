# BPEAI EI creator authoring repo

This is **bpeai-creator-apps** — where authorized creators build Engineered
Intelligence (EI) apps. It is **not** the website deploy repo. Creators never
edit hub/portal React.

## Three layers

1. **Template family** — `py/apps/_templates/equipment_evaluator/` (copy, don’t edit in place)
2. **Knowledge pack** — SME prompts, DIR menus, options, outlines (`py/knowledge/<pack>/`)
3. **SDK** — `py/libs/bpeai_creator_sdk/` (**do not fork**; `git pull` for updates)

## When the user wants to create or customize an EI app

Follow the project skill **`.cursor/skills/ei-creator-wizard/SKILL.md`**
(also invokable as `/ei-creator-wizard` or by the user saying **Create my EI app**).

Prefer pack YAML (`prompt_fragments.yaml`, outlines, options) over forking
hard-coded evaluation contract prompts. Optional Python helpers:
`creator_tools.py` — see `docs/EI_CREATOR_EXTENSIONS.md`.

Preserve handshake boundaries tagged **`HANDSHAKE:`** in the template
(`ei_handshake_v1`, phases `dir` / `evaluate` / `pptx` / `generate_dir`,
`equipment_selector_v1`). Do not invent new SSE events or UI buttons.

## Ship path

Local test → portal zip / `upload_creator_bundle.py` → Test → Submit → admin Publish  
Portal: https://bpiplatform.bpeai.com (apex, not `www`).

## Trust

Creators should **trust this workspace** so project hooks can inject onboarding
context when Agent chat starts.
