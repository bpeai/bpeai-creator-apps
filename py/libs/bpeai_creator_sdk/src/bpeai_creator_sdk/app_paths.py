"""Resolve nested creator-app and knowledge-pack folders.

Live copies live under ``py/apps/<family>/<app_id>/`` and
``py/knowledge/<family>/<app_id>/``. Templates stay at
``py/apps/_templates/<family>/``. Example stubs stay at
``py/knowledge/_examples/<stub>/``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

TEMPLATE_FAMILIES: tuple[str, ...] = ("equipment_evaluator", "equipment_sizing")


def split_family_leaf(raw: str) -> tuple[str | None, str]:
    """Split ``family/leaf`` (or ``family\\leaf``) into parts. Leaf-only → ``(None, leaf)``."""
    text = (raw or "").replace("\\", "/").strip().strip("/")
    if not text:
        return None, ""
    if "/" in text:
        family, leaf = text.split("/", 1)
        family = family.strip()
        leaf = leaf.strip().strip("/")
        if family and leaf:
            return family, leaf
        return None, text.replace("/", "_")
    return None, text


def normalize_app_ref(raw: str) -> str:
    family, leaf = split_family_leaf(raw)
    if family and leaf:
        return f"{family}/{leaf}"
    return leaf


def _unique_existing(paths: Iterable[Path], *, marker: str) -> list[Path]:
    found: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        key = str(resolved)
        if key in seen:
            continue
        if (resolved / marker).is_file():
            seen.add(key)
            found.append(resolved)
    return found


def iter_app_dir_candidates(
    app_id: str,
    apps_root: Path,
    *,
    family: str | None = None,
) -> list[Path]:
    fam, leaf = split_family_leaf(app_id)
    family = fam or family
    if not leaf:
        return []
    out: list[Path] = []
    if family:
        out.append(apps_root / family / leaf)
        # `_templates/<family>` is the template itself, not a live leaf app.
        if leaf == family:
            out.append(apps_root / "_templates" / family)
    out.append(apps_root / leaf)
    out.append(apps_root / "_templates" / leaf)
    if not family:
        for known in TEMPLATE_FAMILIES:
            out.append(apps_root / known / leaf)
    return out


def _prefer_live_app(hits: list[Path]) -> Path | None:
    """When a live copy and the family template both match, keep the live copy."""
    if len(hits) == 1:
        return hits[0]
    live = [path for path in hits if "_templates" not in path.parts]
    if len(live) == 1:
        return live[0]
    return None


def resolve_app_dir(
    app_id: str,
    py_root: Path,
    *,
    family: str | None = None,
) -> Path:
    """Return the folder that contains ``manifest.json`` for ``app_id``."""
    apps_root = py_root / "apps"
    hits = _unique_existing(
        iter_app_dir_candidates(app_id, apps_root, family=family),
        marker="manifest.json",
    )
    preferred = _prefer_live_app(hits)
    if preferred is not None:
        return preferred
    if len(hits) > 1:
        names = ", ".join(path.as_posix() for path in hits)
        raise FileNotFoundError(
            f"App '{app_id}' matches multiple folders ({names}); pass family/leaf "
            f"(e.g. equipment_evaluator/{split_family_leaf(app_id)[1]})."
        )
    raise FileNotFoundError(
        f"App '{app_id}' not found under apps/, apps/<family>/, or apps/_templates/ "
        "(looking for manifest.json)"
    )


def app_zip_prefix(app_dir: Path, apps_root: Path) -> str:
    """Zip path prefix ``py/apps/<id>`` or ``py/apps/<family>/<id>``."""
    try:
        rel = app_dir.resolve().relative_to(apps_root.resolve()).as_posix()
    except ValueError:
        return f"py/apps/{app_dir.name}"
    return f"py/apps/{rel}"


def python_entrypoint_for(app_dir: Path, apps_root: Path) -> str:
    """Dotted module ``apps.<family>.<id>.agent`` or ``apps.<id>.agent``."""
    try:
        rel = app_dir.resolve().relative_to(apps_root.resolve())
    except ValueError:
        return f"apps.{app_dir.name}.agent"
    parts = [p for p in rel.parts if p not in {".", ".."}]
    if parts and parts[0] == "_templates":
        return "apps." + ".".join(("_templates", *parts[1:], "agent"))
    if parts:
        return "apps." + ".".join((*parts, "agent"))
    return f"apps.{app_dir.name}.agent"


def iter_pack_dir_candidates(
    pack_id: str,
    knowledge_root: Path,
    *,
    family: str | None = None,
) -> list[Path]:
    fam, leaf = split_family_leaf(pack_id)
    family = fam or family
    if not leaf:
        return []
    out: list[Path] = []
    if family:
        out.append(knowledge_root / family / leaf)
    out.append(knowledge_root / leaf)
    out.append(knowledge_root / "_examples" / leaf)
    if not family:
        for known in TEMPLATE_FAMILIES:
            out.append(knowledge_root / known / leaf)
    return out


def resolve_pack_dir(
    pack_id: str,
    knowledge_root: Path,
    *,
    family: str | None = None,
    create: bool = False,
) -> Path:
    """Return an existing pack folder, or the default path to create one."""
    hits = _unique_existing(
        iter_pack_dir_candidates(pack_id, knowledge_root, family=family),
        marker="pack.yaml",
    )
    yml_hits = _unique_existing(
        iter_pack_dir_candidates(pack_id, knowledge_root, family=family),
        marker="pack.yml",
    )
    combined: list[Path] = []
    seen: set[str] = set()
    for path in (*hits, *yml_hits):
        key = str(path)
        if key not in seen:
            seen.add(key)
            combined.append(path)
    if len(combined) == 1:
        return combined[0]
    if len(combined) > 1:
        raise FileNotFoundError(
            f"Pack '{pack_id}' matches multiple folders; pass family/leaf."
        )
    fam, leaf = split_family_leaf(pack_id)
    family = fam or family
    if family and leaf:
        target = knowledge_root / family / leaf
    else:
        target = knowledge_root / (leaf or pack_id)
    if create:
        return target.resolve()
    return target.resolve()


def infer_family_from_app_dir(app_dir: Path, apps_root: Path) -> str | None:
    try:
        rel = app_dir.resolve().relative_to(apps_root.resolve())
    except ValueError:
        return None
    parts = rel.parts
    if not parts:
        return None
    if parts[0] in TEMPLATE_FAMILIES:
        return parts[0]
    if parts[0] == "_templates" and len(parts) > 1 and parts[1] in TEMPLATE_FAMILIES:
        return parts[1]
    return None


def discover_live_app_dirs(apps_root: Path, only: Sequence[str] | None = None) -> list[Path]:
    """Find creator app folders (legacy top-level or family-nested). Skips templates."""
    if not apps_root.is_dir():
        return []
    wanted = {item.replace("\\", "/").strip("/") for item in (only or []) if item}
    found: list[Path] = []
    skip = {"_templates", "examples", "__pycache__"}
    for child in sorted(apps_root.iterdir()):
        if not child.is_dir() or child.name in skip or child.name.startswith("_"):
            continue
        if (child / "agent.py").is_file():
            if _matches_only(child.name, None, wanted):
                found.append(child)
            continue
        if child.name in TEMPLATE_FAMILIES or (child / "__init__.py").is_file():
            for leaf in sorted(child.iterdir()):
                if leaf.is_dir() and (leaf / "agent.py").is_file():
                    if _matches_only(leaf.name, child.name, wanted):
                        found.append(leaf)
    return found


def discover_live_pack_dirs(knowledge_root: Path, only: Sequence[str] | None = None) -> list[Path]:
    if not knowledge_root.is_dir():
        return []
    wanted = {item.replace("\\", "/").strip("/") for item in (only or []) if item}
    found: list[Path] = []
    skip = {"_examples", "examples", "__pycache__", "_templates"}
    for child in sorted(knowledge_root.iterdir()):
        if not child.is_dir() or child.name in skip or child.name.startswith("_"):
            continue
        if (child / "pack.yaml").is_file() or (child / "pack.yml").is_file():
            if _matches_only(child.name, None, wanted):
                found.append(child)
            continue
        if child.name in TEMPLATE_FAMILIES:
            for leaf in sorted(child.iterdir()):
                if leaf.is_dir() and (
                    (leaf / "pack.yaml").is_file() or (leaf / "pack.yml").is_file()
                ):
                    if _matches_only(leaf.name, child.name, wanted):
                        found.append(leaf)
    return found


def _matches_only(leaf: str, family: str | None, wanted: set[str]) -> bool:
    if not wanted:
        return True
    names = {leaf, leaf.replace("_", "-")}
    if family:
        names.add(f"{family}/{leaf}")
        names.add(f"{family}\\{leaf}")
    return bool(names & wanted)
