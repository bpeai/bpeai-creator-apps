# Changelog — bpeai-creator-apps / Creator SDK

## 0.2.2 — 2026-08-08

### SME AI handshakes (pack-owned prompts + search)

- Documented every LLM/Serper call: `docs/EI_AI_HANDSHAKES.md`.
- Pack dials: `prompt_fragments.yaml` → `calls.*` and new optional `search_queries.yaml`.
- SDK `KnowledgePack.call_fragment` / `build_search_queries` with domain-neutral fallbacks.
- `equipment_evaluator` agent uses pack dials; template keeps JSON schema contracts only.
- Mixing seed + `mixing_stub` ship `search_queries.yaml` and `calls` (vendor queries moved out of agent.py).

## 0.2.1 — 2026-07-26

### Knowledge packs: examples only in this repo

- Removed production `py/knowledge/mixing/` and `py/knowledge/filtration/` from creator-apps.
- Canonical platform seeds live in **bpeai** `py/knowledge/`.
- Added `py/knowledge/_examples/mixing_stub/` for local SDK unit tests.
- Mirror script/workflow no longer treat production knowledge as creator-apps content.
- Integration tests that need full mixing load from `BPEAI_KNOWLEDGE_ROOT` or sibling `bpeai/py/knowledge`.

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
