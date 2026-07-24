from __future__ import annotations

import os

from .types import JsonCompletion

XAI_BASE_URL = "https://api.x.ai/v1"


class XAIProvider:
    """xAI Grok via OpenAI-compatible Chat Completions + json_object."""

    name = "xai"

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_output_tokens: int,
    ) -> JsonCompletion:
        from openai import OpenAI

        api_key = (os.getenv("XAI_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("XAI_API_KEY is missing")

        client = OpenAI(api_key=api_key, base_url=XAI_BASE_URL)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            max_tokens=max_output_tokens,
        )
        choice = (response.choices or [None])[0]
        if choice is None or choice.message is None:
            raise RuntimeError("LLM returned empty output")
        raw = (choice.message.content or "").strip()
        if not raw:
            raise RuntimeError("LLM returned empty output")

        usage = getattr(response, "usage", None)
        tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        tokens_out = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
        return JsonCompletion(
            text=raw,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            provider=self.name,
            model=model,
        )
