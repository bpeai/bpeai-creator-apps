#!/usr/bin/env python3
"""Pull / push knowledge pack JSON against the creator portal API.

Usage:
  set BPEAI_PLATFORM_URL=https://bpiplatform.bpeai.com
  set BPEAI_SESSION_COOKIE=...   # browser session cookie for authenticated portal
  python py/tools/sync_knowledge_pack.py pull --pack-id <id> --out ./my-pack.json
  python py/tools/sync_knowledge_pack.py push --pack-id <id> --in ./my-pack.json

Does not upload Python agent code. Pack content only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _request(method: str, url: str, cookie: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": cookie,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync knowledge packs with the portal")
    parser.add_argument("action", choices=["pull", "push"])
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("--out", type=Path, help="pull destination JSON")
    parser.add_argument("--in", dest="infile", type=Path, help="push source JSON")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BPEAI_PLATFORM_URL", "https://bpiplatform.bpeai.com"),
    )
    args = parser.parse_args()

    cookie = os.environ.get("BPEAI_SESSION_COOKIE", "").strip()
    if not cookie:
        print("Set BPEAI_SESSION_COOKIE to your portal session cookie.", file=sys.stderr)
        return 2

    base = args.base_url.rstrip("/")
    url = f"{base}/api/platform/knowledge-packs/{args.pack_id}"

    if args.action == "pull":
        out = args.out or Path(f"{args.pack_id}.json")
        payload = _request("GET", url, cookie)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {out}")
        return 0

    infile = args.infile
    if not infile or not infile.is_file():
        print("--in file required for push", file=sys.stderr)
        return 2
    body = json.loads(infile.read_text(encoding="utf-8"))
    # Accept either full GET payload or a flat pack patch
    patch = body.get("runtime_payload") or body.get("pack") or body
    content = patch.get("content") if isinstance(patch, dict) else None
    update = {
        "label": (body.get("pack") or {}).get("label") or patch.get("label"),
        "description": (body.get("pack") or {}).get("description") or patch.get("description"),
        "content": content or patch,
        "write_snapshot": True,
    }
    update = {k: v for k, v in update.items() if v is not None}
    result = _request("PATCH", url, cookie, update)
    print(json.dumps({"ok": True, "pack_id": result.get("pack", {}).get("id")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
