from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from .llm import (
    complete_json,
    default_creator_model,
    default_creator_provider,
    default_max_output_tokens,
    parse_json_safely,
)
from .output import EquipmentSelectorOutput, validate_output

StatusCallback = Callable[[str], None]

# Re-export for callers that imported from base.
__all__ = [
    "CreatorAppBase",
    "default_creator_model",
    "default_creator_provider",
]


class CreatorAppBase(ABC):
    """Base class for BPEAI creator apps."""

    app_id: str = "creator_app"

    def __init__(self, status_callback: Optional[StatusCallback] = None) -> None:
        self._status = status_callback or (lambda _msg: None)
        self._usage: Dict[str, int] = {"tokens_in": 0, "tokens_out": 0, "serper_calls": 0}
        self._last_model: str = default_creator_model()
        self._last_provider: str = default_creator_provider()

    def status(self, message: str) -> None:
        self._status(message)

    def usage_stats(self) -> Dict[str, int]:
        return dict(self._usage)

    def last_model(self) -> str:
        return self._last_model

    def last_provider(self) -> str:
        return self._last_provider

    @abstractmethod
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the app and return a JSON-serializable result."""

    def validate_result(self, data: Dict[str, Any]) -> EquipmentSelectorOutput:
        return validate_output(data)

    def _default_model(self) -> str:
        return default_creator_model()

    def call_llm_json(self, *, system: str, user: str, model: str | None = None) -> Dict[str, Any]:
        """Structured JSON LLM call via the resolved CREATOR_LLM_PROVIDER."""
        completion = complete_json(
            system=system,
            user=user,
            model=model,
            max_output_tokens=default_max_output_tokens(),
        )
        self._last_provider = completion.provider
        self._last_model = completion.model
        self._usage["tokens_in"] += int(completion.tokens_in or 0)
        self._usage["tokens_out"] += int(completion.tokens_out or 0)
        return parse_json_safely(completion.text)

    def call_openai_json(self, *, system: str, user: str, model: str | None = None) -> Dict[str, Any]:
        """Backward-compatible alias for call_llm_json."""
        return self.call_llm_json(system=system, user=user, model=model)

    def serper_search(self, query: str, *, num: int = 8) -> list[dict[str, Any]]:
        from .tools import serper_search

        hits = serper_search(query, num=num)
        self._usage["serper_calls"] += 1
        return hits
