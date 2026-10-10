# Shared knowledge-pack style templates

Committed visual shells used when a creator EI app bootstraps a **new** local
knowledge pack. Style is organized **by template family**:

```
references/style/
  equipment_evaluator/   # evaluation DOCX / PPTX + brand.yaml
  equipment_sizing/      # sizing DOCX / PPTX / XLSX + brand.yaml
```

On pack bootstrap, the SDK copies that family’s files into the pack’s
`references/style/` (never overwrites files already there). Supported seeds:
`default evaluator style example.*` / `default sizing style example.*`,
`brand.yaml`, and optional `logo.*`.

## Creator branding

Runtime colors/fonts/logo come from the **pack** copy of:

- `references/style/brand.yaml`
- `references/style/logo.png` (optional)

`default … style example.*` files are visual examples only; edit `brand.yaml`
(+ logo) to distinguish deliverables. Reseed does not overwrite those files
once present.

## Legacy flat files

Older flat `references/*.pptx` / `*.pdf` may still exist for continuity. Prefer
the per-family `references/style/<template_family>/` layout above.

## Override

Set `BPEAI_TEMPLATE_REFERENCES_ROOT` to point at another style root (family
subfolders or a single flat folder). Env wins over this committed tree.
