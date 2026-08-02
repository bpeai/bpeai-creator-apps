#!/usr/bin/env python3
"""Download an EI app code zip from bpiplatform (S3 library of record).

Usage (from bpeai-creator-apps):
  set BPEAI_PLATFORM_URL=https://bpiplatform.bpeai.com
  set BPEAI_SESSION_COOKIE=bpeai_session=...
  python py/tools/download_app_bundle.py --app vent_filter_expert --out py/apps

Extracts into py/apps/<app_id>/ (overwrites local files in that folder).
App code is only updated on the server when you re-upload — use this for backup/restore.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import zipfile
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True, help="App id (manifest id)")
    parser.add_argument(
        "--out",
        default="py/apps",
        help="Parent directory (default py/apps); zip contains apps/<id>/…",
    )
    parser.add_argument(
        "--base",
        default=os.environ.get("BPEAI_PLATFORM_URL")
        or os.environ.get("NEXT_PUBLIC_PLATFORM_URL")
        or "https://bpiplatform.bpeai.com",
    )
    parser.add_argument(
        "--zip-only",
        action="store_true",
        help="Write bundle.zip next to --out instead of extracting",
    )
    args = parser.parse_args()

    cookie = (
        os.environ.get("BPEAI_SESSION_COOKIE") or os.environ.get("SESSION_COOKIE") or ""
    ).strip()
    if not cookie:
        print("Set BPEAI_SESSION_COOKIE to your portal session cookie.", file=sys.stderr)
        return 2

    url = f"{args.base.rstrip('/')}/api/platform/apps/{args.app}/download"
    req = urllib.request.Request(
        url,
        headers={
            "Cookie": cookie if "=" in cookie else f"bpeai_session={cookie}",
            "Accept": "application/zip",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        print(f"Download failed: HTTP {exc.code} {exc.read()[:500]!r}", file=sys.stderr)
        return 1

    out_parent = Path(args.out)
    if args.zip_only:
        out_parent.mkdir(parents=True, exist_ok=True)
        dest = out_parent / f"{args.app}.zip"
        dest.write_bytes(data)
        print(f"Wrote {dest} ({len(data)} bytes)")
        return 0

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if name.endswith("/") or ".." in name.split("/"):
                continue
            # apps/<id>/rel or <id>/rel
            prefix = f"apps/{args.app}/"
            if name.startswith(prefix):
                rel = name[len(prefix) :]
            elif name.startswith(f"{args.app}/"):
                rel = name[len(args.app) + 1 :]
            else:
                continue
            target = out_parent / args.app / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(info))
            print(f"Wrote {target}")
    print(f"Done. Extracted under {out_parent / args.app}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
