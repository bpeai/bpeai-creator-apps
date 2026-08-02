# bpeai-creator-apps

Templates and source for BPEAI Equipment Intelligence creator apps  
(portal: [bpiplatform.bpeai.com](https://bpiplatform.bpeai.com)).

Public authoring repo for **authorized BPEAI creators**. Do not commit secrets
(`.env`, API keys). Local secrets stay on your PC; BPEAI platform keys are not
used for local test.

**Full playbook:** [CREATOR_PLAYBOOK.md](./CREATOR_PLAYBOOK.md)

**Handshake contract:** [docs/EI_HANDSHAKE.md](./docs/EI_HANDSHAKE.md) —
stable links/parameters between EI apps and BPEAI processing (`ei_handshake_v1`).

**Template architecture:** [docs/EI_APP_TEMPLATE_DESIGN.md](./docs/EI_APP_TEMPLATE_DESIGN.md) —
template family × knowledge pack × SDK.

**Knowledge packs:** Canonical platform seeds live in the **bpeai** deploy repo
(`py/knowledge/mixing`, `filtration`, …). This repo only has
[`py/knowledge/_examples/`](./py/knowledge/_examples/) stubs for local tests.
Creator private packs ship via **portal upload** with your app.

## What this repo is for

- Third-party SMEs build selector / evaluator apps here (Python + private pack).
- **Ship via portal zip upload** (or `py/tools/upload_creator_bundle.py`). Creators
  do **not** deploy the website. BPEAI admins publish after Submit for review.
- App-specific code stays in this repo’s `py/apps/<id>/` (gitignored locally);
  the deploy repo only hosts runtime, platform seeds, and first-party apps.

## Layout

```text
py/
  libs/bpeai_creator_sdk/               ← shared SDK (do not fork; BPEAI mirrors)
  knowledge/_examples/                  ← thin stubs for local tests only
  knowledge/<your_pack>/                ← your pack drafts (local/gitignored)
  apps/
    _templates/equipment_evaluator/     ← copy this to start (DIR → evaluate)
    examples/mixing_agitator_matcher/   ← LEGACY — do not copy (historical only)
    <your_id>/                          ← your app (local/gitignored; folder = app id)
  tools/
    local_chat.py
    upload_creator_bundle.py            ← primary ship path
    download_knowledge_pack.py          ← pull current pack (use --zip)
    download_app_bundle.py              ← backup restore (apps not mutated at runtime)
    sync_knowledge_pack.py
```


## Playbook (code → local test → upload)

1. **Access** — BPEAI grants `creatorAccess`. Sign in at https://bpiplatform.bpeai.com (apex, not `www`).
2. **Clone once**, then for each app copy the template:

```powershell
   Copy-Item -Recurse py\apps\_templates\equipment_evaluator py\apps\heat_exchanger_evaluator
```

3. Rename the agent class and set `app_id` / `knowledge_pack_id` to match your pack.
4. Edit `manifest.json` (slug, label, description, `equipment_system`, `knowledge_pack`,
   optional `handshake_protocol: "ei_handshake_v1"`).
5. Author your private pack under `py/knowledge/<pack_id>/` (DIR menus, options, prompts).
6. **Local test**:

   ```powershell
   python py\tools\local_chat.py --app <your_id>
   ```

7. **Upload** (preferred):

   ```powershell
   $env:BPEAI_PLATFORM_URL = "https://bpiplatform.bpeai.com"
   $env:BPEAI_SESSION_COOKIE = "<portal session cookie>"
   python py\tools\upload_creator_bundle.py --apps <your_id> --packs <pack_id>
   ```

   Or portal **Upload**. Bind the private pack under Settings if needed.
8. Portal **Test** → **Submit** → admin publish on https://bpeai.com.

See [CREATOR_PLAYBOOK.md](./CREATOR_PLAYBOOK.md) for the full flow.
