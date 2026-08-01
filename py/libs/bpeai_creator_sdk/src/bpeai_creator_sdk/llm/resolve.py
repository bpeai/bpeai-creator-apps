from __future__ import annotations

import os
import threading
from typing import Callable, Optional, Tuple

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

_tls = threading.local()


def push_run_overrides(
    *,
    provider: str | None = None,
    model: str | None = None,
    max_output_tokens: int | None = None,
) -> Callable[[], None]:
    """Apply per-run LLM overrides (thread-local). Returns a restore callback."""
    stack: list[dict] = getattr(_tls, "override_stack", None) or []
    prev = {
        "provider": getattr(_tls, "provider", None),
        "model": getattr(_tls, "model", None),
        "max_output_tokens": getattr(_tls, "max_output_tokens", None),
    }
    stack.append(prev)
    _tls.override_stack = stack
    if provider:
        _tls.provider = provider.strip().lower()
    if model:
        _tls.model = model.strip()
    if max_output_tokens is not None:
        _tls.max_output_tokens = int(max_output_tokens)

    def _restore() -> None:
        cur_stack: list[dict] = getattr(_tls, "override_stack", None) or []
        if not cur_stack:
            _tls.provider = None
            _tls.model = None
            _tls.max_output_tokens = None
            return
        old = cur_stack.pop()
        _tls.override_stack = cur_stack
        _tls.provider = old.get("provider")
        _tls.model = old.get("model")
        _tls.max_output_tokens = old.get("max_output_tokens")

    return _restore


def default_creator_provider() -> str:
    """Resolve CREATOR_LLM_PROVIDER (default openai)."""
    override = getattr(_tls, "provider", None)
    if override:
        raw = str(override).strip().lower()
    else:
        raw = (os.getenv("CREATOR_LLM_PROVIDER") or "openai").strip().lower()
    if not raw:
        return "openai"
    if raw not in SUPPORTED_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise RuntimeError(f"Unknown CREATOR_LLM_PROVIDER '{raw}'. Supported: {supported}")
    return raw


def default_max_output_tokens() -> int:
    """Resolve max output tokens with legacy OpenAI fallback."""
    override = getattr(_tls, "max_output_tokens", None)
    if override is not None:
        return int(override)
    raw = (
        os.getenv("CREATOR_LLM_MAX_OUTPUT_TOKENS")
        or os.getenv("OPENAI_CREATOR_MAX_OUTPUT_TOKENS")
        or "16000"
    )
    return int(raw)


def default_creator_model(provider: str | None = None) -> str:
    """Resolve model for the active (or given) provider."""
    prov = (provider or default_creator_provider()).strip().lower()
    override = getattr(_tls, "model", None)
    explicit = (str(override).strip() if override else "") or (
        os.getenv("CREATOR_LLM_MODEL") or ""
    ).strip()
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
