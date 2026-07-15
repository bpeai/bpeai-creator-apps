# SME Creator Playbook (code → test → install → manage)

Updated 2026-07-15

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

### 1.1 Clone once, add apps over time

```powershell
git clone https://github.com/bpeai/bpeai-creator-apps.git
cd bpeai-creator-apps
```

Keep one local clone. For each new selector:

```powershell
Copy-Item -Recurse py\apps\_template py\apps\heat_exchanger_selector
```

(Use your snake_case **id** as the folder name.)

```text
py/apps/<your_id>/
  __init__.py
  agent.py          # class name = portal "Agent class"
  manifest.json     # id / slug / label / …
  README.md         # optional
```

Reference (read-only): `py/apps/examples/mixing_agitator_matcher/`

### 1.2 Recommended order

1. **Code first** — copy template, rename class / `app_id`, implement `run`, local test.
2. **Then portal** — **New app** with matching slug, Python module, Agent class.
3. **Then PR** — BPEAI merges into website `py/apps/` and rebuilds.

You *can* create the portal draft first, but module/class must still match the code you ship.

### 1.3 IDs that must match

| Concept | Example | Notes |
|---------|---------|--------|
| Folder | `py/apps/heat_exchanger_selector/` | snake_case |
| `app_id` in `agent.py` | `heat_exchanger_selector` | Unique |
| Manifest `id` | same | Unique |
| Portal **Slug** | `heat-exchanger-selector` | URL segment; shown read-only on Settings after create |
| Portal **Python module** | `apps.heat_exchanger_selector.agent` | Runtime import path |
| Portal **Agent class** | `HeatExchangerSelectorAgent` | Exact class name in `agent.py` |

### 1.4 Local test

```bash
cd py/apps/<your_id>
echo '{"system_name":"Media Prep Vessel","application":"biopharma"}' | python agent.py
```

- Status → stderr  
- JSON result → stdout  
- Fix validation errors before portal Test  

SDK (same content live): https://bpiplatform.bpeai.com/sdk

---

## 2. Register draft on the portal — Creator

1. https://bpiplatform.bpeai.com → nav **New app** (or Dashboard CTA).
2. Fill slug, label, description, equipment system, Free/Pro/Pro+, Python module, Agent class.
3. Save → **App settings** (`/apps/<id>`). Slug and app id are shown read-only there.

Draft exists in DB. Runtime fails until Python is on the server (next step).

---

## 3. Install Python on the server — Creator + BPEAI

No upload API. Code ships via git.

| Step | Who |
|------|-----|
| PR into `bpeai-creator-apps` with `py/apps/<id>/` | Creator |
| Review, copy into website `bpeai` `py/apps/`, merge | BPEAI |
| EC2 rebuild | BPEAI |

```bash
cd ~/bpeai
git pull origin master
docker compose up -d --build
```

Runtime reads `python_module` + `agent_class` from the `creator_apps` row.

---

## 4. Test on the portal — Creator

1. After deploy: `/apps/<id>/test` → **Run test**
2. Confirm streamed `equipment_selector_v1` result
3. Fix → new PR / redeploy → retest

Import / unknown-app errors → Python not deployed or module/class mismatch.

---

## 5. Submit & publish — Creator + BPEAI

| Step | Who | Where |
|------|-----|--------|
| Submit for review | Creator | `/apps/<id>/submit` |
| Set status → published | BPEAI admin | https://bpeai.com/admin/creator-apps |
| App on hub | system | https://bpeai.com/engineering/equipment-intelligence |
| Users open selector | End users | `/engineering/equipment-intelligence/<slug>` |

Creators cannot self-publish. Mixing keeps a custom UI; other apps use the generic runner.

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
- **Creator:** Profile → clone repo → copy `_template` → code → local test
- **Creator:** New app (module + class + access tier)
- **BPEAI:** Merge into website + `docker compose` rebuild `vendor_api`
- **Creator:** Portal Test → Submit for review
- **BPEAI:** Publish
- **User:** Run on EI hub
- **Creator:** Stats / settings / enable-disable as needed

## Quick role summary

- **Creator owns:** Python logic, draft metadata, testing, submit, profile, stats, post-publish settings (including disable).
- **BPEAI owns:** Access grant, repo merge + server rebuild, review/publish, optional custom UI for complex apps.

Portal SDK page (accurate live guide): https://bpiplatform.bpeai.com/sdk
