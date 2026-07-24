from __future__ import annotations

import sys
from types import SimpleNamespace

from bpeai_creator_sdk.llm.anthropic_provider import AnthropicProvider
from bpeai_creator_sdk.llm.google_provider import GoogleProvider
from bpeai_creator_sdk.llm.openai_provider import OpenAIProvider
from bpeai_creator_sdk.llm.xai_provider import XAIProvider


def test_openai_provider_complete_json(monkeypatch):
    class _Resp:
        output_text = '{"x": 1}'
        usage = SimpleNamespace(input_tokens=10, output_tokens=5)

    class _Client:
        class responses:
            @staticmethod
            def create(**kwargs):
                assert kwargs["text"]["format"]["type"] == "json_object"
                return _Resp()

    import openai as openai_mod

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(openai_mod, "OpenAI", lambda **kwargs: _Client())

    out = OpenAIProvider().complete_json(
        system="s", user="u", model="gpt-4o", max_output_tokens=100
    )
    assert out.text == '{"x": 1}'
    assert out.tokens_in == 10
    assert out.tokens_out == 5
    assert out.provider == "openai"


def test_anthropic_provider_complete_json(monkeypatch):
    class _Msg:
        content = [SimpleNamespace(text='{"a": true}')]
        usage = SimpleNamespace(input_tokens=4, output_tokens=6)

    class _Messages:
        @staticmethod
        def create(**kwargs):
            assert "JSON" in kwargs["system"]
            return _Msg()

    class _Anthropic:
        def __init__(self, **kwargs):
            self.messages = _Messages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=_Anthropic))

    out = AnthropicProvider().complete_json(
        system="s", user="u", model="claude-sonnet-4-5", max_output_tokens=200
    )
    assert '"a"' in out.text
    assert out.provider == "anthropic"
    assert out.tokens_in == 4


def test_google_provider_complete_json(monkeypatch):
    class _Resp:
        text = '{"g": 2}'
        usage_metadata = SimpleNamespace(prompt_token_count=1, candidates_token_count=2)

    class _Models:
        @staticmethod
        def generate_content(**kwargs):
            return _Resp()

    class _Client:
        def __init__(self, **kwargs):
            self.models = _Models()

    class _Types:
        class GenerateContentConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

    genai_mod = SimpleNamespace(Client=_Client, types=_Types)
    google_pkg = SimpleNamespace(genai=genai_mod)

    monkeypatch.setenv("GOOGLE_API_KEY", "g-test")
    monkeypatch.setitem(sys.modules, "google", google_pkg)
    monkeypatch.setitem(sys.modules, "google.genai", genai_mod)
    monkeypatch.setitem(sys.modules, "google.genai.types", _Types)

    out = GoogleProvider().complete_json(
        system="s", user="u", model="gemini-2.5-pro", max_output_tokens=200
    )
    assert out.text == '{"g": 2}'
    assert out.provider == "google"


def test_xai_provider_complete_json(monkeypatch):
    class _Choice:
        message = SimpleNamespace(content='{"z": 9}')

    class _Resp:
        choices = [_Choice()]
        usage = SimpleNamespace(prompt_tokens=7, completion_tokens=3)

    class _Completions:
        @staticmethod
        def create(**kwargs):
            assert kwargs["response_format"]["type"] == "json_object"
            return _Resp()

    class _Client:
        def __init__(self, **kwargs):
            assert kwargs.get("base_url") == "https://api.x.ai/v1"
            self.chat = SimpleNamespace(completions=_Completions())

    import openai as openai_mod

    monkeypatch.setenv("XAI_API_KEY", "xai-test")
    monkeypatch.setattr(openai_mod, "OpenAI", lambda **kwargs: _Client(**kwargs))

    out = XAIProvider().complete_json(
        system="s", user="u", model="grok-3", max_output_tokens=100
    )
    assert out.text == '{"z": 9}'
    assert out.tokens_in == 7
    assert out.provider == "xai"
