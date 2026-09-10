# Mixing sizing stub (EXAMPLE ONLY)

This is **not** a platform production knowledge pack.

Use this stub for `equipment_sizing` SDK tests only. Do **not** copy it as a live
starter pack. Evaluator tests must keep using `_examples/mixing_stub/`.

```python
from bpeai_creator_sdk.sme import load_knowledge_pack, knowledge_root

examples = knowledge_root() / "_examples"
pack = load_knowledge_pack("mixing_sizing_stub", pack_root=examples)
```
