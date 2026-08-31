"""Detect provider API-key / billing failures, fail the run, and notify admins."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

CREDENTIAL_HTTP_STATUSES = {401, 402, 403}
_MESSAGE_MARKERS = (
    "invalid_api_key",
    "invalid api key",
    "incorrect api key",
    "incorrect api key provided",
    "authentication",
    "unauthorized",
    "forbidden",
    "insufficient_quota",
    "insufficient quota",
    "billing_not_active",
    "billing",
    "payment required",
    "account deactivated",
    "account disabled",
    "not enough credits",
    "insufficient credits",
    "api_key is missing",
    "api key is missing",
    "is not set",
)

_LLM_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
    "serper": "SERPER_API_KEY",
}

_lock = threading.Lock()
_last_posted: dict[str, float] = {}
_POST_DEBOUNCE_SEC = 60.0


class ProviderCredentialError(RuntimeError):
    """Hard failure: the provider rejected our key or the account cannot be billed."""

    def __init__(self, provider: str, message: str, *, status_code: int | None = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(message)


def llm_key_env_name(provider: str) -> str:
    return _LLM_KEY_ENV.get((provider or "").strip().lower(), "API_KEY")


def is_credential_failure(
    *,
    status_code: int | None = None,
    body: str = "",
    exc: BaseException | None = None,
) -> bool:
    status = status_code
    text = (body or "").lower()
    if exc is not None:
        text = f"{text} {type(exc).__name__} {exc}".lower()
        status = status or _status_from_exc(exc)
    if status in CREDENTIAL_HTTP_STATUSES:
        return True
    if status == 429 and any(m in text for m in ("quota", "billing", "credit", "insufficient")):
        return True
    if status == 400 and any(m in text for m in ("invalid api key", "invalid_api_key", "incorrect api key")):
        return True
    return any(m in text for m in _MESSAGE_MARKERS)


def user_message(provider: str, *, status_code: int | None = None, detail: str = "") -> str:
    label = (provider or "provider").strip()
    reason = "API key rejected, unpaid, disabled, or missing"
    if status_code:
        reason = f"{reason} (HTTP {status_code})"
    extra = " ".join((detail or "").strip().split())[:200]
    if extra:
        return (
            f"{label} request failed: {reason}. {extra} "
            "An administrator has been notified."
        )
    return (
        f"{label} request failed: {reason}. "
        "Web search and LLM calls cannot continue until the key is restored. "
        "An administrator has been notified."
    )


def raise_missing_key(provider: str, env_name: str, *, source: str = "") -> None:
    msg = user_message(provider, detail=f"{env_name} is not set")
    report_provider_failure(
        provider=provider,
        source=source or f"missing:{env_name}",
        status_code=None,
        message=msg,
    )
    raise ProviderCredentialError(provider, msg)


def raise_if_http_failed(provider: str, response: Any, *, source: str = "") -> None:
    status = getattr(response, "status_code", None)
    body = ""
    try:
        body = str(getattr(response, "text", "") or "")
    except Exception:
        body = ""
    raise_if_status_failed(provider, status, body, source=source or "http")


def raise_if_status_failed(
    provider: str,
    status_code: int | None,
    body: str = "",
    *,
    source: str = "",
) -> None:
    if not is_credential_failure(status_code=status_code, body=body):
        return
    msg = user_message(provider, status_code=status_code, detail=body)
    report_provider_failure(
        provider=provider,
        source=source or "http",
        status_code=status_code,
        message=msg,
    )
    raise ProviderCredentialError(provider, msg, status_code=status_code)


def wrap_exception(provider: str, exc: BaseException, *, source: str = "") -> BaseException:
    if isinstance(exc, ProviderCredentialError):
        return exc
    if not is_credential_failure(exc=exc, body=str(exc)):
        return exc
    status = _status_from_exc(exc)
    msg = user_message(provider, status_code=status, detail=str(exc))
    report_provider_failure(
        provider=provider,
        source=source or type(exc).__name__,
        status_code=status,
        message=msg,
    )
    return ProviderCredentialError(provider, msg, status_code=status)


def report_provider_failure(
    *,
    provider: str,
    source: str,
    message: str,
    status_code: int | None = None,
) -> None:
    key = f"{(provider or '').lower()}:{status_code}"
    now = time.time()
    with _lock:
        last = _last_posted.get(key, 0.0)
        if now - last < _POST_DEBOUNCE_SEC:
            return
        _last_posted[key] = now

    logger.error(
        "provider credential failure provider=%s source=%s status=%s message=%s",
        provider,
        source,
        status_code,
        message,
    )
    base = (
        os.environ.get("BPEAI_INTERNAL_BASE_URL")
        or os.environ.get("NEXT_INTERNAL_BASE_URL")
        or ""
    ).rstrip("/")
    if not base:
        return
    token = (
        os.environ.get("INTERNAL_API_TOKEN")
        or os.environ.get("CREATOR_INTERNAL_TOKEN")
        or os.environ.get("VENDOR_API_INTERNAL_TOKEN")
        or ""
    )
    payload = {
        "provider": provider,
        "source": source,
        "status_code": status_code,
        "message": message,
    }
    try:
        import urllib.request

        req = urllib.request.Request(
            f"{base}/api/internal/ops-alerts",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **({"x-internal-token": token} if token else {}),
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
    except Exception as exc:
        logger.warning("ops alert post failed: %s", exc)


def _status_from_exc(exc: BaseException) -> int | None:
    for attr in ("status_code", "status", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    resp = getattr(exc, "response", None)
    if resp is not None:
        value = getattr(resp, "status_code", None)
        if isinstance(value, int):
            return value
    return None
