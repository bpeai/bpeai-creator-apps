# bpeai-creator-sdk

SDK for BPEAI Equipment Intelligence creator apps.

## SME knowledge packs

Load system-specific DIR questionnaires and option catalogs:

```python
from bpeai_creator_sdk import load_knowledge_pack, resolve_scenario_id, validate_dir_code

pack = load_knowledge_pack("my_app_id")
scenario = resolve_scenario_id(pack, "Media Prep Vessel")
check = validate_dir_code(pack, scenario, "2-1-2-3-1-1")
```

Packs live in `py/knowledge/<pack_id>/` (see `docs/EI_APP_TEMPLATE_DESIGN.md`).

## Authoring guide (SME)

### 1. Copy the template

```text
py/apps/_templates/equipment_evaluator/   ← start here (DIR → evaluate + knowledge pack)
py/knowledge/<your_app_id>/               ← private pack (same name as the app)
```

```powershell
Copy-Item -Recurse py\apps\_templates\equipment_evaluator py\apps\<your_slug>
```

Rename the agent class and `app_id`, and edit `manifest.json`. Set `knowledge_pack`
to the **same** `app_id`. `equipment_system` is taxonomy only (mixing, filtration, …).

### 2. Implement `run(inputs)`

Prefer the shipped evaluator template (pack-backed). Minimal contract:

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

**Preferred — local chat** (smart text; optional personal `OPENAI_API_KEY` via `.env`):

```powershell
python py/tools/local_chat.py --app <your_slug>
# > Media prep vessel, biopharma
# > 2-1-2-3-1-1
# > pptx
```

Helpers: `local_env`, `local_parse`, `local_format`, `local_run`, `llm` (multi-provider JSON).  
Artifacts helpers: `build_evaluation_pdf`, `build_evaluation_pptx`, `list_reference_decks`,
`replace_reference_deck`.

LLM provider adapter (v1): default `CREATOR_LLM_PROVIDER=openai`. Optional allowlisted
providers `anthropic` / `google` / `xai`. See `docs/PROVIDER_DIR_QA.md` in the creator-apps
repo. Agents keep using `self.call_openai_json(...)` (alias of `call_llm_json`).

Portal `/sdk` §3 wording: `docs/PORTAL_SDK_LOCAL_TEST.md` (keep in sync with website
`src/lib/creatorSdkDocs.ts`).

### 4. Register on bpiplatform

1. Admin grants `creatorAccess` → sign in at https://bpiplatform.bpeai.com
2. **New app** → set Python module `apps.<your_slug>.agent` and agent class name
3. Open a PR that adds `py/apps/<your_slug>/` — BPEAI merges and rebuilds `vendor_api`
   (**no upload API**)
4. **Test** → **Submit for review** → BPEAI publishes

Runtime resolves `python_module` + `agent_class` from the `creator_apps` database row.

### Required output fields

`equipment_tag`, `selected_model`, `equipment_system`, `key_specs[]`, `rationale`,
`creator_attribution`.

Optional GPT-parity / evaluator fields: `datasheet_markdown`, `design_basis`,
`dir_summary`, `objectives`, `failure_modes`, `mixing_options`, `evaluation_matrix`,
`alternate_basis`, `do_not_specify`, `preliminary_specs`, `manufacturers`,
`source_basis`, `recommended_basis`.

## Desktop (BPE AI Workspace) — deferred

Desktop integration is **contract-only** until the workspace app ships. Desktop
docs live in the main **bpeai** website repo (not this authoring repo). Same
output contract: `equipment_selector_v1` validated with `validate_output()`.
