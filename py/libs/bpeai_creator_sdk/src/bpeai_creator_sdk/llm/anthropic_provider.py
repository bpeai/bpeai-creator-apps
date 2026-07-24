from __future__ import annotations

import os

from .types import JsonCompletion

_JSON_SUFFIX = (
    "\n\nRespond with a single JSON object only. "
    "Do not wrap the object in markdown fences or add commentary."
)


class AnthropicProvider:
    """Anthropic Messages API → JSON text (prompt-enforced)."""

    name = "anthropic"

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_output_tokens: int,
    ) -> JsonCompletion:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "Anthropic SDK is not installed. "
                "Install with: pip install 'bpeai-creator-sdk[anthropic]'"
            ) from exc

        api_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is missing")

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=max_output_tokens,
            system=system + _JSON_SUFFIX,
            messages=[{"role": "user", "content": user}],
        )
        parts: list[str] = []
        for block in message.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(str(text))
        raw = "".join(parts).strip()
        if not raw:
            raise RuntimeError("LLM returned empty output")

        usage = getattr(message, "usage", None)
        tokens_in = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
        tokens_out = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
        return JsonCompletion(
            text=raw,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            provider=self.name,
            model=model,
        )
