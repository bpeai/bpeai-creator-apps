# EI Handshake Protocol (`ei_handshake_v1`)

Production contract between **EI apps** (authored in `bpeai-creator-apps`) and
**BPEAI processing** (`bpeai.com` / `bpiplatform.bpeai.com` + `vendor_api`).

Designed so thousands of creators and many thousands of apps share one stable
wire format that does not break when individual apps evolve.

---

## Ownership (Option B — cloud library of record)

| Asset | Lives in | Ships via |
|-------|----------|-----------|
| App Python (`agent.py`, `manifest.json`) | Local `py/apps/<id>/` → **S3** zip | Portal / CLI upload; optional backup download |
| Private knowledge pack | Local → **Postgres + S3 snapshot** | Upload; **download before local edit** (packs update on server) |
| EC2 `creator_runtime` | Hot **cache** only (LRU eviction) | Filled on demand from S3 |
| Platform seed packs | `bpeai/py/knowledge/` | BPEAI deploy only |
| Runtime, hub UI, APIs | `bpeai` | BPEAI deploy |
| Shared SDK / templates | Both repos (mirrored) | BPEAI deploy pin |

Creators **must not** edit the deploy repo to ship an app. Upload → Test →
Submit → admin publish is the only creator path.

**Creator sync loop**

```text
download pack (content_version)  →  local edit  →  upload pack
Test / generate DIR  →  server bumps content_version  →  download again before next edit
upload app only when agent/manifest changes (apps are not mutated at runtime)
```

CLI: `download_knowledge_pack.py` (`--zip`), `download_app_bundle.py`, `upload_creator_bundle.py`.  
Quotas: `CREATOR_STORAGE_QUOTA_BYTES` (default 500MB). Cache: `CREATOR_RUNTIME_MAX_APPS` / `CREATOR_RUNTIME_MAX_BYTES`.

---

## Manifest links (required handshake fields)

See `manifest.schema.json`. Critical links:

| Field | Role |
|-------|------|
| `id` | Stable app id (`snake_case`) — runtime key |
| `slug` | Hub URL segment |
| `equipment_system` | Domain routing / taxonomy |
| `template_family` | Deliverable family; defaults to `equipment_evaluator` for legacy manifests |
| `knowledge_pack` | Local pack folder id (upload binds private pack) |
| `python_entrypoint` | `apps.<id>.agent` module path |
| `required_inputs` | UI + validation keys (`system_name`, …) |
| `input_ports` / `output_ports` | Typed composition ports; additive to `required_inputs` |
| `output_schema_version` | Currently `equipment_selector_v1` |
| `handshake_protocol` | `ei_handshake_v1` (optional; defaulted by platform) |
| `route` / `runtime` / `min_tier` / `status` | Hub visibility |

DB also stores `agent_class`, `release_version`, `llm_*`, bound pack id.

---

## Run wire protocol

```text
Browser  →  POST /api/creator-apps/{appId}/run
         ←  { run_id, started, app_id, protocol_version, history_run_id? }

Browser  →  GET  /api/creator-apps/{appId}/stream?run_id=
         ←  SSE events (see below)

Next     →  vendor_api POST /creator-apps/{app_id}/run
         →  vendor_api GET  /creator-apps/{app_id}/stream?run_id=
```

### Request `inputs` (generic)

```json
{
  "phase": "dir",
  "system_name": "Process vessel vent filter",
  "application": "biopharmaceutical",
  "dir_code": "4-1-2-3-2-2",
  "deliverable": "pptx",
  "evaluation_result": {},
  "handshake_protocol": "ei_handshake_v1",
  "history_run_id": "cuid…"
}
```

Platform injects (never trust client for these):

- `knowledge_pack_payload` — full private pack blob
- LLM env overrides from app settings

### SSE events

| Event | Payload | Meaning |
|-------|---------|---------|
| `heartbeat` | `{ "ts": … }` | Keepalive (not silent ping) |
| `status` | string | Human progress line |
| `dir_requirements` | DIR JSON | Questionnaire ready |
| `evaluation` / `result` | result JSON | Evaluation or phase payload |
| `error` | `{ "message" }` | Fatal |
| `done` | `{ "run_id", "status", "protocol_version" }` | Terminal |

### Generic result envelope

Composition-aware consumers use `ei_result_manifest_v1`, whose `outputs[]`
entries contain `port_id`, `schema_ref`, and `value`. For the evaluator,
`result` and `equipment_selection.value` are the unchanged
`equipment_selector_v1` object. Persisted envelopes also carry `run`, `inputs`,
and `artifacts`.
Bare `equipment_selector_v1` results remain valid. SDK adapters
`wrap_evaluator_result` and `unwrap_evaluator_result` convert between forms, and
`validate_output` accepts either form.

```json
{
  "schema_version": "ei_result_manifest_v1",
  "template_family": "equipment_evaluator",
  "run": {},
  "inputs": {},
  "result": { "schema_version": "equipment_selector_v1" },
  "outputs": [{
    "port_id": "equipment_selection",
    "schema_ref": "https://bpeai.com/schemas/equipment-selector/v1",
    "value": { "schema_version": "equipment_selector_v1" }
  }]
}
```

### Result payload extras (`_handshake`)

```json
{
  "_handshake": {
    "protocol_version": "ei_handshake_v1",
    "run_id": "ca-…",
    "app_id": "vent_filter_expert",
    "history_run_id": "cuid…",
    "release_version": "0.2.0",
    "pack_release_version": "0.1.0",
    "knowledge_pack_id": "…"
  },
  "evaluation_options": [],
  "mixing_options": [],
  "artifacts": {
    "markdown_s3_key": "…",
    "markdown_url": "https://…",
    "pdf_s3_key": "…",
    "pdf_url": "https://…",
    "pptx_s3_key": "…",
    "pptx_url": "https://…"
  }
}
```

`evaluation_options` is canonical; `mixing_options` is a **compat alias**
(same array). Clients should prefer `evaluation_options`.

---

## Durability

- Active runs are dual-written: in-process queue **and** Postgres
  `ei_runtime_runs` (survive worker restart / multi-instance stream attach).
- History rows: `creator_app_runs` (linked via `vendor_run_id`).
- Binary artifacts: uploaded to S3 when configured; result carries keys +
  short-lived presigned URLs. Host-local paths are authoring-only fallbacks.

---

## Versioning rules (non-breaking)

1. Additive fields are always OK.
2. Renames keep the old field as alias for at least one major platform release.
3. `output_schema_version` / `handshake_protocol` bumps require dual-read in
   platform before dual-write is removed.
4. Closed `equipment_system` enum expands only via platform release (document
   new values in schema + TS).
