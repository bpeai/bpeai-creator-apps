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

See `docs/EI_AI_HANDSHAKES.md` for the full when/why inventory (`dir_search`,
`dir_generate`, `evaluate_search`, `evaluate`, `evaluate_repair`, `pptx`,
`pack_bootstrap`).

## Prompt fragment keys (`fragments`)

`role`, `scope`, `application_default`, `evaluation_goals`, `workflow`, `output_style`, `depth_requirements`, `response_outline`, `exclusions_rule`

Optional pack meta: `prompt_hooks.emphasize` (list).

## Call keys (`calls`)

`dir_generate.system` / `.instructions` · `evaluate.user_instructions` ·
`evaluate_repair.instructions` · `pptx.system_extra` / `.instructions` ·
`pack_bootstrap.system`

## Output contract

- Schema: `equipment_selector_v1`
- Canonical options field: `evaluation_options` (alias `mixing_options`)
- Hub stores `datasheet_markdown` as S3 `.md`

See `docs/EI_CREATOR_EXTENSIONS.md`.
