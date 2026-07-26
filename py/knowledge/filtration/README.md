> **DRAFT** — initial version pending SME / platform approval.

# Filtration knowledge pack (vent / sterile barrier)

Initial SME pack for `equipment_evaluator` apps targeting sterile vent /
tank-breather filtration (e.g. `vent_filter_expert`).

Status: `draft_pending_sme_approval` in `pack.yaml`. Review DIR questionnaires,
option catalog, and prompt fragments before production use.

Design: `docs/EI_APP_TEMPLATE_DESIGN.md`.

## Scenarios

| Scenario id | Use when system_name mentions |
|-------------|-------------------------------|
| `sterile_tank_vent` | vent, tank breather, buffer/hold tank vent (default) |
| `bioreactor_vent` | bioreactor, fermenter, sparge/exhaust vent |

Example DIR (sterile_tank_vent): `2-1-2-3-1-1`

## Reference PPTX

Add style stubs under `references/` and replace private decks:

```powershell
python py\tools\manage_pptx_reference.py --pack filtration list
python py\tools\manage_pptx_reference.py --pack filtration replace --src path\to\deck.pptx --name sterile_tank_vent_filter_evaluation.pptx
```
