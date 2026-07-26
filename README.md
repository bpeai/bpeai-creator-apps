# bpeai-creator-apps

Templates and source for BPEAI Equipment Intelligence creator apps  
(portal: [bpiplatform.bpeai.com](https://bpiplatform.bpeai.com)).

Public authoring repo for **authorized BPEAI creators**. Do not commit secrets
(`.env`, API keys). Local secrets stay on your PC; BPEAI platform keys are not
used for local test.

**Full playbook:** [CREATOR_PLAYBOOK.md](./CREATOR_PLAYBOOK.md)

**Template architecture:** [docs/EI_APP_TEMPLATE_DESIGN.md](./docs/EI_APP_TEMPLATE_DESIGN.md) —
template family × knowledge pack × SDK.

**Knowledge packs:** Canonical platform seeds live in the **bpeai** deploy repo
(`py/knowledge/mixing`, `filtration`, …). This repo only has
[`py/knowledge/_examples/`](./py/knowledge/_examples/) stubs for local tests.
Creator private packs are portal-managed — do not PR full SME packs here.

## What this repo is for

- Third-party SMEs build selector / evaluator apps here (Python).
- Production deploy still happens from the main `bpeai` website repo on EC2 —
  **creators do not deploy**. There is **no zip upload API** — code ships via git PR.

## Layout

```text
py/
  libs/bpeai_creator_sdk/               ← shared SDK (do not fork; BPEAI mirrors)
  knowledge/_examples/                  ← thin stubs for local tests only
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
5. Manage DIR / options on the portal **Knowledge** page (or clone a platform seed). Do not add production packs under `py/knowledge/`.
6. **Local test** (smart text preferred):

   ```powershell
   python py\tools\local_chat.py --app <your_id>
   # > Media prep vessel, biopharma
   # > 2-1-2-3-1-1
   # > pptx
   ```

   Optional: sync a pack from the portal with `py/tools/sync_knowledge_pack.py`.

7. Open a PR with `py/apps/<your_id>/` only (plus docs if needed).
8. After BPEAI merges + rebuilds: portal **Test** → **Submit** → admin publish.

See [CREATOR_PLAYBOOK.md](./CREATOR_PLAYBOOK.md) for the full flow.
