from __future__ import annotations

from typing import Any, Dict

from ..credential_errors import (
    ProviderCredentialError,
    llm_key_env_name,
    raise_missing_key,
    wrap_exception,
)
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
    if not llm_credentials_present(_prov):
        raise_missing_key(_prov, llm_key_env_name(_prov), source="creator_sdk.complete_json")
    tokens = max_output_tokens if max_output_tokens is not None else default_max_output_tokens()
    try:
        return adapter.complete_json(
            system=system,
            user=user,
            model=chosen,
            max_output_tokens=tokens,
        )
    except ProviderCredentialError:
        raise
    except Exception as exc:
        wrapped = wrap_exception(_prov, exc, source="creator_sdk.complete_json")
        raise wrapped from exc


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
