# Mixing stub (EXAMPLE ONLY)

This is **not** a platform production knowledge pack.

- Canonical mixing seed: **bpeai** deploy repo → `py/knowledge/mixing/`
- Creator private packs: portal **Knowledge** (Postgres)

Use this stub for:

- `pytest` in `bpeai_creator_sdk`
- Offline template smoke tests when no portal payload is available

Do **not** use this folder as the LLM bootstrap reference for new creator packs.
Authoring-time shape examples live in `_examples/equipment_evaluator_stub/`.

Load via explicit pack root:

```python
from pathlib import Path
from bpeai_creator_sdk.sme import load_knowledge_pack, knowledge_root

examples = knowledge_root() / "_examples"
pack = load_knowledge_pack("mixing_stub", pack_root=examples)
```
