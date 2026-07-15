# Selector app template

Copy this folder to create a new Equipment Intelligence selector.

## Quick start

1. Copy `py/apps/_template/` → `py/apps/your_app_slug/`
2. Rename the class in `agent.py` and set `app_id` to match your manifest `id`
3. Edit `manifest.json` (`id`, `slug`, `label`, `equipment_system`, …)
4. Implement `run(inputs)` — return validated `equipment_selector_v1` JSON
5. Local test:

```bash
cd py/apps/your_app_slug
echo '{"system_name":"Media Prep Vessel","application":"biopharma"}' | python agent.py
```

6. On [bpiplatform.bpeai.com](https://bpiplatform.bpeai.com): **New app** → set
   - Python module: `apps.your_app_slug.agent`
   - Agent class: `YourAgentClass`
7. Open a PR that adds `py/apps/your_app_slug/` — BPEAI merges and rebuilds `vendor_api`, then **Test** → **Submit for review**

See the portal **SDK** page and `py/libs/bpeai_creator_sdk/README.md` for the full contract.

## Reference

Production-quality example: `py/apps/examples/mixing_agitator_matcher/`
