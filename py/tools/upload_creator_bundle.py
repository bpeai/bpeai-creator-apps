#!/usr/bin/env python3
"""One-shot upload of local EI apps + knowledge packs to the creator portal.

From a bpeai-creator-apps (or website) clone:

  set BPEAI_PLATFORM_URL=https://bpiplatform.bpeai.com
  set BPEAI_SESSION_COOKIE=name=value   # logged-in portal session cookie
  python py/tools/upload_creator_bundle.py
  python py/tools/upload_creator_bundle.py --apps vent_filter_expert --packs vent-filter-expert
  python py/tools/upload_creator_bundle.py --zip-only -o bundle.zip

Discovers py/apps/*/agent.py (skips _templates) and py/knowledge/*/pack.yaml
(skips _examples). Folder names may differ from manifest ids.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

SKIP_APP_DIRS = {"_templates", "examples", "__pycache__"}
SKIP_PACK_DIRS = {"_examples", "examples", "__pycache__"}
SKIP_FILE_PARTS = {".env", "__pycache__", "artifacts", ".venv", "venv", ".git"}
ALLOW_SUFFIX = {
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".toml",
    ".csv",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_FILE_PARTS:
        return True
    name = path.name.lower()
    if name.startswith(".env") or name in {"credentials.json", "secrets.json"}:
        return True
    if path.is_file() and path.suffix.lower() not in ALLOW_SUFFIX:
        return True
    return False


def discover_apps(root: Path, only: list[str] | None) -> list[Path]:
    apps_root = root / "py" / "apps"
    if not apps_root.is_dir():
        return []
    found: list[Path] = []
    for child in sorted(apps_root.iterdir()):
        if not child.is_dir() or child.name in SKIP_APP_DIRS or child.name.startswith("_"):
            continue
        if only and child.name not in only and child.name.replace("_", "-") not in only:
            continue
        if (child / "agent.py").is_file():
            found.append(child)
    return found


def discover_packs(root: Path, only: list[str] | None) -> list[Path]:
    packs_root = root / "py" / "knowledge"
    if not packs_root.is_dir():
        return []
    found: list[Path] = []
    for child in sorted(packs_root.iterdir()):
        if not child.is_dir() or child.name in SKIP_PACK_DIRS or child.name.startswith("_"):
            continue
        if only and child.name not in only and child.name.replace("_", "-") not in only:
            continue
        if (child / "pack.yaml").is_file() or (child / "pack.yml").is_file():
            found.append(child)
    return found


def add_tree(zf: zipfile.ZipFile, folder: Path, arc_prefix: str) -> int:
    count = 0
    for path in folder.rglob("*"):
        if not path.is_file() or _should_skip(path):
            continue
        rel = path.relative_to(folder).as_posix()
        zf.write(path, f"{arc_prefix}/{rel}")
        count += 1
    return count


def build_zip(root: Path, apps: list[Path], packs: list[Path], out: Path) -> int:
    total = 0
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for app in apps:
            total += add_tree(zf, app, f"py/apps/{app.name}")
        for pack in packs:
            total += add_tree(zf, pack, f"py/knowledge/{pack.name}")
    return total


def upload(zip_path: Path, base_url: str, cookie: str) -> dict:
    boundary = "----BpeaiCreatorBundle7MA4YWxkTrZu0gW"
    body = bytearray()
    filename = zip_path.name
    data = zip_path.read_bytes()
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        (
            f'Content-Disposition: form-data; name="bundle"; filename="{filename}"\r\n'
            "Content-Type: application/zip\r\n\r\n"
        ).encode()
    )
    body.extend(data)
    body.extend(f"\r\n--{boundary}--\r\n".encode())

    url = f"{base_url.rstrip('/')}/api/platform/apps/upload"
    req = urllib.request.Request(
        url,
        data=bytes(body),
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Cookie": cookie,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            import json

            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload local EI apps/packs to bpiplatform")
    parser.add_argument("--root", type=Path, default=None, help="Repo root (default: auto)")
    parser.add_argument("--apps", nargs="*", default=None, help="Only these app folder names")
    parser.add_argument("--packs", nargs="*", default=None, help="Only these knowledge folder names")
    parser.add_argument("--zip-only", action="store_true", help="Write zip; do not upload")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Zip output path")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BPEAI_PLATFORM_URL", "https://bpiplatform.bpeai.com"),
    )
    args = parser.parse_args()

    root = (args.root or _repo_root()).resolve()
    apps = discover_apps(root, args.apps)
    packs = discover_packs(root, args.packs)
    if not apps and not packs:
        print(
            f"No apps/packs found under {root / 'py'}. "
            "Expected py/apps/<id>/agent.py and/or py/knowledge/<pack>/pack.yaml",
            file=sys.stderr,
        )
        return 2

    print("Apps:", ", ".join(a.name for a in apps) or "(none)")
    print("Packs:", ", ".join(p.name for p in packs) or "(none)")

    if args.zip_only or args.output:
        out = args.output or Path("creator-bundle.zip")
        n = build_zip(root, apps, packs, out)
        print(f"Wrote {out} ({n} files)")
        if args.zip_only:
            return 0
        zip_path = out
    else:
        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        zip_path = Path(tmp.name)
        tmp.close()
        n = build_zip(root, apps, packs, zip_path)
        print(f"Built temp zip ({n} files)")

    cookie = os.environ.get("BPEAI_SESSION_COOKIE", "").strip()
    if not cookie:
        print(
            "Set BPEAI_SESSION_COOKIE to your logged-in portal session cookie "
            "(DevTools → Application → Cookies).",
            file=sys.stderr,
        )
        return 2

    result = upload(zip_path, args.base_url, cookie)
    import json

    print(json.dumps(result, indent=2))
    if not args.output and zip_path.exists() and zip_path.name.startswith("tmp"):
        try:
            zip_path.unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
