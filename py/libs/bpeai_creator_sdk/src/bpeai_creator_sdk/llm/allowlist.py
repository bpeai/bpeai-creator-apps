from __future__ import annotations

from typing import FrozenSet, Mapping, Optional

# None = pass-through (any model id allowed). Used for OpenAI only in v1.
ALLOWLIST: Mapping[str, Optional[FrozenSet[str]]] = {
    "openai": None,
    "anthropic": frozenset({"claude-sonnet-4-5"}),
    "google": frozenset({"gemini-2.5-pro"}),
    "xai": frozenset({"grok-3"}),
}

DEFAULT_MODELS: Mapping[str, str] = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-5",
    "google": "gemini-2.5-pro",
    "xai": "grok-3",
}

SUPPORTED_PROVIDERS: FrozenSet[str] = frozenset(ALLOWLIST.keys())


def validate_model(provider: str, model: str) -> None:
    """Raise RuntimeError if provider/model is not allowed for v1."""
    key = provider.strip().lower()
    if key not in ALLOWLIST:
        supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise RuntimeError(f"Unknown CREATOR_LLM_PROVIDER '{provider}'. Supported: {supported}")
    allowed = ALLOWLIST[key]
    if allowed is None:
        return
    chosen = model.strip()
    if chosen not in allowed:
        raise RuntimeError(
            f"Model '{chosen}' is not allowlisted for provider '{key}'. "
            f"Allowed: {', '.join(sorted(allowed))}"
        )
