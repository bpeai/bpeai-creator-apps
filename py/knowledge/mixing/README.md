# Mixing knowledge pack (platform seed)

SME pack for `equipment_evaluator` apps. **Platform-owned** seed (`owner = null` in DB).

Creators may:

- Bind this pack to their apps, or
- **Clone** it into a private pack on the portal (Knowledge → Clone) and edit DIR menus for their apps only.

Shared across **one creator’s** apps when they bind/clone it — not a marketplace for other creators.

DIR menus select by `(equipment_system_variant × industry × scenario)`. See `dir_requirements.yaml` `menus:` and `docs/EI_APP_TEMPLATE_DESIGN.md`.

Design: `docs/EI_APP_TEMPLATE_DESIGN.md`.

## Reference PPTX

`references/*.pptx` in this public repo are **style stubs** (geometry/colors only).
Replace with your private SME decks:

```powershell
python py\tools\manage_pptx_reference.py --pack mixing replace --src path\to\deck.pptx --name media_preparation_vessel_mixing_evaluation.pptx
```
