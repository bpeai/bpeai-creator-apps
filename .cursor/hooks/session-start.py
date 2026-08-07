#!/usr/bin/env python3
"""sessionStart hook — nudge Agent toward the EI creator wizard.

Requires a trusted workspace. Outputs JSON for Cursor hooks (additional_context).
Always-on rules in AGENTS.md / .cursor/rules remain the reliable fallback.
"""

from __future__ import annotations

import json
import sys

CONTEXT = """
This is the BPEAI **bpeai-creator-apps** authoring repo for Engineered Intelligence (EI) apps.

If the user is starting, unclear, or wants to create/customize an EI app:
1. Follow `.cursor/skills/ei-creator-wizard/SKILL.md` (or treat their message as "Create my EI app").
2. Ask which app they want to build (id, domain / equipment_system, pack approach).
3. Prefer knowledge-pack YAML for prompts and outputs; optional Python via creator_tools.py.
4. Preserve HANDSHAKE boundaries — creators do not edit the website UI.

Portal ship path: https://bpiplatform.bpeai.com → Upload → Test → Submit.
""".strip()


def main() -> int:
    # Read stdin (sessionStart payload) but do not require fields.
    try:
        sys.stdin.read()
    except Exception:
        pass
    # Write UTF-8 bytes (no BOM) — Windows consoles may otherwise emit utf-8-sig.
    payload = json.dumps({"additional_context": CONTEXT}, ensure_ascii=True) + "\n"
    sys.stdout.buffer.write(payload.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
