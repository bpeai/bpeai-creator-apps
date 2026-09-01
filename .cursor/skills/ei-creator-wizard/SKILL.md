---
name: ei-creator-wizard
description: >-
  Guide BPEAI creators to scaffold and customize an EI app from the
  equipment_evaluator template (prompts, outputs, optional Python tools),
  local-test, and portal upload. Use when the user wants to create, customize,
  onboard, or get started with an EI app, or says "Create my EI app".
---

# EI Creator Wizard

Step-by-step wizard for building a customized EI app in **this repo only**.
Creators do **not** have the website UI codebase — never edit hub/portal React.

Read references as needed:

- [customization-map.md](references/customization-map.md)
- [handshake-ui.md](references/handshake-ui.md)
- [playbook-checklist.md](references/playbook-checklist.md)

Full docs: `docs/EI_CREATOR_EXTENSIONS.md`, `docs/EI_HANDSHAKE.md`, `CREATOR_PLAYBOOK.md`.

## Guardrails (always)

- Prefer pack YAML over forking `DIR_GENERATE_PROMPT` / `EVALUATION_PROMPT` / `PPTX_SLIDE_PACK_PROMPT`.
- Preserve `handshake_protocol` / `output_schema_version` / known phases and SSE events.
- Do not invent new SSE events or UI buttons.
- Do not fork `py/libs/bpeai_creator_sdk/`.
- Do not commit secrets, `.env`, `artifacts/`, or treat gitignored apps as platform seeds.
- Platform seed packs cannot be bound at runtime — a creator app uses a **private pack with the same id** as the app.

## Interview (one decision at a time)

Ask briefly; wait for answers before scaffolding.

1. **App identity**
   - `id` (snake_case folder / `app_id` / manifest `id` / pack folder / `pack.yaml` `pack_id` — **all the same**)
   - slug, label, creator display name
   - `equipment_system` (taxonomy only: mixing, filtration, heat_transfer, … — **not** the pack name)

2. **Starting knowledge pack** (always `py/knowledge/<same app id>/`)
   - Let the template LLM-bootstrap a draft on first `local_chat` run, **or**
   - Copy/adapt `py/knowledge/_examples/mixing_stub/` into `py/knowledge/<id>/` and set `pack_id` to `<id>`
   - Ask whether the creator has technical PDFs/docs. If yes, they go in `py/knowledge/<id>/references/content/` (optional). Style PPTX shells live in `references/style/`.

3. **Customization depth** (user may pick more than one)
   - **SME dial (prompts)** — edit `prompt_fragments.yaml` (+ light catalog touch)
   - **Outputs** — `report_outline.yaml`, options, validation within `equipment_selector_v1`
   - **Optional Python tools** — wire `creator_tools.py` inside existing phases; show HANDSHAKE constraints

## Execute

1. Copy template (PowerShell example):

   ```powershell
   Copy-Item -Recurse py\apps\_templates\equipment_evaluator py\apps\<id>
   ```

2. Rewrite in `py/apps/<id>/`:
   - Class name + `app_id` + `knowledge_pack_id` (**same as `app_id`**) + `equipment_system` + `creator_display_name` in `agent.py`
   - `manifest.json`: `id`, `slug`, `label`, `equipment_system`, `knowledge_pack` (**same as `id`**), `python_entrypoint` (`apps.<id>.agent`), `route`, keep `output_schema_version: equipment_selector_v1`
   - Point out `HANDSHAKE:` comments and `EXTENSIONS.md`

3. Pack work (per chosen depth):
   - Prompts → `prompt_fragments.yaml` keys listed in customization-map
   - Outputs → outlines / options / validation
   - Tools → keep `creator_tools.py`; show example import + call inside `dir` / `evaluate` only
   - After first local run, remind the creator to drop SME files into `references/content/` if they have any, then re-run to index them

4. Local verify:

   ```powershell
   python py\tools\local_chat.py --app <id>
   ```

5. Ship path (do not edit the website repo):

   - Portal https://bpiplatform.bpeai.com → Upload zip of `py/apps/<id>/` **and** `py/knowledge/<id>/`, **or**
   - `python py/tools/upload_creator_bundle.py --apps <id>` (includes the matching pack by default)
   - Then **Test → Submit → admin Publish**

## After scaffolding

Summarize what changed, which files are the “dials”, and the next command to run locally. Offer to deepen prompts, outputs, or optional tools next.
