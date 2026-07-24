from __future__ import annotations

import os
from typing import Tuple

from .allowlist import DEFAULT_MODELS, SUPPORTED_PROVIDERS, validate_model
from .anthropic_provider import AnthropicProvider
from .google_provider import GoogleProvider
from .openai_provider import OpenAIProvider
from .types import LlmProvider
from .xai_provider import XAIProvider

_ADAPTERS: dict[str, LlmProvider] = {
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "google": GoogleProvider(),
    "xai": XAIProvider(),
}


def default_creator_provider() -> str:
    """Resolve CREATOR_LLM_PROVIDER (default openai)."""
    raw = (os.getenv("CREATOR_LLM_PROVIDER") or "openai").strip().lower()
    if not raw:
        return "openai"
    if raw not in SUPPORTED_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise RuntimeError(f"Unknown CREATOR_LLM_PROVIDER '{raw}'. Supported: {supported}")
    return raw


def default_max_output_tokens() -> int:
    """Resolve max output tokens with legacy OpenAI fallback."""
    raw = (
        os.getenv("CREATOR_LLM_MAX_OUTPUT_TOKENS")
        or os.getenv("OPENAI_CREATOR_MAX_OUTPUT_TOKENS")
        or "16000"
    )
    return int(raw)


def default_creator_model(provider: str | None = None) -> str:
    """Resolve model for the active (or given) provider."""
    prov = (provider or default_creator_provider()).strip().lower()
    explicit = (os.getenv("CREATOR_LLM_MODEL") or "").strip()
    if prov == "openai":
        chosen = (
            explicit
            or (os.getenv("OPENAI_CREATOR_MODEL") or "").strip()
            or (os.getenv("OPENAI_MODEL") or "").strip()
            or DEFAULT_MODELS["openai"]
        )
    else:
        chosen = explicit or DEFAULT_MODELS[prov]
    validate_model(prov, chosen)
    return chosen


def resolve_provider(
    *,
    provider: str | None = None,
    model: str | None = None,
) -> Tuple[str, str, LlmProvider]:
    """Return (provider_name, model_id, adapter) after allowlist checks."""
    prov = (provider or default_creator_provider()).strip().lower()
    if prov not in _ADAPTERS:
        supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise RuntimeError(f"Unknown CREATOR_LLM_PROVIDER '{prov}'. Supported: {supported}")
    chosen = (model or default_creator_model(prov)).strip()
    validate_model(prov, chosen)
    return prov, chosen, _ADAPTERS[prov]


def llm_credentials_present(provider: str | None = None) -> bool:
    """True when the API key for the provider is set in the environment."""
    prov = (provider or default_creator_provider()).strip().lower()
    if prov == "openai":
        return bool((os.getenv("OPENAI_API_KEY") or "").strip())
    if prov == "anthropic":
        return bool((os.getenv("ANTHROPIC_API_KEY") or "").strip())
    if prov == "google":
        return bool(
            (os.getenv("GOOGLE_API_KEY") or "").strip()
            or (os.getenv("GEMINI_API_KEY") or "").strip()
        )
    if prov == "xai":
        return bool((os.getenv("XAI_API_KEY") or "").strip())
    return False
