# Shared style shells (by template family)

Canonical visual references for creator pack bootstrap. Each EI template family
has its own folder; bootstrap copies that family's files into the pack's
`references/style/` (never overwriting creator edits).

```
style/
  equipment_evaluator/   # evaluation DOCX / PPTX shells + brand.yaml
  equipment_sizing/      # sizing DOCX / PPTX / XLSX shells + brand.yaml
  <future_family>/       # add a folder named for the template_family id
```

Supported seed files:

- Evaluator: `default evaluator style example.{pptx,docx}` (optional `.pdf`)
- Sizing: `default sizing style example.{pptx,docx,xlsx}`

plus `brand.yaml` and optional `logo.png` / `.jpg` / `.jpeg` / `.webp`.

## Creator branding

Runtime colors/fonts/logo come from the **pack** copy of:

- `references/style/brand.yaml` — company colors and fonts
- `references/style/logo.png` (optional) — header/cover mark

`default … style example.*` Office files are **visual examples only** (open them
to see the intended look). Editing those files does not change generated output —
edit `brand.yaml` (and drop a logo) instead. Reseed never overwrites files once
present.

Staging copies also live under `website/references/<family> style/` for local
editing; prefer committing updates here so creator-apps can seed without a
website checkout.
