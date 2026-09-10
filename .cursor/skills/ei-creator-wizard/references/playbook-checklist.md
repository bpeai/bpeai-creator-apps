# Clone → wizard (app) → local_chat (pack) → upload

1. **Access** — BPEAI grants `creatorAccess`. Sign in at https://bpiplatform.bpeai.com (apex, not `www`).
2. **Clone** — `git clone https://github.com/bpeai/bpeai-creator-apps.git` (this repo). Open in Cursor; **trust the workspace**.
3. **Wizard** — Agent chat → “Create my EI app” (or `/ei-creator-wizard`). Choose evaluator vs sizing. Cursor copies the family template into `py/apps/<family>/<id>/` and writes identity only — **not** pack YAML.
4. **Identity** — `py/apps/<family>/<id>/` + matching `manifest.json` / class / pack id (= leaf id).
5. **Local pack generate** — creator runs `python py/tools/local_chat.py --app <family>/<id>` in PowerShell (their `.env` keys). First run LLM-bootstraps `py/knowledge/<family>/<id>/`. Optional SME PDFs in `references/content/`; first prompt e.g. `CIP return pump, biopharmaceutical`.
6. **Customize** — pack prompts + catalogs + outlines (after the draft exists).
7. **Upload** — portal Upload zip or `upload_creator_bundle.py`.
8. **Portal** — Test → Submit → admin Publish → hub on https://bpeai.com.

Stay current: `git pull` for SDK/template updates. Never commit `.env` or secrets.

Primary path is Cursor wizard; manual copy steps remain in `CREATOR_PLAYBOOK.md` §1 for non-Cursor users.
