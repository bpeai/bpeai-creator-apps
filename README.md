# bpeai-creator-apps

Templates and source for BPEAI Equipment Intelligence creator apps  
(portal: [bpiplatform.bpeai.com](https://bpiplatform.bpeai.com)).

**Confidential** — for authorized BPEAI creators only. All rights reserved.

**Full playbook:** [CREATOR_PLAYBOOK.md](./CREATOR_PLAYBOOK.md) (same guide as in the website docs).

## What this repo is for

- Third-party SMEs build selector apps here (Python).
- Production deploy still happens from the main `bpeai` website repo on EC2 — **creators do not deploy**.

## Layout

```text
py/
  libs/bpeai_creator_sdk/              ← SDK contract (install locally; pip later)
  apps/
    _template/                         ← copy this to start
    examples/mixing_agitator_matcher/  ← read-only reference
    <your_id>/                         ← your app (via PR; snake_case folder = app id)
```

## Playbook (code → test → PR)

1. **Access** — BPEAI grants `creatorAccess` (you get an email). Sign in at https://bpiplatform.bpeai.com (apex, not `www`).
2. **Clone once**, then for each app copy the template:

   ```powershell
   Copy-Item -Recurse py\apps\_template py\apps\heat_exchanger_selector
   ```

3. Rename the agent class and set `app_id` to match manifest `id` (unique).
4. Edit `manifest.json` (slug, label, description, equipment system, …).
5. Implement `run(inputs)` — return validated `equipment_selector_v1` JSON.
6. **Local test**

   ```bash
   cd py/apps/<your_id>
   echo '{"system_name":"Media Prep Vessel","application":"biopharma"}' | python agent.py
   ```

7. Push your branch and **open a PR** into this repo.
8. On **bpiplatform.bpeai.com**:
   - **New app** → set Python module `apps.<your_id>.agent` and agent class name (slug shown later on Settings)
   - After BPEAI merges & deploys → **Test** → **Submit for review**

Full contract: [bpiplatform.bpeai.com/sdk](https://bpiplatform.bpeai.com/sdk) and `py/libs/bpeai_creator_sdk/README.md`.

## Required output

Your agent must return `equipment_selector_v1` with at least:

- `equipment_tag`, `selected_model`, `equipment_system`
- `key_specs[]`, `rationale`
- `creator_attribution` `{ display_name, app_id }`

## Roles

| Who | Does |
|-----|------|
| **Creator** | Code here, local test, portal draft, portal Test, Submit |
| **BPEAI** | Review PR, copy into main `bpeai` deploy repo, rebuild `vendor_api`, publish on the hub |

## Access tiers (portal)

When creating the app on bpiplatform: Free / Pro / Pro+ (maps to account tiers FREE / INDIVIDUAL / PROFESSIONAL).

## Support

Questions about access or publish: contact your BPEAI technical lead.  
Do not commit secrets (`.env`, API keys).
