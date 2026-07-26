# Changelog — bpeai-creator-apps / Creator SDK

## 0.2.0 — 2026-07-26

### Knowledge pack alignment (hybrid)

- **Private creator packs:** Creator-owned knowledge is for that creator’s apps only; platform seeds (`mixing`) remain BPEAI-owned.
- **DIR menus** select by `(equipment_system_variant × industry × scenario)`; legacy scenarios still work as fallback.
- **SDK** `resolve_dir_menu`, `resolve_variant_id`, `resolve_industry`, `knowledge_pack_from_dict` (DB/API hydrate).
- **Evaluate** requires approved menus when lifecycle is present.
- **Taxonomy soft-check** normalizes `applications.yaml` list/object shapes.
- **Docs:** hybrid transfer (git for Python; portal/DB for pack content), ownership rules, creator update channel.
- **Version file:** `CREATOR_SDK_VERSION`.

### How to update

```powershell
cd bpeai-creator-apps
git pull
```

Also check portal **SDK** page for the published version and changelog excerpt.

## 0.1.0 — 2026-07-24

- Initial equipment_evaluator template, mixing pack, local chat, PDF/PPTX artifacts.
