from __future__ import annotations

import os

from .types import JsonCompletion


class OpenAIProvider:
    """OpenAI Responses API with json_object format (existing creator path)."""

    name = "openai"

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_output_tokens: int,
    ) -> JsonCompletion:
        from openai import OpenAI

        api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing")
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            text={"format": {"type": "json_object"}},
            max_output_tokens=max_output_tokens,
        )
        usage = getattr(response, "usage", None)
        tokens_in = 0
        tokens_out = 0
        if usage is not None:
            prompt = getattr(usage, "input_tokens", None)
            if prompt is None:
                prompt = getattr(usage, "prompt_tokens", 0)
            completion = getattr(usage, "output_tokens", None)
            if completion is None:
                completion = getattr(usage, "completion_tokens", 0)
            tokens_in = int(prompt or 0)
            tokens_out = int(completion or 0)

        raw = getattr(response, "output_text", "") or ""
        if not raw:
            raise RuntimeError("LLM returned empty output")
        return JsonCompletion(
            text=raw,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            provider=self.name,
            model=model,
        )
