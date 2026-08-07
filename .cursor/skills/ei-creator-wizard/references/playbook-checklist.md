# Clone → customize → local_chat → upload

1. **Access** — BPEAI grants `creatorAccess`. Sign in at https://bpiplatform.bpeai.com (apex, not `www`).
2. **Clone** — `git clone https://github.com/bpeai/bpeai-creator-apps.git` (this repo). Open in Cursor; **trust the workspace**.
3. **Wizard** — Agent chat → “Create my EI app” (or `/ei-creator-wizard`).
4. **Identity** — `py/apps/<id>/` + matching `manifest.json` / class / pack id.
5. **Pack** — private pack prompts + catalogs + outlines (not platform seed bind).
6. **Local test** — `python py/tools/local_chat.py --app <id>` (DIR → code → evaluate; optional pptx).
7. **Upload** — portal Upload zip or `upload_creator_bundle.py`.
8. **Portal** — Test → Submit → admin Publish → hub on https://bpeai.com.

Stay current: `git pull` for SDK/template updates. Never commit `.env` or secrets.

Primary path is Cursor wizard; manual copy steps remain in `CREATOR_PLAYBOOK.md` §1 for non-Cursor users.
