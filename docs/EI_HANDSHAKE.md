# EI Handshake Protocol (`ei_handshake_v1`)

Canonical copy also lives in the website deploy repo:
`bpeai/docs/EI_HANDSHAKE.md`. Keep them aligned when changing the wire format.

Production contract between **EI apps** (this repo) and **BPEAI processing**
(`bpeai.com` / `bpiplatform.bpeai.com` + `vendor_api`).

---

## Ownership

| Asset | Lives in | Ships via |
|-------|----------|-----------|
| App Python (`agent.py`, `manifest.json`) | `py/apps/<id>/` (gitignored locally) | **Portal zip upload** (primary) |
| Private knowledge pack | `py/knowledge/<pack>/` → portal | Same upload zip / Knowledge UI |
| Platform seed packs | website `bpeai/py/knowledge/` | BPEAI deploy only |
| Shared SDK / templates | This repo + mirrored into website | BPEAI deploy pin |

Creators **must not** edit the website deploy repo to ship an app.

### Upload (preferred)

```powershell
$env:BPEAI_PLATFORM_URL = "https://bpiplatform.bpeai.com"
$env:BPEAI_SESSION_COOKIE = "your_session_cookie"
python py/tools/upload_creator_bundle.py --apps my_app --packs my_pack
```

Or portal **New app → Upload**. Then Test → Submit → admin publish.

---

## Manifest links

Required: `id`, `slug`, `label`, `equipment_system`, `author`, `app_kind`,
`output_schema_version`, `route`, `runtime`, `status`, plus
`python_entrypoint` and `required_inputs` for evaluators.

Recommended: `knowledge_pack`, `handshake_protocol: "ei_handshake_v1"`,
`version` (semver), optional `llm_model` / `llm_provider`.

See `py/libs/bpeai_creator_sdk/manifest.schema.json`.

---

## Run wire protocol (summary)

1. `POST /api/creator-apps/{appId}/run` with `{ project_id, inputs }`
2. SSE `GET /api/creator-apps/{appId}/stream?run_id=`
3. Events: `heartbeat`, `status`, `dir_requirements`, `evaluation`/`result`,
   `error`, `done`
4. Result includes `_handshake` and `artifacts` with S3 keys/URLs when available
5. Prefer `evaluation_options` over legacy alias `mixing_options`

Full detail: keep this file in sync with `bpeai/docs/EI_HANDSHAKE.md`.
