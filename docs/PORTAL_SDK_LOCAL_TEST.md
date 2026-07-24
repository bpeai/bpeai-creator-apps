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

Optional personal OpenAI key (local PC only):
  1. Copy .env.example → .env at the repo root (never commit .env)
  2. Set OPENAI_API_KEY=sk-… (your key; BPEAI platform keys are not used locally)
  3. For evaluator quality (match/exceed custom GPT depth), set a strong model, e.g.
     OPENAI_CREATOR_MODEL=gpt-5.2 (or another reasoning-capable model on your account).
     Code default remains gpt-4o if unset. Also set OPENAI_CREATOR_MAX_OUTPUT_TOKENS=16000.
  Local chat prints the resolved LLM model name at startup.

Artifacts (gitignored ./artifacts/): *_evaluation.md, *_evaluation.pdf, optional
*_evaluation.pptx. Portal hub datasheets use datasheet_markdown → S3 .md only.

Start from py/apps/_templates/equipment_evaluator (not the legacy mixing matcher
example). SME packs live under py/knowledge/<system>/. Manage reference PPTX stubs:

  python py/tools/manage_pptx_reference.py --pack mixing list

Rule-based agents work without a key. A key enables richer natural-language
parsing and any self.call_openai_json(…) calls inside your agent.

Advanced — JSON pipe (same contract the server uses):

  cd py/apps/<your_id>
  '{"system_name":"Media Prep Vessel"}' | python agent.py

Status → stderr; JSON → stdout. Fix validation errors before portal Test.

Local chat does not replace portal Test after BPEAI deploys your PR. Multi-phase
DIR → evaluate → PPTX training is primarily via local_chat in this beta.
PORTAL_BODY_END
