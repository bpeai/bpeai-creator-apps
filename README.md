# bpeai-creator-apps

Templates and source for BPEAI Equipment Intelligence creator apps  
(portal: [bpiplatform.bpeai.com](https://bpiplatform.bpeai.com)).

**Confidential** — for authorized BPEAI creators only. All rights reserved.

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
    <your_slug>/                       ← your app (via PR)
```

## Playbook (code → test → PR)

1. **Access** — BPEAI grants `creatorAccess`. Sign in at https://bpiplatform.bpeai.com
2. **Copy the template**

   ```text
   py/apps/_template/  →  py/apps/<your_slug>/
   ```

3. Rename the agent class and set `app_id` to match your manifest `id`.
4. Edit `manifest.json` (slug, label, description, equipment system, …).
5. Implement `run(inputs)` — return validated `equipment_selector_v1` JSON.
6. **Local test**

   ```bash
   cd py/apps/<your_slug>
   echo '{"system_name":"Media Prep Vessel","application":"biopharma"}' | python agent.py
   ```

7. Push your branch and **open a PR** into this repo (or notify BPEAI).
8. On **bpiplatform.bpeai.com**:
   - **New app** → set Python module `apps.<your_slug>.agent` and agent class name
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
