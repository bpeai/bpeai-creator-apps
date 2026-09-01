from __future__ import annotations

"""Keep a creator EI app and its private knowledge pack on the same id.

Canonical id is the app ``id`` (snake_case). Auto-renames the pack folder and
rewrites ``pack.yaml`` / ``manifest.json`` / ``agent.py`` when the pairing is
unambiguous. Collision (two distinct pack folders mapping to one app) is reported
and not merged.
"""

from pathlib import Path
from typing import Any, Dict, List, NamedTuple

import json
import re

import yaml

from .pack_loader import knowledge_root


def normalize_pack_id(raw: str) -> str:
    """Snake_case id used for app folders, pack folders, and pack_id."""
    return re.sub(r"[^a-z0-9]+", "_", (raw or "").strip().lower()).strip("_")[:64]


def ids_equivalent(left: str, right: str) -> bool:
    return normalize_pack_id(left) == normalize_pack_id(right) and bool(
        normalize_pack_id(left)
    )


class PackAlignResult(NamedTuple):
    pack_id: str
    notes: List[str]
    collision: bool = False


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def read_app_pack_pointer(app_dir: Path) -> str:
    """Manifest ``knowledge_pack`` first, then ``agent.py`` ``knowledge_pack_id``."""
    manifest = app_dir / "manifest.json"
    if manifest.is_file():
        data = _load_json(manifest)
        ref = str(data.get("knowledge_pack") or "").strip()
        if ref:
            return ref
    agent = app_dir / "agent.py"
    if agent.is_file():
        try:
            text = agent.read_text(encoding="utf-8")
        except OSError:
            return ""
        match = re.search(r'knowledge_pack_id\s*=\s*["\']([^"\']+)["\']', text)
        if match:
            return match.group(1).strip()
    return ""


def rewrite_pack_yaml_id(pack_root: Path, pack_id: str) -> bool:
    path = pack_root / "pack.yaml"
    if not path.is_file():
        alt = pack_root / "pack.yml"
        path = alt if alt.is_file() else path
    if not path.is_file():
        return False
    try:
        meta = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return False
    if not isinstance(meta, dict):
        return False
    current = str(meta.get("pack_id") or "").strip()
    if current == pack_id:
        return False
    meta["pack_id"] = pack_id
    path.write_text(
        yaml.safe_dump(meta, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return True


def rewrite_app_pack_pointers(app_dir: Path, pack_id: str) -> List[str]:
    """Set manifest.knowledge_pack and agent.knowledge_pack_id to ``pack_id``."""
    notes: List[str] = []
    if not app_dir.is_dir():
        return notes

    manifest = app_dir / "manifest.json"
    if manifest.is_file():
        data = _load_json(manifest)
        if data and str(data.get("knowledge_pack") or "").strip() != pack_id:
            data["knowledge_pack"] = pack_id
            manifest.write_text(
                json.dumps(data, indent=2) + "\n",
                encoding="utf-8",
            )
            notes.append(f"Set {manifest.name} knowledge_pack to '{pack_id}'.")

    agent = app_dir / "agent.py"
    if agent.is_file():
        try:
            text = agent.read_text(encoding="utf-8")
        except OSError:
            return notes
        updated, count = re.subn(
            r'(knowledge_pack_id\s*=\s*)(["\'])([^"\']*)\2',
            rf"\1\2{pack_id}\2",
            text,
            count=1,
        )
        if count and updated != text:
            agent.write_text(updated, encoding="utf-8")
            notes.append(f"Set agent.py knowledge_pack_id to '{pack_id}'.")
    return notes


def align_pack_to_app(
    app_id: str,
    *,
    py_root: Path | None = None,
    pack_id: str | None = None,
) -> PackAlignResult:
    """Make pack folder, pack.yaml pack_id, and app pointers match ``app_id``.

    If ``py/knowledge/<app_id>/`` already exists and a *different* pack folder
    also exists, leave both folders and report a collision (use the app-id pack).
    """
    notes: List[str] = []
    canonical = normalize_pack_id(app_id)
    if not canonical:
        raise ValueError("app_id is required")

    root = Path(py_root) if py_root is not None else knowledge_root().parent
    kroot = knowledge_root(root)
    app_dir = root / "apps" / canonical
    dest = kroot / canonical

    hinted = pack_id or read_app_pack_pointer(app_dir) or canonical
    current = normalize_pack_id(hinted) or canonical
    src = kroot / current

    dest_exists = dest.is_dir()
    src_exists = src.is_dir()
    same_folder = dest_exists and src_exists and dest.resolve() == src.resolve()

    if dest_exists and src_exists and not same_folder:
        rewrite_pack_yaml_id(dest, canonical)
        notes.append(
            f"Collision: pack folders '{current}' and '{canonical}' both exist; "
            f"using '{canonical}' and leaving '{current}' unchanged."
        )
        notes.extend(rewrite_app_pack_pointers(app_dir, canonical))
        return PackAlignResult(pack_id=canonical, notes=notes, collision=True)

    if dest_exists:
        if rewrite_pack_yaml_id(dest, canonical):
            notes.append(f"Aligned pack.yaml pack_id to '{canonical}'.")
        notes.extend(rewrite_app_pack_pointers(app_dir, canonical))
        return PackAlignResult(pack_id=canonical, notes=notes)

    if src_exists and current != canonical:
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dest)
        notes.append(f"Renamed pack folder '{current}' → '{canonical}'.")
        if rewrite_pack_yaml_id(dest, canonical):
            notes.append(f"Aligned pack.yaml pack_id to '{canonical}'.")
        notes.extend(rewrite_app_pack_pointers(app_dir, canonical))
        return PackAlignResult(pack_id=canonical, notes=notes)

    notes.extend(rewrite_app_pack_pointers(app_dir, canonical))
    if current != canonical:
        notes.append(
            f"Aligned knowledge_pack pointers to '{canonical}' "
            "(pack folder will be created on bootstrap)."
        )
    return PackAlignResult(pack_id=canonical, notes=notes)
