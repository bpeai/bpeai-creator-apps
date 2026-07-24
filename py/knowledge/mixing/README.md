# Mixing knowledge pack (production path)

SME pack for `equipment_evaluator` apps. Shared across apps that set
`equipment_system` / `knowledge_pack` to `mixing`.

Design: `docs/EI_APP_TEMPLATE_DESIGN.md`.

## Reference PPTX

`references/*.pptx` in this public repo are **style stubs** (geometry/colors only).
Replace with your private SME decks:

```powershell
python py\tools\manage_pptx_reference.py --pack mixing replace --src path\to\deck.pptx --name media_preparation_vessel_mixing_evaluation.pptx
```
