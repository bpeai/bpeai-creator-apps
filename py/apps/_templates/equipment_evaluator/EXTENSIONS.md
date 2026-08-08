# Extensions for this template

Creators customize **prompts**, **search queries**, and **outputs** via the
knowledge pack first. Optional Python helpers live in [`creator_tools.py`](./creator_tools.py).

**AI handshakes (LLM + Serper inventory):**  
→ [`docs/EI_AI_HANDSHAKES.md`](../../../docs/EI_AI_HANDSHAKES.md)

Full guide (prompt/output dials, UI capability matrix):  
→ [`docs/EI_CREATOR_EXTENSIONS.md`](../../../docs/EI_CREATOR_EXTENSIONS.md)

Wire protocol: [`docs/EI_HANDSHAKE.md`](../../../docs/EI_HANDSHAKE.md)

Pack dials:

- `prompt_fragments.yaml` — `fragments` (evaluate system) + `calls` (per-handshake)
- `search_queries.yaml` — Serper templates / static queries

Look for **`HANDSHAKE:`** (UI wire) and **`AI_HANDSHAKE:`** (LLM/search) comments
in [`agent.py`](./agent.py). Do not invent new SSE events or UI buttons; you do
not have access to hub/portal React code.
