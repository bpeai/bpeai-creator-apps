from __future__ import annotations

import pytest

from bpeai_creator_sdk.llm.allowlist import DEFAULT_MODELS, validate_model
from bpeai_creator_sdk.llm.parse import parse_json_safely
from bpeai_creator_sdk.llm.resolve import (
    default_creator_model,
    default_creator_provider,
    llm_credentials_present,
    resolve_provider,
)
from bpeai_creator_sdk.llm.types import JsonCompletion
from bpeai_creator_sdk.base import CreatorAppBase


def test_default_provider_is_openai(monkeypatch):
    monkeypatch.delenv("CREATOR_LLM_PROVIDER", raising=False)
    assert default_creator_provider() == "openai"


def test_default_model_falls_back_to_gpt4o(monkeypatch):
    monkeypatch.delenv("CREATOR_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("CREATOR_LLM_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_CREATOR_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert default_creator_model() == "gpt-4o"


def test_openai_creator_model_env(monkeypatch):
    monkeypatch.delenv("CREATOR_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("CREATOR_LLM_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_CREATOR_MODEL", "gpt-5.2")
    assert default_creator_model() == "gpt-5.2"


def test_creator_llm_model_wins_for_openai(monkeypatch):
    monkeypatch.setenv("CREATOR_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CREATOR_LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_CREATOR_MODEL", "gpt-5.2")
    assert default_creator_model() == "gpt-4o-mini"


def test_anthropic_default_model(monkeypatch):
    monkeypatch.setenv("CREATOR_LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("CREATOR_LLM_MODEL", raising=False)
    assert default_creator_model() == "claude-sonnet-4-5"


def test_allowlist_rejects_unknown_anthropic_model():
    with pytest.raises(RuntimeError, match="not allowlisted"):
        validate_model("anthropic", "claude-opus-4")


def test_allowlist_rejects_unknown_provider():
    with pytest.raises(RuntimeError, match="Unknown CREATOR_LLM_PROVIDER"):
        validate_model("cohere", "command-r")


def test_openai_passthrough_any_model():
    validate_model("openai", "gpt-anything-custom")


def test_resolve_provider_xai(monkeypatch):
    monkeypatch.setenv("CREATOR_LLM_PROVIDER", "xai")
    monkeypatch.delenv("CREATOR_LLM_MODEL", raising=False)
    prov, model, adapter = resolve_provider()
    assert prov == "xai"
    assert model == "grok-3"
    assert adapter.name == "xai"


def test_llm_credentials_present_per_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    assert llm_credentials_present("openai") is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert llm_credentials_present("anthropic") is True
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    assert llm_credentials_present("google") is True


def test_parse_json_safely_strips_fences():
    raw = '```json\n{"a": 1}\n```'
    assert parse_json_safely(raw) == {"a": 1}


def test_call_llm_json_uses_complete_json(monkeypatch):
    class _Agent(CreatorAppBase):
        app_id = "test_agent"

        def run(self, inputs):
            return inputs

    def _fake_complete_json(**kwargs):
        return JsonCompletion(
            text='{"ok": true}',
            tokens_in=3,
            tokens_out=2,
            provider="openai",
            model="gpt-4o",
        )

    monkeypatch.setattr("bpeai_creator_sdk.base.complete_json", _fake_complete_json)
    agent = _Agent()
    result = agent.call_openai_json(system="s", user="u")
    assert result == {"ok": True}
    assert agent.last_model() == "gpt-4o"
    assert agent.last_provider() == "openai"
    assert agent.usage_stats()["tokens_in"] == 3
    assert agent.usage_stats()["tokens_out"] == 2


def test_default_models_match_allowlist_defaults():
    assert DEFAULT_MODELS["anthropic"] == "claude-sonnet-4-5"
    assert DEFAULT_MODELS["google"] == "gemini-2.5-pro"
    assert DEFAULT_MODELS["xai"] == "grok-3"
