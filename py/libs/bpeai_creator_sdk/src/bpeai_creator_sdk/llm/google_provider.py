from __future__ import annotations

import os

from .types import JsonCompletion


class GoogleProvider:
    """Google Gemini via google-genai with application/json MIME type."""

    name = "google"

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_output_tokens: int,
    ) -> JsonCompletion:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError(
                "Google GenAI SDK is not installed. "
                "Install with: pip install 'bpeai-creator-sdk[google]'"
            ) from exc

        api_key = (
            (os.getenv("GOOGLE_API_KEY") or "").strip()
            or (os.getenv("GEMINI_API_KEY") or "").strip()
        )
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY (or GEMINI_API_KEY) is missing")

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                max_output_tokens=max_output_tokens,
            ),
        )
        raw = (getattr(response, "text", None) or "").strip()
        if not raw:
            raise RuntimeError("LLM returned empty output")

        tokens_in = 0
        tokens_out = 0
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            tokens_in = int(getattr(usage, "prompt_token_count", 0) or 0)
            tokens_out = int(getattr(usage, "candidates_token_count", 0) or 0)

        return JsonCompletion(
            text=raw,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            provider=self.name,
            model=model,
        )
