from __future__ import annotations

import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type

from .base import CreatorAppBase
from .output import validate_output

StatusCallback = Callable[[str], None]


def repo_py_root(start: Path | None = None) -> Path:
    """Locate the `py/` directory that contains `apps/` and `libs/`."""
    cur = (start or Path.cwd()).resolve()
    for directory in (cur, *cur.parents):
        apps = directory / "apps"
        libs = directory / "libs"
        if apps.is_dir() and libs.is_dir():
            return directory
        nested = directory / "py"
        if (nested / "apps").is_dir() and (nested / "libs").is_dir():
            return nested
    raise FileNotFoundError(
        "Could not find py/ with apps/ and libs/. Run from the creator-apps repo."
    )


def ensure_import_paths(py_root: Path | None = None) -> Path:
    """Put py/ and SDK src on sys.path for local runs."""
    root = py_root or repo_py_root()
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    sdk_src = root / "libs" / "bpeai_creator_sdk" / "src"
    if sdk_src.is_dir():
        sdk_s = str(sdk_src)
        if sdk_s not in sys.path:
            sys.path.insert(0, sdk_s)
    return root


def resolve_app_id(app_id: str | None = None, *, cwd: Path | None = None) -> str:
    """Resolve app id from --app or from cwd under py/apps/<id>."""
    if app_id and app_id.strip():
        return app_id.strip()
    cur = (cwd or Path.cwd()).resolve()
    parts = cur.parts
    for i, part in enumerate(parts):
        if part == "apps" and i + 1 < len(parts):
            candidate = parts[i + 1]
            if candidate not in ("examples", "_template", "_templates") and not candidate.startswith(
                "."
            ) and not candidate.startswith("_"):
                return candidate
    raise ValueError(
        "Could not resolve app id. Pass --app <snake_case_id> or run from py/apps/<id>."
    )


def load_manifest(app_id: str, *, py_root: Path | None = None) -> Dict[str, Any]:
    root = py_root or repo_py_root()
    path = _app_manifest_path(app_id, root)
    return json.loads(path.read_text(encoding="utf-8"))


def _app_dir(app_id: str, root: Path) -> Path:
    """Resolve ``apps/<id>`` or ``apps/_templates/<id>``."""
    direct = root / "apps" / app_id
    if (direct / "manifest.json").is_file():
        return direct
    nested = root / "apps" / "_templates" / app_id
    if (nested / "manifest.json").is_file():
        return nested
    raise FileNotFoundError(
        f"App '{app_id}' not found under apps/ or apps/_templates/ (looking for manifest.json)"
    )


def _app_manifest_path(app_id: str, root: Path) -> Path:
    return _app_dir(app_id, root) / "manifest.json"

def _agent_class_from_module(module: Any) -> Type[CreatorAppBase]:
    candidates: list[Type[CreatorAppBase]] = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if obj is CreatorAppBase:
            continue
        if not issubclass(obj, CreatorAppBase):
            continue
        if obj.__module__ != module.__name__:
            continue
        candidates.append(obj)
    if not candidates:
        raise RuntimeError(f"No CreatorAppBase subclass found in {module.__name__}")
    if len(candidates) == 1:
        return candidates[0]
    # Prefer class whose name ends with Agent.
    for cls in candidates:
        if cls.__name__.endswith("Agent"):
            return cls
    return candidates[0]


def load_agent_class(
    app_id: str,
    *,
    py_root: Path | None = None,
    python_module: str | None = None,
    agent_class: str | None = None,
) -> Type[CreatorAppBase]:
    """Import the agent class for an app id (manifest-aware)."""
    root = ensure_import_paths(py_root)
    manifest = load_manifest(app_id, py_root=root)
    module_name = python_module or str(manifest.get("python_entrypoint") or f"apps.{app_id}.agent")
    module = importlib.import_module(module_name)
    if agent_class:
        cls = getattr(module, agent_class, None)
        if cls is None:
            raise AttributeError(f"{module_name} has no class {agent_class}")
        if not (inspect.isclass(cls) and issubclass(cls, CreatorAppBase)):
            raise TypeError(f"{agent_class} is not a CreatorAppBase subclass")
        return cls
    return _agent_class_from_module(module)


def is_selector_result(result: Dict[str, Any]) -> bool:
    """True when the payload should be validated as equipment_selector_v1."""
    if not isinstance(result, dict):
        return False
    phase = str(result.get("phase") or "").strip().lower()
    if phase in {"dir_requirements", "dir"}:
        return False
    schema = str(result.get("schema_version") or "").strip()
    if schema == "equipment_selector_v1":
        return True
    if phase in {"evaluation", "evaluate"}:
        return True
    # Heuristic: final selector cards always include these keys.
    return bool(result.get("equipment_tag") and result.get("selected_model") and result.get("rationale"))


def _manifest_llm_overrides(app_id: str, py_root: Path | None) -> Dict[str, Any]:
    """Read llm_* fields from apps/<id>/manifest.json when present."""
    root = py_root or repo_py_root()
    path = root / "apps" / app_id / "manifest.json"
    if not path.is_file():
        return {}
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, Any] = {}
    if data.get("llm_provider"):
        out["provider"] = str(data["llm_provider"]).strip()
    if data.get("llm_model"):
        out["model"] = str(data["llm_model"]).strip()
    if data.get("llm_max_output_tokens") is not None:
        try:
            out["max_output_tokens"] = int(data["llm_max_output_tokens"])
        except (TypeError, ValueError):
            pass
    return out


def run_agent(
    app_id: str,
    inputs: Dict[str, Any],
    *,
    status_callback: Optional[StatusCallback] = None,
    py_root: Path | None = None,
    python_module: str | None = None,
    agent_class: str | None = None,
) -> Dict[str, Any]:
    """Instantiate agent, call run(inputs); validate selector results only."""
    cls = load_agent_class(
        app_id,
        py_root=py_root,
        python_module=python_module,
        agent_class=agent_class,
    )
    agent = cls(status_callback=status_callback)
    overrides = _manifest_llm_overrides(app_id, py_root)
    restore = None
    if overrides:
        try:
            from bpeai_creator_sdk.llm.resolve import push_run_overrides

            restore = push_run_overrides(
                provider=overrides.get("provider"),
                model=overrides.get("model"),
                max_output_tokens=overrides.get("max_output_tokens"),
            )
        except Exception:
            restore = None
    try:
        result = agent.run(inputs)
    finally:
        if restore is not None:
            restore()
    if not isinstance(result, dict):
        raise TypeError("Agent.run() must return a dict")
    if is_selector_result(result):
        # Validate core schema fields, but keep agent extras (phase, dir_code,
        # system_name, pptx_prompt, decoded_dir, etc.) that are not on the model.
        validated = validate_output(result).model_dump()
        merged = dict(result)
        merged.update(validated)
        return merged
    return result
