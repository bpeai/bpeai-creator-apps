"""SME/creator helpers for managing knowledge-pack reference PPTX decks.

Reference decks under ``py/knowledge/<pack>/references/`` are visual style guides.
The evaluator renderer recreates that look in code; replacing a reference PPTX lets
SMEs update the target visual system and keep pack docs in sync.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Mapping


def references_dir(pack_path: Path | str) -> Path:
    return Path(pack_path) / "references"


def list_reference_decks(
    pack_path: Path | str,
    *,
    outline: Mapping[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """List reference PPTX files for a knowledge pack.

    Prefer ``pptx_outline.yaml`` ``reference_decks`` entries when present; also
    include any extra ``*.pptx`` found under ``references/``.
    """
    root = Path(pack_path)
    ref_root = references_dir(root)
    declared: List[str] = []
    if isinstance(outline, Mapping):
        raw = outline.get("reference_decks") or []
        if isinstance(raw, list):
            declared = [str(x).replace("\\", "/").lstrip("./") for x in raw if str(x).strip()]

    seen: set[str] = set()
    out: List[Dict[str, Any]] = []

    def _add(rel: str, *, declared_entry: bool) -> None:
        key = rel.replace("\\", "/").lower()
        if key in seen:
            return
        seen.add(key)
        path = root / rel if not Path(rel).is_absolute() else Path(rel)
        # Allow "references/foo.pptx" or bare "foo.pptx"
        if not path.is_file() and not rel.startswith("references/"):
            alt = ref_root / Path(rel).name
            if alt.is_file():
                path = alt
                rel = f"references/{alt.name}"
        out.append(
            {
                "relative_path": rel.replace("\\", "/"),
                "path": str(path.resolve()) if path.exists() else str(path),
                "exists": path.is_file(),
                "declared": declared_entry,
                "name": Path(rel).name,
            }
        )

    for rel in declared:
        _add(rel, declared_entry=True)

    if ref_root.is_dir():
        for pptx in sorted(ref_root.glob("*.pptx")):
            _add(f"references/{pptx.name}", declared_entry=False)

    return out


def resolve_reference_deck(
    pack_path: Path | str,
    name_or_path: str,
    *,
    outline: Mapping[str, Any] | None = None,
) -> Path:
    """Resolve a reference deck by file name or relative path."""
    needle = (name_or_path or "").strip().replace("\\", "/")
    if not needle:
        raise ValueError("name_or_path is required")
    for entry in list_reference_decks(pack_path, outline=outline):
        if entry["name"].lower() == Path(needle).name.lower():
            path = Path(entry["path"])
            if path.is_file():
                return path
        if entry["relative_path"].lower() == needle.lower():
            path = Path(entry["path"])
            if path.is_file():
                return path
    # Direct path under references/
    candidate = references_dir(pack_path) / Path(needle).name
    if candidate.is_file():
        return candidate.resolve()
    raise FileNotFoundError(f"Reference PPTX not found: {name_or_path}")


def replace_reference_deck(
    pack_path: Path | str,
    source_pptx: Path | str,
    *,
    dest_name: str | None = None,
    outline_path: Path | str | None = None,
    register_in_outline: bool = True,
) -> Path:
    """Copy ``source_pptx`` into the pack ``references/`` folder (replace if present).

    Optionally appends the new relative path to ``pptx_outline.yaml`` ``reference_decks``.
    """
    src = Path(source_pptx)
    if not src.is_file():
        raise FileNotFoundError(f"Source PPTX not found: {src}")
    if src.suffix.lower() != ".pptx":
        raise ValueError("Source must be a .pptx file")

    root = Path(pack_path)
    ref_root = references_dir(root)
    ref_root.mkdir(parents=True, exist_ok=True)
    name = dest_name or src.name
    if not name.lower().endswith(".pptx"):
        name = f"{name}.pptx"
    dest = ref_root / name
    shutil.copy2(src, dest)

    if register_in_outline:
        yaml_path = Path(outline_path) if outline_path else root / "pptx_outline.yaml"
        if yaml_path.is_file():
            _ensure_outline_lists_deck(yaml_path, f"references/{name}")

    return dest.resolve()


def _ensure_outline_lists_deck(outline_path: Path, relative: str) -> None:
    import yaml

    raw = yaml.safe_load(outline_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return
    decks = raw.get("reference_decks")
    if not isinstance(decks, list):
        decks = []
    rel = relative.replace("\\", "/")
    existing = {str(x).replace("\\", "/").lower() for x in decks}
    if rel.lower() not in existing:
        decks.append(rel)
        raw["reference_decks"] = decks
        outline_path.write_text(
            yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
