from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from bpeai_creator_sdk.credential_errors import (
    ProviderCredentialError,
    is_credential_failure,
    raise_if_http_failed,
    raise_missing_key,
    wrap_exception,
)
from bpeai_creator_sdk.tools import serper_search


def test_detects_http_401():
    assert is_credential_failure(status_code=401, body="nope")


def test_detects_quota_429():
    assert is_credential_failure(status_code=429, body="insufficient_quota")
    assert not is_credential_failure(status_code=429, body="slow down")


def test_detects_invalid_key_400():
    assert is_credential_failure(status_code=400, body='{"message":"Invalid API Key"}')


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("BPEAI_INTERNAL_BASE_URL", raising=False)
    monkeypatch.delenv("NEXT_INTERNAL_BASE_URL", raising=False)
    with pytest.raises(ProviderCredentialError) as exc:
        raise_missing_key("serper", "SERPER_API_KEY", source="test")
    assert "SERPER_API_KEY" in str(exc.value)


def test_http_401_raises(monkeypatch):
    monkeypatch.delenv("BPEAI_INTERNAL_BASE_URL", raising=False)
    monkeypatch.delenv("NEXT_INTERNAL_BASE_URL", raising=False)
    resp = SimpleNamespace(status_code=401, text="Unauthorized")
    with pytest.raises(ProviderCredentialError):
        raise_if_http_failed("serper", resp, source="test")


def test_http_500_does_not_raise_credential_error():
    resp = SimpleNamespace(status_code=500, text="upstream")
    raise_if_http_failed("serper", resp, source="test")


def test_wrap_openai_auth_error(monkeypatch):
    monkeypatch.delenv("BPEAI_INTERNAL_BASE_URL", raising=False)
    monkeypatch.delenv("NEXT_INTERNAL_BASE_URL", raising=False)

    class AuthenticationError(Exception):
        status_code = 401

    wrapped = wrap_exception("openai", AuthenticationError("invalid_api_key"), source="test")
    assert isinstance(wrapped, ProviderCredentialError)


def test_serper_search_missing_key(monkeypatch):
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    monkeypatch.delenv("SERPER_DEV_API_KEY", raising=False)
    monkeypatch.delenv("BPEAI_INTERNAL_BASE_URL", raising=False)
    monkeypatch.delenv("NEXT_INTERNAL_BASE_URL", raising=False)
    with pytest.raises(ProviderCredentialError):
        serper_search("mixing agitator")


def test_serper_search_401(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "bad-key")
    monkeypatch.delenv("BPEAI_INTERNAL_BASE_URL", raising=False)
    monkeypatch.delenv("NEXT_INTERNAL_BASE_URL", raising=False)

    class Resp:
        status_code = 403
        text = "Invalid API Key"

        def raise_for_status(self):
            raise RuntimeError("should not reach network error path")

        def json(self):
            return {}

    def fake_post(*_args, **_kwargs):
        return Resp()

    monkeypatch.setattr("bpeai_creator_sdk.tools.requests.post", fake_post)
    with pytest.raises(ProviderCredentialError):
        serper_search("query")


def test_serper_search_ok(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "ok-key")

    class Resp:
        status_code = 200
        text = json.dumps({"organic": [{"title": "A", "link": "https://x", "snippet": "s"}]})

        def raise_for_status(self):
            return None

        def json(self):
            return {"organic": [{"title": "A", "link": "https://x", "snippet": "s"}]}

    monkeypatch.setattr("bpeai_creator_sdk.tools.requests.post", lambda *a, **k: Resp())
    hits = serper_search("query")
    assert hits[0]["title"] == "A"
