from __future__ import annotations

import html
import os
import re
from typing import Any
from urllib.parse import urlparse

import requests

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>")
_WS_RE = re.compile(r"\s+")


def serper_search(query: str, *, num: int = 8) -> list[dict[str, Any]]:
    api_key = (os.getenv("SERPER_API_KEY") or "").strip()
    if not api_key:
        return []

    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": min(max(num, 1), 10)}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    results: list[dict[str, Any]] = []
    for item in data.get("organic", []) or []:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
        )
    return results


def _html_to_text(raw: str) -> str:
    cleaned = _SCRIPT_RE.sub(" ", raw or "")
    cleaned = _TAG_RE.sub(" ", cleaned)
    cleaned = html.unescape(cleaned)
    return _WS_RE.sub(" ", cleaned).strip()


def fetch_page_excerpt(
    url: str,
    *,
    max_chars: int | None = None,
    timeout: float = 12.0,
) -> str:
    """Fetch a URL and return a length-capped readable text excerpt."""
    if max_chars is None:
        max_chars = int(os.getenv("BPEAI_SEARCH_EXCERPT_MAX_CHARS", "1200"))
    link = (url or "").strip()
    if not link.startswith(("http://", "https://")):
        return ""
    host = urlparse(link).netloc.lower()
    # Skip obvious binary / login-walled hosts lightly
    if any(x in host for x in ("linkedin.com", "facebook.com", "twitter.com", "x.com")):
        return ""
    headers = {
        "User-Agent": "BPEAI-CreatorApps/1.0 (+industrial research; excerpt only)",
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = requests.get(link, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code >= 400:
            return ""
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "html" not in ctype and "text" not in ctype and ctype:
            return ""
        text = _html_to_text(resp.text[: 250_000])
        if len(text) <= max_chars:
            return text
        return text[: max(0, max_chars - 1)].rstrip() + "…"
    except Exception:
        return ""


def enrich_search_hits_with_excerpts(
    hits: list[dict[str, Any]],
    *,
    max_pages: int | None = None,
    max_chars: int | None = None,
) -> list[dict[str, Any]]:
    """Attach ``excerpt`` to the top unique URLs among Serper hits."""
    enabled = (os.getenv("BPEAI_FETCH_SEARCH_EXCERPTS") or "1").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return hits

    if max_pages is None:
        max_pages = int(os.getenv("BPEAI_SEARCH_EXCERPT_MAX_PAGES", "6"))

    seen: set[str] = set()
    enriched: list[dict[str, Any]] = []
    fetched = 0
    for hit in hits:
        item = dict(hit)
        link = str(item.get("link") or "").strip()
        if link and link not in seen and fetched < max_pages:
            seen.add(link)
            excerpt = fetch_page_excerpt(link, max_chars=max_chars)
            if excerpt:
                item["excerpt"] = excerpt
                fetched += 1
        enriched.append(item)
    return enriched


def format_search_context(hits: list[dict[str, Any]], *, limit: int = 20) -> str:
    """Format Serper hits (optional excerpts) for LLM context."""
    lines: list[str] = []
    for h in hits[:limit]:
        title = h.get("title") or ""
        snippet = h.get("snippet") or ""
        link = h.get("link") or ""
        excerpt = h.get("excerpt") or ""
        block = f"- {title}: {snippet} ({link})"
        if excerpt:
            block += f"\n  Excerpt: {excerpt}"
        lines.append(block)
    return "\n".join(lines)
