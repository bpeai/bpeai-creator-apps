# SME Creator Playbook (code → test → install → manage)

Updated 2026-07-26 · SDK [`CREATOR_SDK_VERSION`](./CREATOR_SDK_VERSION) · [`CHANGELOG.md`](./CHANGELOG.md)

## Hosts

| Host | Purpose |
|------|---------|
| **Creators** | https://bpiplatform.bpeai.com (use **apex**, not `www`) |
| **Users / BPEAI admin** | https://bpeai.com |

`www.bpiplatform.bpeai.com` redirects to the apex. Creator chrome (Dashboard, Stats, Profile, SDK, New app) only appears on the platform host. The main-site sidebar is for `bpeai.com` product work (projects, engineering, etc.).

## Roles

| Role | Who | Can |
|------|-----|-----|
| Third-party creator (SME) | User with `creatorAccess` | Write Python, portal draft/settings, local + portal test, submit for review, manage own profile/stats, enable/disable own published apps |
| BPEAI admin | `tier === ADMIN` | Grant/revoke creator access, merge PRs, rebuild `vendor_api`, publish/deprecate any app, platform analytics |
| End user | Normal bpeai.com account | Run **published** apps on the EI hub (tier-gated) |

---

## 0. Onboard the creator — BPEAI

1. Creator registers/logs in on **bpeai.com** (same account works on both hosts). Creator access is required to use the portal.
2. Admin → https://bpeai.com/admin/creator-apps (sidebar **Admin → Creator apps**) → search by email → **Grant access**.
3. System emails the creator with the portal link and next steps (when SES is configured).
4. Tell the creator to open **https://bpiplatform.bpeai.com** and sign in (lands on creator dashboard).
5. Optional: creator fills **Profile** (`/profile` on the portal) — display name, company, bio, payout email.

**Profiles:** Portal **Profile** stores `CreatorProfile` (attribution / payout). Account **Profile** on bpeai.com stores `User` fields. They are separate today; use creator Profile for hub attribution.

If they lack access → `/platform/forbidden`.

---

## 1. Write the Python app — Creator

