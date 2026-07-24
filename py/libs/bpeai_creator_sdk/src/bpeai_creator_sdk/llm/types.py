from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class JsonCompletion:
    """Normalized JSON-text completion from any creator LLM provider."""

    text: str
    tokens_in: int
    tokens_out: int
    provider: str
    model: str


class LlmProvider(Protocol):
    """Provider adapter that returns a JSON object as text."""

    name: str

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_output_tokens: int,
    ) -> JsonCompletion: ...
