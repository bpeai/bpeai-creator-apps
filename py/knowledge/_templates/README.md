# Shared knowledge-pack style templates

Committed visual shells used when a creator EI app bootstraps a **new** local
knowledge pack under `py/knowledge/<pack_id>/`.

| Path | Purpose |
|------|---------|
| `references/*.pptx` | Style guide for local evaluation decks |
| `references/*.pdf` | Style guide for local evaluation reports |

## Naming policy

**Any** `*.pptx` / `*.pdf` in `references/` is a seed template. Filenames do **not**
need to match historical mixing examples.

On pack bootstrap, SDK copies every matching file into
`py/knowledge/<pack_id>/references/` (never overwrites files already there).

After seed:

- Prefer `pptx_outline.yaml` → `reference_decks` when choosing a PPTX style source
- Else use any `*.pptx` present under the pack’s `references/`
- Creators may replace or add decks with any name via
  `python py/tools/manage_pptx_reference.py --pack <id> replace --src …`

Historical seed names (kept for continuity with website staging):

- `chromatography_resin_slurry_tank_agitator_evaluation.pptx`
- `media_preparation_vessel_mixing_evaluation.pdf`

These are **style-only** (layout / fonts / colors). They are not domain content
for filtration, chromatography, etc.

## Override

Set `BPEAI_TEMPLATE_REFERENCES_ROOT` to point at another folder of `*.pptx`/`*.pdf`
(e.g. a private SME library). Env wins over this committed folder.
