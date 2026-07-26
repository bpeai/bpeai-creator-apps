"""Resolve platform packs for integration tests (not shipped in creator-apps)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from bpeai_creator_sdk.sme import load_knowledge_pack


def platform_knowledge_root(creator_py_root: Path) -> Path | None:
    """Prefer BPEAI_KNOWLEDGE_ROOT, then sibling bpeai/py/knowledge."""
    env = (os.getenv("BPEAI_KNOWLEDGE_ROOT") or "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            return p.resolve()
    # creator-apps/py → website/bpeai/py/knowledge
    sibling = (creator_py_root.parent.parent / "bpeai" / "py" / "knowledge").resolve()
    if sibling.is_dir():
        return sibling
    # creator-apps next to bpeai
    alt = (creator_py_root.parent.parent.parent / "bpeai" / "py" / "knowledge").resolve()
    if alt.is_dir():
        return alt
    return None


def load_platform_pack_or_skip(pack_id: str, creator_py_root: Path):
    root = platform_knowledge_root(creator_py_root)
    if root is None or not (root / pack_id / "pack.yaml").is_file():
        pytest.skip(
            f"Platform pack '{pack_id}' not available. "
            "Set BPEAI_KNOWLEDGE_ROOT to bpeai/py/knowledge or run beside the bpeai repo."
        )
    return load_knowledge_pack(pack_id, pack_root=root)
