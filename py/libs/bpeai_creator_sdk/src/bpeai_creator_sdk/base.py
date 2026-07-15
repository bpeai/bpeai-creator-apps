from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from openai import OpenAI

from .output import EquipmentSelectorOutput, validate_output

StatusCallback = Callable[[str], None]


class CreatorAppBase(ABC):
    """Base class for BPEAI creator apps."""

    app_id: str = "creator_app"

    def __init__(self, status_callback: Optional[StatusCallback] = None) -> None:
        self._status = status_callback or (lambda _msg: None)
        self._usage: Dict[str, int] = {"tokens_in": 0, "tokens_out": 0, "serper_calls": 0}

    def status(self, message: str) -> None:
        self._status(message)

    def usage_stats(self) -> Dict[str, int]:
        return dict(self._usage)

    @abstractmethod
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the app and return a JSON-serializable result."""

    def validate_result(self, data: Dict[str, Any]) -> EquipmentSelectorOutput:
        return validate_output(data)

    def _openai_client(self) -> OpenAI:
        api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing")
        return OpenAI(api_key=api_key)

    def _default_model(self) -> str:
        return (
            os.getenv("OPENAI_CREATOR_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "gpt-4o"
        ).strip()

    def call_openai_json(self, *, system: str, user: str, model: str | None = None) -> Dict[str, Any]:
        client = self._openai_client()
        chosen = (model or self._default_model()).strip()
        response = client.responses.create(
            model=chosen,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            text={"format": {"type": "json_object"}},
            max_output_tokens=int(os.getenv("OPENAI_CREATOR_MAX_OUTPUT_TOKENS", "8000")),
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            prompt = getattr(usage, "input_tokens", None)
            if prompt is None:
                prompt = getattr(usage, "prompt_tokens", 0)
            completion = getattr(usage, "output_tokens", None)
            if completion is None:
                completion = getattr(usage, "completion_tokens", 0)
            self._usage["tokens_in"] += int(prompt or 0)
            self._usage["tokens_out"] += int(completion or 0)

        raw = getattr(response, "output_text", "") or ""
        if not raw:
            raise RuntimeError("LLM returned empty output")
        return _parse_json_safely(raw)

    def serper_search(self, query: str, *, num: int = 8) -> list[dict[str, Any]]:
        from .tools import serper_search

        self._usage["serper_calls"] += 1
        return serper_search(query, num=num)


def _parse_json_safely(raw: str) -> Dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object from LLM")
    return parsed
