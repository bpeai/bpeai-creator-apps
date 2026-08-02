#!/usr/bin/env python3
"""Download a private knowledge pack from bpiplatform into py/knowledge/<pack_id>/.

Usage (from bpeai-creator-apps or bpeai):
  set BPEAI_PLATFORM_URL=https://bpiplatform.bpeai.com
  set BPEAI_SESSION_COOKIE=bpeai_session=...
  python py/tools/download_knowledge_pack.py --pack <slug-or-id> --out py/knowledge

Requires a logged-in creator session cookie.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", required=True, help="Pack id or slug")
    parser.add_argument(
        "--out",
        default="py/knowledge",
        help="Parent directory for pack folder (default py/knowledge)",
    )
    parser.add_argument(
        "--base",
        default=os.environ.get("BPEAI_PLATFORM_URL")
        or os.environ.get("NEXT_PUBLIC_PLATFORM_URL")
        or "https://bpiplatform.bpeai.com",
    )
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Download zip (download-zip) and extract into --out",
    )
    args = parser.parse_args()

    cookie = (
        os.environ.get("BPEAI_SESSION_COOKIE")
        or os.environ.get("SESSION_COOKIE")
        or ""
    ).strip()
    if not cookie:
        print("Set BPEAI_SESSION_COOKIE to your bpeai_session cookie value.", file=sys.stderr)
        return 2

    cookie_header = cookie if "=" in cookie else f"bpeai_session={cookie}"

    if args.zip:
        import io
        import zipfile

        url = f"{args.base.rstrip('/')}/api/platform/knowledge-packs/{args.pack}/download-zip"
        req = urllib.request.Request(
            url,
            headers={"Cookie": cookie_header, "Accept": "application/zip"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
                cv = resp.headers.get("X-BPEAI-Content-Version", "?")
        except urllib.error.HTTPError as exc:
            print(f"Download failed: HTTP {exc.code} {exc.read()[:500]!r}", file=sys.stderr)
            return 1
        out_root = Path(args.out)
        out_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            zf.extractall(out_root)
            for n in zf.namelist():
                print(f"Wrote {out_root / n}")
        print(f"Done. content_version={cv} under {out_root}")
        return 0

    url = f"{args.base.rstrip('/')}/api/platform/knowledge-packs/{args.pack}/download"
    req = urllib.request.Request(
        url,
        headers={"Cookie": cookie_header, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"Download failed: HTTP {exc.code} {exc.read()[:500]!r}", file=sys.stderr)
        return 1

    pack_id = str(data.get("pack_id") or args.pack)
    out_dir = Path(args.out) / pack_id
    out_dir.mkdir(parents=True, exist_ok=True)
    files = data.get("files") or {}
    for name, text in files.items():
        path = out_dir / name
        path.write_text(str(text), encoding="utf-8")
        print(f"Wrote {path}")
    print(
        f"Done. release={data.get('release_version')} content_version={data.get('content_version')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