Work in the dedicated GitHub repo: **[bpeai/bpeai-creator-apps](https://github.com/bpeai/bpeai-creator-apps)** (not the website deploy repo).

**Platform note (templates):** EI apps use a **template family** (by deliverable) + **SME knowledge pack** + **shared SDK**. Start from `py/apps/_templates/equipment_evaluator`. See [docs/EI_APP_TEMPLATE_DESIGN.md](./docs/EI_APP_TEMPLATE_DESIGN.md).

**Knowledge ownership:** Your pack content is **private to your apps** (portal-managed). Platform seeds under `py/knowledge/` (e.g. `mixing`) are BPEAI-owned; bind them or **clone** into a private pack on the portal. Do not expect other creators to see your pack. Python agent code still ships only via git PR (no zip upload).

### 1.1 Clone once, add apps over time

```powershell
git clone https://github.com/bpeai/bpeai-creator-apps.git
cd bpeai-creator-apps
```

Keep one local clone. Pull regularly for SDK/template updates (`git pull`). For each new evaluator app:

```powershell
Copy-Item -Recurse py\apps\_templates\equipment_evaluator py\apps\heat_exchanger_evaluator
```

(Use your snake_case **id** as the folder name.)

### 1.2 Intended tree (upload / PR clarity)

```text
py/apps/_templates/equipment_evaluator/   # copy source — do not edit in place for your app
py/apps/<your_id>/                        # your app (open a PR that adds this)
py/knowledge/<system>/                    # platform seed packs only (BPEAI); your packs live in portal/DB
py/libs/bpeai_creator_sdk/                # do not fork; BPEAI mirrors into website deploy
```

**Size guidance:** keep pack YAML-first for seeds; manage creator DIR menus in portal **Knowledge**. Local sync: `python py/tools/sync_knowledge_pack.py`. Never commit `.env` or generated `artifacts/` (PDF/MD/PPTX).

### 1.3 How creators get SDK / template updates

1. `git pull` on this repo.
2. Portal **SDK** page shows `CREATOR_SDK_VERSION` + changelog excerpt.
3. Major bumps may email users with creator access.
4. Read [`CHANGELOG.md`](./CHANGELOG.md) for breaking changes.

App folder contents:

```text
py/apps/<your_id>/
  __init__.py
  agent.py          # class name = portal "Agent class"
  manifest.json     # id / slug / label / equipment_system / knowledge_pack …
  README.md         # optional
```

**Do not copy** `py/apps/examples/mixing_agitator_matcher/` — that example is **legacy** (in-code DIR, not pack-backed).

### 1.3 Recommended order

1. **Code first** — copy template, rename class / `app_id` / `knowledge_pack_id`, local test.
2. **Then portal** — **New app** with matching slug, Python module, Agent class.
3. **Then PR** — BPEAI merges into website `py/apps/` (+ mirrors SDK/packs as needed) and rebuilds.

You *can* create the portal draft first, but module/class must still match the code you ship.

### 1.4 IDs that must match

| Concept | Example | Notes |
|---------|---------|--------|
| Folder | `py/apps/heat_exchanger_evaluator/` | snake_case |
| `app_id` in `agent.py` | `heat_exchanger_evaluator` | Unique |
| Manifest `id` | same | Unique |
| Portal **Slug** | `heat-exchanger-evaluator` | URL segment; shown read-only on Settings after create |
| Portal **Python module** | `apps.heat_exchanger_evaluator.agent` | Runtime import path |
| Portal **Agent class** | `HeatExchangerEvaluatorAgent` | Exact class name in `agent.py` |
| Knowledge pack | `mixing` (or your pack id) | `py/knowledge/<pack>/`; manifest `knowledge_pack` optional (defaults to `equipment_system`) |

### 1.5 Local test

**Preferred — local chat (smart text):**

```powershell
python py\tools\local_chat.py --app <your_id>
# > Media prep vessel, biopharma
# > 2-1-2-3-1-1
# > pptx
```

- Type plain English, then a DIR code; recommendation prints as readable text
- After evaluation, reply `pptx` / `y` for a 7-slide deck (local artifact)
- Artifacts write under `./artifacts/` (gitignored): markdown + PDF report; optional PPTX
- Optional: copy `.env.example` → `.env` and set personal `OPENAI_API_KEY` (never commit)
- For evaluator depth: `OPENAI_CREATOR_MODEL=gpt-5.2` and `OPENAI_CREATOR_MAX_OUTPUT_TOKENS=16000` (code default remains `gpt-4o`)
- Multi-provider (v1 allowlist): set `CREATOR_LLM_PROVIDER` to `openai` (default), `anthropic`, `google`, or `xai`, plus the matching API key. Non-OpenAI models are hard-allowlisted (`claude-sonnet-4-5`, `gemini-2.5-pro`, `grok-3`). See [docs/PROVIDER_DIR_QA.md](./docs/PROVIDER_DIR_QA.md).
- `--json` dumps validated `equipment_selector_v1`; `--once "…"` for one-shot

**Reference PPTX management (SME):**

```powershell
python py\tools\manage_pptx_reference.py --pack mixing list
python py\tools\manage_pptx_reference.py --pack mixing replace --src path\to\deck.pptx --name media_preparation_vessel_mixing_evaluation.pptx
```

**Advanced — JSON pipe** (same contract the server uses):

```powershell
cd py\apps\<your_id>
'{"system_name":"Media Prep Vessel","application":"biopharma"}' | python agent.py
```

- Status → stderr; JSON → stdout
- Fix validation errors before portal Test

Canonical portal copy: [docs/PORTAL_SDK_LOCAL_TEST.md](./docs/PORTAL_SDK_LOCAL_TEST.md)  
SDK (same content live after website deploy): https://bpiplatform.bpeai.com/sdk

**Portal vs local formats:** Hub datasheets use **`datasheet_markdown` → S3 `.md`**. Local PDF/PPTX are for authoring review only unless product later adds binary upload.

---

## 2. Register draft on the portal — Creator

1. https://bpiplatform.bpeai.com → nav **New app** (or Dashboard CTA).
2. Fill slug, label, description, equipment system, Free/Pro/Pro+, Python module, Agent class.
3. Save → **App settings** (`/apps/<id>`). Slug and app id are shown read-only there.

Draft exists in DB. Runtime fails until Python is on the server (next step).

---

## 3. Install Python on the server — Creator + BPEAI

**No upload API.** Code ships via git PR. BPEAI mirrors `py/apps/<id>/`, and as needed `py/knowledge/` + `bpeai_creator_sdk`, into the website deploy repo.

| Step | Who |
|------|-----|
| PR into `bpeai-creator-apps` with `py/apps/<id>/` | Creator |
| Review, copy into website `bpeai` `py/`, merge | BPEAI |
| EC2 rebuild | BPEAI |

```bash
cd ~/bpeai
git pull origin master
docker compose up -d --build
```

Runtime reads `python_module` + `agent_class` from the `creator_apps` row.

**Security:** never commit API keys; use `.env` locally only; PRs are reviewed before merge. Platform OpenAI/Serper keys are not used for creator local test.

---

## 4. Test on the portal — Creator

1. After deploy: `/apps/<id>/test` → **Run test**
2. Confirm streamed `equipment_selector_v1` result
3. Fix → new PR / redeploy → retest

Import / unknown-app errors → Python not deployed or module/class mismatch.

Multi-phase DIR → evaluate → PPTX training is done primarily via **local_chat**. Portal Test remains a basic smoke check for this beta.

---

## 5. Submit & publish — Creator + BPEAI

| Step | Who | Where |
|------|-----|--------|
| Submit for review | Creator | `/apps/<id>/submit` |
| Set status → published | BPEAI admin | https://bpeai.com/admin/creator-apps |
| App on hub | system | https://bpeai.com/engineering/equipment-intelligence |
| Users open selector | End users | `/engineering/equipment-intelligence/<slug>` |

Creators cannot self-publish. The first-party Mixing Agitator Matcher keeps a custom UI (legacy); new evaluator apps use the generic runner unless BPEAI adds a custom UI.

---

## 6. Manage after publish — Creator

| Task | Where |
|------|--------|
| Edit name, description, Free/Pro/Pro+ | `/apps/<id>` (Settings) — use **Back to dashboard** to leave |
| Disable / enable | Settings → Disable / Enable |
| Usage stats | `/platform/stats` |
| Author profile | `/platform/profile` |
| Retest | `/apps/<id>/test` |

BPEAI can still change any app’s status and view `/admin/creator-analytics`.

**Ops note:** Prefer emailing creators when access is granted (automated), and when an app is published or needs changes (admin process until fully automated).

---

## End-to-end checklist

- **BPEAI:** Grant `creatorAccess` (email sent)
- **Creator:** Profile → clone repo → copy `_templates/equipment_evaluator` → rename ids → local_chat → local MD/PDF/PPTX
- **Creator:** New app (module + class + access tier)
- **BPEAI:** Merge into website + `docker compose` rebuild `vendor_api`
- **Creator:** Portal Test → Submit for review
- **BPEAI:** Publish
- **User:** Run on EI hub (markdown datasheet)
- **Creator:** Stats / settings / enable-disable as needed

## Quick role summary

- **Creator owns:** Python logic, draft metadata, testing, submit, profile, stats, post-publish settings (including disable).
- **BPEAI owns:** Access grant, repo merge + server rebuild, review/publish, optional custom UI for complex apps.

Portal SDK page (accurate live guide): https://bpiplatform.bpeai.com/sdk
