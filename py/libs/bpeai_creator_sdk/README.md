# bpeai-creator-sdk

SDK for BPEAI Equipment Intelligence creator apps.

## Contract

- **Manifest** (`CreatorAppManifest`): app identity, equipment system, inputs, routing.
- **Output** (`EquipmentSelectorOutput`, schema version `equipment_selector_v1`): structured result card for Project Tray and equipment-list insert.
- **Base class** (`CreatorAppBase`): status callbacks, OpenAI JSON calls, Serper search.

## Authoring guide (SME)

### 1. Copy the template

```text
py/apps/_template/                 ← start here
py/apps/mixing_agitator_matcher/   ← full reference (DIR workflow)
```

Copy `_template` to `py/apps/<your_slug>/`, rename the agent class and `app_id`, and edit `manifest.json`.

### 2. Implement `run(inputs)`

```python
from bpeai_creator_sdk import (
    CreatorAppBase,
    EquipmentSelectorOutput,
    KeySpecValue,
    validate_output,
)

class MyApp(CreatorAppBase):
    app_id = "my_app"

    def run(self, inputs: dict) -> dict:
        self.status("Running evaluation…")
        output = EquipmentSelectorOutput(
            equipment_tag="EQ-101",
            selected_model="Model A",
            equipment_system="mixing",
            key_specs=[KeySpecValue(key="Duty", value="blend")],
            rationale="Why this model fits.",
            creator_attribution={"display_name": "Your Name", "app_id": self.app_id},
        )
        return validate_output(output.model_dump()).model_dump()
```

### 3. Local test

```bash
cd py/apps/<your_slug>
echo '{"system_name":"Media Prep Vessel"}' | python agent.py
```

### 4. Register on bpiplatform

1. Admin grants `creatorAccess` → sign in at https://bpiplatform.bpeai.com
2. **New app** → set Python module `apps.<your_slug>.agent` and agent class name
3. Open a PR that adds `py/apps/<your_slug>/` — BPEAI merges and rebuilds `vendor_api` (chosen deploy path; no upload API)
4. **Test** → **Submit for review** → BPEAI publishes

Runtime resolves `python_module` + `agent_class` from the `creator_apps` database row.

### Required output fields

`equipment_tag`, `selected_model`, `equipment_system`, `key_specs[]`, `rationale`, `creator_attribution`.

Optional: `datasheet_markdown`, `mixing_options`, `manufacturers`, `source_basis`, `recommended_basis`.

## Desktop (BPE AI Workspace) — deferred

Desktop integration is **contract-only** until the workspace app ships. No desktop runtime in the current web repo.

| Topic | Document |
|-------|----------|
| Full desktop contract | [`docs/DESKTOP_EQUIPMENT_INTELLIGENCE.md`](../../../docs/DESKTOP_EQUIPMENT_INTELLIGENCE.md) |
| Publish sync plan | [`docs/desktop/PUBLISH_SYNC.md`](../../../docs/desktop/PUBLISH_SYNC.md) |
| Publish JSON schema | [`docs/desktop/publish-sync.schema.json`](../../../docs/desktop/publish-sync.schema.json) |
| TypeScript contract types | [`src/lib/desktopSyncContracts.ts`](../../../src/lib/desktopSyncContracts.ts) |

### Desktop rules (summary)

1. **Same output** — `equipment_selector_v1` JSON; validate with `validate_output()`.
2. **Same tray shape** — Project Tray items match `ProjectTrayItemRecord` (see web `projectTrayStore.ts`).
3. **Mirrored paths** — Local `engineering-artifacts/`, `project-tray/`, `datasheets/` map to S3 under `users/{uid}/projects/{pid}/`.
4. **Publish** — `POST /api/desktop/publish` with Bearer desktop token; Phase 7 validates payload and returns planned S3 keys (upload TBD).
5. **Enterprise local run** — Optional future mode: run `CreatorAppBase` on-device with local API keys; publish results when user chooses.
