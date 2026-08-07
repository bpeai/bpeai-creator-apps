# Extensions for this template

Creators customize **prompts** and **outputs** via the knowledge pack first.
Optional Python helpers live in [`creator_tools.py`](./creator_tools.py).

Full guide (prompt dial, output dial, handshake, UI capability matrix):

→ [`docs/EI_CREATOR_EXTENSIONS.md`](../../../docs/EI_CREATOR_EXTENSIONS.md)

Wire protocol: [`docs/EI_HANDSHAKE.md`](../../../docs/EI_HANDSHAKE.md)

Look for **`HANDSHAKE:`** comments in [`agent.py`](./agent.py) — those mark
links the generic web UI already understands. Do not invent new SSE events or
UI buttons; you do not have access to hub/portal React code.
