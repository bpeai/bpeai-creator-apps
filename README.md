# bpeai-creator-apps

Templates and source for BPEAI Equipment Intelligence creator apps  
(portal: [bpiplatform.bpeai.com](https://bpiplatform.bpeai.com)).

Public authoring repo for **authorized BPEAI creators**. Do not commit secrets
(`.env`, API keys). Local secrets stay on your PC; BPEAI platform keys are not
used for local test.

## Start here (Cursor)

1. Clone this repo and **Open Folder** in [Cursor](https://cursor.com).
2. **Trust the workspace** when prompted (enables project hooks).
3. Open **Agent** chat and say: **Create my EI app**  
   (or `/ei-creator-wizard`). Cursor follows the in-repo wizard under
   `.cursor/skills/ei-creator-wizard/` — you do not need to memorize the SDK.

See [AGENTS.md](./AGENTS.md). Customization dials (prompts, outputs, optional
Python tools, UI capability matrix): [docs/EI_CREATOR_EXTENSIONS.md](./docs/EI_CREATOR_EXTENSIONS.md).

**Full playbook:** [CREATOR_PLAYBOOK.md](./CREATOR_PLAYBOOK.md) (manual steps kept as fallback).

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
2. **Clone once**, open in **Cursor**, trust workspace, Agent → **Create my EI app** (primary).
3. **Manual fallback** — for each app copy the template:

```powershell
   Copy-Item -Recurse py\apps\_templates\equipment_evaluator py\apps\heat_exchanger_evaluator
```

4. Rename the agent class and set `app_id` / `knowledge_pack_id` to match your pack.
5. Edit `manifest.json` (slug, label, description, `equipment_system`, `knowledge_pack`,
   optional `handshake_protocol: "ei_handshake_v1"`).
6. **First local run generates the knowledge pack** (creator `.env` keys — OpenAI / Serper).
   Do not hand-author pack YAML before this. Optional SME files go in
   `py/knowledge/<your_id>/references/content/`.

   ```powershell
   python py\tools\local_chat.py --app <your_id>
   # > CIP return pump, biopharmaceutical
   ```

7. After the draft pack exists, edit `prompt_fragments.yaml` + outlines; see
   [docs/EI_CREATOR_EXTENSIONS.md](./docs/EI_CREATOR_EXTENSIONS.md).

8. **Upload** (preferred):

   ```powershell
   $env:BPEAI_PLATFORM_URL = "https://bpiplatform.bpeai.com"
   $env:BPEAI_SESSION_COOKIE = "<portal session cookie>"
   python py\tools\upload_creator_bundle.py --apps <your_id> --packs <pack_id>
   ```

   Or portal **Upload**. Bind the private pack under Settings if needed.
9. Portal **Test** → **Submit** → admin publish on https://bpeai.com.

See [CREATOR_PLAYBOOK.md](./CREATOR_PLAYBOOK.md) for the full flow.
