# bpeai-creator-apps

Templates and source for BPEAI Equipment Intelligence creator apps  
(portal: [bpiplatform.bpeai.com](https://bpiplatform.bpeai.com)).

Public authoring repo for **authorized BPEAI creators**. Do not commit secrets
(`.env`, API keys). Local secrets stay on your PC; BPEAI platform keys are not
used for local test.

**Full playbook:** [CREATOR_PLAYBOOK.md](./CREATOR_PLAYBOOK.md)

**Template architecture (beta locked):** [docs/EI_APP_TEMPLATE_DESIGN.md](./docs/EI_APP_TEMPLATE_DESIGN.md) —
template family × knowledge pack × SDK. Production mixing pack:
[`py/knowledge/mixing/`](./py/knowledge/mixing/).

## What this repo is for

- Third-party SMEs build selector / evaluator apps here (Python).
- Production deploy still happens from the main `bpeai` website repo on EC2 —
  **creators do not deploy**. There is **no zip upload API** — code ships via git PR.

## Layout

```text
py/
  libs/bpeai_creator_sdk/               ← shared SDK (do not fork; BPEAI mirrors)
  knowledge/<system>/                   ← SME packs (YAML + stub reference PPTX)
  apps/
    _templates/equipment_evaluator/     ← copy this to start (DIR → evaluate)
    examples/mixing_agitator_matcher/   ← LEGACY — do not copy (historical only)
    <your_id>/                          ← your app (PR this; folder = app id)
```

## Playbook (code → test → PR)

1. **Access** — BPEAI grants `creatorAccess` (you get an email). Sign in at https://bpiplatform.bpeai.com (apex, not `www`).
2. **Clone once**, then for each app copy the template:

```powershell
   Copy-Item -Recurse py\apps\_templates\equipment_evaluator py\apps\heat_exchanger_evaluator
```

3. Rename the agent class and set `app_id` / `knowledge_pack_id` to match your pack.
4. Edit `manifest.json` (slug, label, description, `equipment_system`, optional `knowledge_pack`).
5. Prefer editing **YAML packs** under `py/knowledge/<system>/` for DIR / options / prompts — not giant prompt strings.
6. **Local test** (smart text preferred):

   ```powershell
   python py\tools\local_chat.py --app <your_id>
   # > Media prep vessel, biopharma
   # > 2-1-2-3-1-1
   # > pptx
   ```

   Optional personal key: copy `.env.example` → `.env` (gitignored). For evaluator
   depth set `OPENAI_CREATOR_MODEL=gpt-5.2` and `OPENAI_CREATOR_MAX_OUTPUT_TOKENS=16000`
   (code default remains `gpt-4o`). See [docs/PORTAL_SDK_LOCAL_TEST.md](./docs/PORTAL_SDK_LOCAL_TEST.md).

   Local artifacts (gitignored `./artifacts/`): `*_evaluation.md`, `*_evaluation.pdf`,
   optional `*_evaluation.pptx`. **Portal hub datasheets use markdown only**
   (`datasheet_markdown` → S3 `.md`).

7. Push your branch and **open a PR** into this repo.
8. On **bpiplatform.bpeai.com**:
   - **New app** → set Python module `apps.<your_id>.agent` and agent class name
   - After BPEAI merges & deploys → **Test** → **Submit for review**

Full contract: [bpiplatform.bpeai.com/sdk](https://bpiplatform.bpeai.com/sdk) and
`py/libs/bpeai_creator_sdk/README.md`.

## Required output

Your agent must return `equipment_selector_v1` with at least:

- `equipment_tag`, `selected_model`, `equipment_system`
- `key_specs[]`, `rationale`
- `creator_attribution` `{ display_name, app_id }`

Evaluator apps also populate GPT-parity fields (`design_basis`, `failure_modes`,
`mixing_options`, `evaluation_matrix`, `datasheet_markdown`, …).

## Roles

| Who | Does |
|-----|------|
| **Creator** | Code here, local test, portal draft, portal Test, Submit |
| **BPEAI** | Review PR, copy into main `bpeai` deploy repo, rebuild `vendor_api`, publish on the hub |

## Support

Questions about access or publish: contact your BPEAI technical lead.
