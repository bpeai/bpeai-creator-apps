# Provider DIR QA matrix

Ship bar for each allowlisted provider: evaluate mixing DIR
`media_preparation` / `2-1-2-3-1-1` and produce schema-valid
`equipment_selector_v1` JSON with required report headings after ≤1 repair.

## How to run

From `bpeai-creator-apps` (with the relevant API keys in `.env`):

```powershell
pip install -e "py/libs/bpeai_creator_sdk[all]"
pytest py/libs/bpeai_creator_sdk/tests/test_provider_dir_qa.py -m llm -v
```

Cases without credentials are skipped. Default CI should not require `-m llm`.

Unit tests (mocked, no network):

```powershell
pytest py/libs/bpeai_creator_sdk/tests/test_llm_providers.py -v
```

## v1 allowlist

| Provider | Model | Key env | Extra |
|----------|-------|---------|-------|
| openai | any (default `gpt-4o`; recommend `gpt-5.2`) | `OPENAI_API_KEY` | (core) |
| anthropic | `claude-sonnet-4-5` | `ANTHROPIC_API_KEY` | `[anthropic]` |
| google | `gemini-2.5-pro` | `GOOGLE_API_KEY` or `GEMINI_API_KEY` | `[google]` |
| xai | `grok-3` | `XAI_API_KEY` | (uses `openai` client) |

Set `CREATOR_LLM_PROVIDER` + optional `CREATOR_LLM_MODEL`. OpenAI still honors
`OPENAI_CREATOR_MODEL` / `OPENAI_MODEL`.

## Results log (fill when run)

| Provider | Model | Pass | Notes |
|----------|-------|------|-------|
| openai | | | |
| anthropic | claude-sonnet-4-5 | | |
| google | gemini-2.5-pro | | |
| xai | grok-3 | | |

Do not expand the allowlist without repeating this DIR matrix for the new model.
