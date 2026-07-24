from __future__ import annotations

import os
from pathlib import Path


def find_dotenv(start: Path | None = None) -> Path | None:
    """Walk upward from start (default cwd) looking for a .env file."""
    cur = (start or Path.cwd()).resolve()
    for directory in (cur, *cur.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
        # Stop at repo root markers so we do not scan the whole drive.
        if (directory / "py" / "apps").is_dir() and (directory / "py" / "libs").is_dir():
            break
        if (directory / ".git").exists():
            break
    return None


def load_dotenv(path: Path | None = None, *, override: bool = False) -> Path | None:
    """Load KEY=VALUE pairs from .env into os.environ.

    Does not override existing environment variables unless override=True.
    Returns the path loaded, or None if no file was found.
    """
    env_path = path or find_dotenv()
    if env_path is None or not env_path.is_file():
        return None

    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if not override and key in os.environ:
            continue
        os.environ[key] = value
    return env_path


def openai_key_present() -> bool:
    return bool((os.getenv("OPENAI_API_KEY") or "").strip())


def llm_credentials_present(provider: str | None = None) -> bool:
    """True when the API key for the active (or given) CREATOR_LLM_PROVIDER is set."""
    from .llm.resolve import llm_credentials_present as _present

    return _present(provider)
