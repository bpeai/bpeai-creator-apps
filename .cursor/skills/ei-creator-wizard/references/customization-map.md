# Customization map

| Goal | Safe dial (prefer) | Advanced (Python) | Do not touch |
|------|--------------------|-------------------|--------------|
| LLM prompts / SME voice | Pack `prompt_fragments.yaml` via `KnowledgePack.build_system_prompt()` | Light edits to pack-driven user messages | Hard-coded `DIR_GENERATE_PROMPT` / `EVALUATION_PROMPT` / `PPTX_SLIDE_PACK_PROMPT` unless changing deliverable contract |
| Outputs / report shape | `report_outline.yaml`, `equipment_options.yaml`, `validation_rules.yaml`, `dir_requirements.yaml` | Post-process validated `equipment_selector_v1` before return | New SSE events or hub schema fields without platform support |
| Optional tools | SDK: `call_llm_json`, `serper_search`, `status()` | Helpers in `creator_tools.py` invoked from `run()` | Editing hub/portal React; assuming new UI buttons |

## Prompt fragment keys

`role`, `scope`, `application_default`, `evaluation_goals`, `workflow`, `output_style`, `depth_requirements`, `response_outline`, `exclusions_rule`

Optional pack meta: `prompt_hooks.emphasize` (list).

## Output contract

- Schema: `equipment_selector_v1`
- Canonical options field: `evaluation_options` (alias `mixing_options`)
- Hub stores `datasheet_markdown` as S3 `.md`

See `docs/EI_CREATOR_EXTENSIONS.md`.
