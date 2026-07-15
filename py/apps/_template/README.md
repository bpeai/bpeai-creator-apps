# Selector app template

Copy this folder to create a new Equipment Intelligence selector.

## Recommended order

1. Clone [bpeai-creator-apps](https://github.com/bpeai/bpeai-creator-apps) (or use this monorepo `py/apps/` locally).
2. Copy `_template` → your app folder and implement Python (local test).
3. On [bpiplatform.bpeai.com](https://bpiplatform.bpeai.com): **New app** with matching slug / module / class.
4. Open a PR; after BPEAI deploys: **Test** → **Submit for review**.

## Quick start

1. Copy `py/apps/_template/` → `py/apps/your_app_slug/`  
   (folder name = snake_case **id**, e.g. `heat_exchanger_selector`)
2. In `agent.py`:
   - Rename `MySelectorAgent` → your class (portal **Agent class**)
   - Set `app_id` to match manifest `id` (unique across apps)
3. Edit `manifest.json` fields (see table below)
4. Implement `run(inputs)` — return validated `equipment_selector_v1` JSON
5. Local test:

```bash
cd py/apps/your_app_slug
echo '{"system_name":"Media Prep Vessel","application":"biopharma"}' | python agent.py
```

6. Portal **New app**:
   - Slug: `your-app-slug` (URL segment; becomes id `your_app_slug`)
   - Python module: `apps.your_app_slug.agent`
   - Agent class: your renamed class
7. PR → BPEAI merge + rebuild → **Test** → **Submit**

## manifest.json fields

| Field | Meaning |
|-------|---------|
| `id` | Unique snake_case id; must match `agent.py` `app_id` and folder name |
| `slug` | URL segment on the EI hub (`/engineering/equipment-intelligence/<slug>`) |
| `label` | Display name on hub card |
| `description` | Short hub blurb |
| `equipment_system` | e.g. `mixing`, `heat_transfer` |
| `required_inputs` | Keys your `run(inputs)` expects |
| `python_entrypoint` | Illustrative; portal **Python module** is what runtime uses (`apps.<id>.agent`) |
| `min_tier` | FREE / INDIVIDUAL / PROFESSIONAL (portal: Free / Pro / Pro+) |

## Reference

Production-quality example: `py/apps/examples/mixing_agitator_matcher/` (creator-apps repo) or `py/apps/mixing_agitator_matcher/` (website monorepo).
