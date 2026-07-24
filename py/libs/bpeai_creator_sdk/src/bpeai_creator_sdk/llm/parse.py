from __future__ import annotations

import json
import re
from typing import Any, Dict


def parse_json_safely(raw: str) -> Dict[str, Any]:
    """Strip optional markdown fences and parse a top-level JSON object."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object from LLM")
    return parsed
