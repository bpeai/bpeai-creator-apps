from __future__ import annotations

import os
from typing import Any

import requests


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
