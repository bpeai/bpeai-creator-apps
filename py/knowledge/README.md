# Knowledge in creator-apps

| Location | Purpose | In git? |
|----------|---------|---------|
| `py/knowledge/_examples/` | Thin stubs for local SDK / template tests | Yes |
| `py/knowledge/_templates/references/` | Shared PPTX/PDF **style** shells for new packs | Yes |
| `py/knowledge/<id>/` | **Creator workspace drafts** (bootstrap / runtime DIR catalog) | **No** (gitignored) |
| `bpeai` website `py/knowledge/<id>/` | Platform seeds owned by BPEAI | In bpeai deploy repo |
| Portal Knowledge | Creator-owned private packs + DIR CRUD | Portal / Postgres + S3 |

## Ownership model

- Pack **YAML content** for a creator EI app is authored on the creator side
  (LLM bootstrap → runtime DIR generate/append → SME review/approval).
- Do not copy website pack YAML into a creator pack unless that creator originally owned it.
- Shared **style templates** (`_templates/references/*.pptx` / `*.pdf`) seed into each new
  pack’s `references/style/` on bootstrap. Creator technical PDFs/docs belong in
  `references/content/` (indexed for LLM as a supplement to web search). Filenames
  are not required to be standardized. Override style source with
  `BPEAI_TEMPLATE_REFERENCES_ROOT` or replace per pack via `manage_pptx_reference.py`.
- Creator apps under `py/apps/<your_id>/` (copies of `_templates/equipment_evaluator`) are
  also gitignored — open PRs only when BPEAI’s publish process explicitly asks for app code.

## DIR catalog (SME-readable)

Preferred shape in `dir_requirements.yaml`:

- `dir_menus:` list of self-contained menus (`menu_id`, `status`, variant, industry,
  requirements, numeric `common_codes` with captions)
- Companion `dir_catalog.md` table for review

Runtime **match-or-generate** appends `draft_generated` rows for unique cases. See
`docs/EI_APP_TEMPLATE_DESIGN.md` and `py/apps/_templates/equipment_evaluator/README.md`.

Do not open PRs that promote unreviewed full SME packs as platform seeds from this directory.
