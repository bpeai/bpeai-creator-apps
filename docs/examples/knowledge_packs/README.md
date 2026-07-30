# Knowledge pack examples

**Production platform seeds do not live in creator-apps.**

| Where | What |
|-------|------|
| `bpeai/py/knowledge/<id>/` | Canonical platform seeds (`mixing`, `filtration`, …) |
| Portal → Knowledge | Creator-owned private packs |
| [`py/knowledge/_examples/`](../../../py/knowledge/_examples/) | Thin stubs for local SDK tests (committed) |
| `py/knowledge/<id>/` (local) | Creator drafts + runtime DIR catalog (**gitignored**) |

DIR menus use a list catalog (`dir_menus`) with numeric starter codes and optional
`dir_catalog.md` for SME review. The `equipment_evaluator` template match-or-generates
menus for unique runs.

See `docs/EI_APP_TEMPLATE_DESIGN.md` for the hybrid ownership model.
