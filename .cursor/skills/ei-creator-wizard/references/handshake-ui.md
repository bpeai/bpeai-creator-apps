# Handshake ↔ web UI

Creators have **no** access to hub/portal React. The generic runner understands only the stable wire protocol (`ei_handshake_v1`). Full detail: `docs/EI_HANDSHAKE.md`.

## Phases

| Phase / trigger | UI meaning |
|-----------------|------------|
| `dir` / no `dir_code` | Show DIR questionnaire |
| valid `dir_code` / evaluate | Show evaluation result |
| `pptx` / `deliverable=pptx` | PPTX path |
| `generate_dir` | Force DIR generate |

## SSE events (do not invent new names)

`heartbeat` · `status` (from `self.status`) · `dir_requirements` · `evaluation` / `result` · `error` · `done`

## Capability matrix (summary)

| Capability | Creator-customizable? |
|------------|------------------------|
| DIR + evaluate + status + markdown report | Yes (pack + agent within schema) |
| PPTX | Partial via SDK artifacts |
| Custom buttons / new SSE / custom chat tools | **No** — platform request |
| Legacy MixingAgitatorMatcher UI | First-party only — do not copy |

Look for **`HANDSHAKE:`** comments in `py/apps/_templates/equipment_evaluator/agent.py` and `creator_tools.py`.
