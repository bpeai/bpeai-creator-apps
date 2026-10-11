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
- Platform seed packs cannot be bound at runtime — a creator app uses a **private pack** bound 1:1 on the portal (after upload, pack `pack_id` follows the platform-assigned opaque App ID).
- **Do not write knowledge-pack YAML in Cursor.** The pack is LLM-bootstrapped when the creator runs `local_chat.py` in PowerShell, using **their** `.env` keys (`OPENAI_API_KEY`, `SERPER_API_KEY`). Do not copy `py/knowledge/_examples/mixing_stub/`, `equipment_evaluator_stub/`, or `mixing_sizing_stub/` as a starter pack. Do not run `local_chat.py` for them.

## Interview (one decision at a time)

Ask briefly; wait for answers before scaffolding.

0. **Template family** (choose one)
   - **Evaluator** (`equipment_evaluator`) — design-option recommendation, `equipment_selector_v1`
   - **Sizing** (`equipment_sizing`) — capacity / connections / envelope, `equipment_sizing_v1`

1. **App identity**
   - **label** (display name — creator-managed, like a YouTube video title)
   - **local folder** (optional convenience name under `py/apps/<family>/<folder>/` — **not** the global identity)
   - **App ID** — platform-assigned opaque id (5–6 mixed-case letters, e.g. `KqWmX`). Minted on portal draft create **or** first zip upload. Leave `manifest.json` `id` empty until then; after mint, put the assigned id in `manifest.id` / `agent.app_id` / pack bind.
   - creator display name
   - `equipment_system` (taxonomy only: mixing, filtration, heat_transfer, … — **not** the pack name)
   - Public URL is `/engineering/app/<AppID>` (no separate human slug)

2. **SME documents** (optional; indexed later by Python, not by this wizard)
   - Ask whether the creator has technical PDFs/docs (`.pdf`, `.md`, `.txt`, `.csv` — not `.docx`).
   - If yes, they go in `py/knowledge/<family>/<folder>/references/content/` **before or after** the first local run. Style PPTX shells live in `references/style/`.

3. **Customization depth after the first Python run** (user may pick more than one)
   - **SME dial (prompts)** — edit `prompt_fragments.yaml` (+ light catalog touch)
   - **Outputs** — `report_outline.yaml`, options, validation within the family schema
   - **Optional Python tools** — wire `creator_tools.py` inside existing phases; show HANDSHAKE constraints

   Record the choice. Do **not** author pack files now — wait until Python has generated the draft.

## Execute (app only)

1. Copy template (PowerShell example). Use the family from step 0 and a **local folder** name (not a global id):

   ```powershell
   Copy-Item -Recurse py\apps\_templates\equipment_evaluator py\apps\equipment_evaluator\<folder>
   Copy-Item -Recurse py\apps\_templates\equipment_sizing py\apps\equipment_sizing\<folder>
   ```

2. Rewrite in `py/apps/<family>/<folder>/` only:
   - Class name + `equipment_system` + `creator_display_name` in `agent.py`
   - Leave `app_id` / `knowledge_pack_id` as placeholders **or** empty until the portal assigns an App ID
   - Keep `template_family` matching the copied template
   - `manifest.json`: set `label`, `equipment_system`; leave `id` / `slug` empty for first upload (platform mints opaque App ID and rewrites them). After mint, keep `id` = assigned App ID and `python_entrypoint` `apps.<family>.<AppID>.agent`
   - Point out `HANDSHAKE:` comments and `EXTENSIONS.md`
   - Optionally create empty `py/knowledge/<family>/<folder>/references/content/` so they have a drop folder. **Do not** write `pack.yaml` or other pack YAML.

3. Stop. Instruct the creator to generate the pack themselves in a **PowerShell** terminal (their `.env` keys). Give this block and wait for feedback:

   ```powershell
   python py\tools\local_chat.py --app <family>/<folder>
   ```

   Tell them:

   - First run LLM-bootstraps `py/knowledge/<family>/<folder>/` (draft pending SME approval).
   - Optional SME files: copy into `py/knowledge/<family>/<folder>/references/content/`, then re-run to index.
   - At the `>` prompt, enter **system name and application/domain**, for example: `CIP return pump, biopharmaceutical`
   - Then reply with a DIR code to evaluate; sizing apps may ask a second input code; `pptx` after a finished result for a deck.
   - Ask them to paste status lines or questions here when the first run finishes.

4. **After** they confirm the pack exists, help with the chosen depth:
   - Prompts → `prompt_fragments.yaml` keys listed in customization-map
   - Outputs → outlines / options / validation
   - Tools → keep `creator_tools.py`; show example import + call inside `dir` / `evaluate` only

5. Ship path (do not edit the website repo):

   - Portal https://bpiplatform.bpeai.com → Upload zip of `py/apps/<family>/<folder>/` **and** `py/knowledge/<family>/<folder>/` (platform mints App ID on first upload if `manifest.id` is empty), **or** create a draft on the portal first (label only) and put the returned App ID into `manifest.json` before upload
   - `python py/tools/upload_creator_bundle.py --apps <folder>` (includes the matching pack by default)
   - Then **Test → Submit → admin Publish**

## After scaffolding

Summarize the local app folder that was copied/edited, remind them **not** to expect pack YAML until Python has run, and repeat the `local_chat.py` command plus the `system name, application` example. Offer to deepen prompts, outputs, or optional tools **after** that first run.
