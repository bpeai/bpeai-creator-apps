# Customization map

| Goal | Safe dial (prefer) | Advanced (Python) | Do not touch |
|------|--------------------|-------------------|--------------|
| LLM prompts / SME voice | Pack `prompt_fragments.yaml` → `fragments` + `calls` | Light edits to pack-driven user messages | Template JSON schema contracts in `agent.py` unless changing deliverable |
| Web search queries | Pack `search_queries.yaml` (templates + static) | Custom Serper helpers in `creator_tools.py` | Hard-coding vendor queries in `agent.py` |
| Creator PDF/docs | Pack `references/content/` (indexed; supplements Serper) | — | Replacing web search with pack files only; `.docx` (not indexed) |
| Initial pack YAML | First `local_chat.py` run (`pack_bootstrap`, creator `.env` keys) | — | Cursor writing `pack.yaml` / outlines before Python runs |
| Outputs / report shape | `report_outline.yaml`, `equipment_options.yaml`, `validation_rules.yaml`, `dir_requirements.yaml` | Post-process validated `equipment_selector_v1` before return | New SSE events or hub schema fields without platform support |
| Optional tools | SDK: `call_llm_json`, `serper_search`, `status()` | Helpers in `creator_tools.py` invoked from `run()` | Editing hub/portal React; assuming new UI buttons |

## AI handshake pack files

See `docs/EI_AI_HANDSHAKES.md` for the full when/why inventory.

**Evaluator family:** `dir_search`, `dir_generate`, `evaluate_search`,
`evaluate`, `evaluate_repair`, `pptx`, `pack_bootstrap`.

**Sizing family:** `dir_search`, `dir_generate`, `sizing_plan`, `sizing_search`,
`sizing_capacity`, `sizing_connections`, `sizing_dimensions`, `sizing_report`,
`sizing_repair`, `pptx`, `pack_bootstrap`. Do not emit `evaluate` /
`evaluate_repair`.

## Prompt fragment keys (`fragments`)

`role`, `scope`, `application_default`, `evaluation_goals`, `workflow`, `output_style`, `depth_requirements`, `response_outline`, `exclusions_rule`

Optional pack meta: `prompt_hooks.emphasize` (list).

## Call keys (`calls`)

Shared: `dir_generate.system` / `.instructions` · `pptx.system_extra` /
`.instructions` · `pack_bootstrap.system`

Evaluator: `evaluate.user_instructions` · `evaluate_repair.instructions`

Sizing: `sizing_plan` · `sizing_capacity` · `sizing_connections` ·
`sizing_dimensions` · `sizing_report` · `sizing_repair.instructions`

## Output contract

- Evaluator schema: `equipment_selector_v1`
- Sizing schema: `equipment_sizing_v1` (optional `excel_ready_table`)
- Canonical options field (evaluator): `evaluation_options` (alias `mixing_options`)
- Hub stores `datasheet_markdown` as S3 `.md`; local sizing also writes Word/Excel

See `docs/EI_CREATOR_EXTENSIONS.md`.
