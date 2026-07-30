<!--
  Portal SDK source of truth for section "3. Local test".
  Paste the BODY below (between PORTAL_BODY_START / PORTAL_BODY_END) into
  bpeai/src/lib/creatorSdkDocs.ts → CREATOR_SDK_SECTIONS entry titled "3. Local test".
  Keep this file and creatorSdkDocs.ts in sync when CLI flags change.
-->

# 3. Local test (portal body)

PORTAL_BODY_START
Preferred — local chat (smart text), from your app folder or with --app:

  python py/tools/local_chat.py --app <your_id>
  > Media prep vessel, biopharma, sterile vent
  > 2-1-2-3-1-1
  > pptx

Type plain English, then a DIR code. Status lines print while the agent runs; the
recommendation prints as readable text. After evaluation, reply pptx or y for a
local 7-slide deck. Use --json to dump validated equipment_selector_v1. Use
--once "…" for a one-shot run.

Optional personal LLM key (local PC only):
  1. Copy .env.example → .env at the repo root (never commit .env)
  2. Default provider is OpenAI: set OPENAI_API_KEY=sk-… (BPEAI platform keys are not used locally)
  3. For evaluator quality (match/exceed custom GPT depth), set a strong model, e.g.
     OPENAI_CREATOR_MODEL=gpt-5.2 (or another reasoning-capable model on your account).
     Code default remains gpt-4o if unset. Also set OPENAI_CREATOR_MAX_OUTPUT_TOKENS=16000.
  4. Optional v1 providers (hard allowlist): CREATOR_LLM_PROVIDER=anthropic|google|xai
     with ANTHROPIC_API_KEY / GOOGLE_API_KEY / XAI_API_KEY and allowlisted models
     claude-sonnet-4-5 / gemini-2.5-pro / grok-3. Install extras:
     pip install 'bpeai-creator-sdk[anthropic]' or [google] or [all].
  Local chat prints the resolved provider/model at startup.

Artifacts (gitignored ./artifacts/): *_evaluation.md, *_evaluation.pdf, optional
*_evaluation.pptx. Portal hub datasheets use datasheet_markdown → S3 .md only.

Start from py/apps/_templates/equipment_evaluator (not the legacy mixing matcher
example). Copy the template to py/apps/<your_id> for local work — creator apps and
py/knowledge/<pack>/ drafts are gitignored; this repo commits templates + `_examples/`
stubs only. Platform SME packs live in the bpeai deploy repo. DIR phase match-or-generates
questionnaires (numeric common codes) into your local pack catalog. Manage reference
PPTX stubs against bpeai seeds:

  python py/tools/manage_pptx_reference.py --pack mixing list

Rule-based agents work without a key. A key enables richer natural-language
parsing and any self.call_openai_json(…) / call_llm_json(…) calls inside your agent.

Advanced — JSON pipe (same contract the server uses):

  cd py/apps/<your_id>
  '{"system_name":"Media Prep Vessel"}' | python agent.py

Status → stderr; JSON → stdout. Fix validation errors before portal Test.

Local chat does not replace portal Test after BPEAI deploys your PR. Multi-phase
DIR → evaluate → PPTX training is primarily via local_chat in this beta.
PORTAL_BODY_END
