from __future__ import annotations

from typing import Any, Dict

from .parse import parse_json_safely
from .resolve import (
    default_creator_model,
    default_creator_provider,
    default_max_output_tokens,
    llm_credentials_present,
    resolve_provider,
)
from .types import JsonCompletion

__all__ = [
    "JsonCompletion",
    "complete_json",
    "default_creator_model",
    "default_creator_provider",
    "default_max_output_tokens",
    "llm_credentials_present",
    "parse_json_safely",
    "resolve_provider",
]


def complete_json(
    *,
    system: str,
    user: str,
    model: str | None = None,
    provider: str | None = None,
    max_output_tokens: int | None = None,
) -> JsonCompletion:
    """Run a JSON-object completion via the resolved creator LLM provider."""
    _prov, chosen, adapter = resolve_provider(provider=provider, model=model)
    tokens = max_output_tokens if max_output_tokens is not None else default_max_output_tokens()
    return adapter.complete_json(
        system=system,
        user=user,
        model=chosen,
        max_output_tokens=tokens,
    )


def complete_json_object(
    *,
    system: str,
    user: str,
    model: str | None = None,
    provider: str | None = None,
    max_output_tokens: int | None = None,
) -> Dict[str, Any]:
    """complete_json + parse_json_safely → dict."""
    completion = complete_json(
        system=system,
        user=user,
        model=model,
        provider=provider,
        max_output_tokens=max_output_tokens,
    )
    return parse_json_safely(completion.text)
