from __future__ import annotations

# Allow `python agent.py` from this folder as well as package imports.
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    _py_root = Path(__file__).resolve().parents[2]
    _py_root_str = str(_py_root)
    if _py_root_str not in sys.path:
        sys.path.insert(0, _py_root_str)
    _sdk_src = _py_root / "libs" / "bpeai_creator_sdk" / "src"
    if str(_sdk_src) not in sys.path:
        sys.path.insert(0, str(_sdk_src))
    __package__ = "apps._template"

import json
from typing import Any, Dict

from bpeai_creator_sdk import CreatorAppBase, EquipmentSelectorOutput, KeySpecValue, validate_output


class MySelectorAgent(CreatorAppBase):
    """Minimal Equipment Intelligence selector — copy and rename this class.

    Portal "Agent class" must match this class name exactly (e.g. MySelectorAgent).
    """

    # Must match manifest.json "id" and the portal App id (snake_case, unique).
    # Example: slug "heat-exchanger-selector" → id "heat_exchanger_selector".
    app_id = "my_selector_app"

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Common inputs — declare required ones in manifest.json "required_inputs".
        system_name = str(inputs.get("system_name") or "Process Vessel").strip()
        application = str(inputs.get("application") or "biopharmaceutical").strip()

        self.status(f"Evaluating {system_name}…")

        # Replace this stub with your SME logic:
        #   self.call_openai_json(...)  — structured LLM
        #   self.serper_search(...)     — web search (usage tracked)
        # Always return equipment_selector_v1 via validate_output(...).
        output = EquipmentSelectorOutput(
            equipment_tag="EQ-101",  # tag shown in Project Tray
            selected_model="Example Model A",  # primary recommendation
            equipment_system="mixing",  # must align with manifest equipment_system
            equipment_name=f"Selector result for {system_name}",
            equipment_category="Mixing",
            key_specs=[
                KeySpecValue(key="Application", value=application),
                KeySpecValue(key="System", value=system_name),
            ],
            rationale=(
                f"Placeholder recommendation for {system_name} ({application}). "
                "Replace MySelectorAgent.run() with your domain logic."
            ),
            creator_attribution={
                "display_name": "Your Name",  # usually matches portal Profile display name
                "app_id": self.app_id,
            },
            source_basis=["_template stub"],
        )
        return validate_output(output.model_dump()).model_dump()


def run_from_stdio() -> None:
    raw = sys.stdin.read()
    inputs = json.loads(raw) if raw.strip() else {}
    agent = MySelectorAgent(status_callback=lambda m: print(m, file=sys.stderr))
    result = agent.run(inputs)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_from_stdio()
