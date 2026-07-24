#!/usr/bin/env python3
"""Local smart-text chat runner for BPEAI creator apps.

Mirrors the website handshake (status callback + validated equipment_selector_v1
or DIR questionnaire phase) without requiring JSON stdin.
Optional personal OPENAI_API_KEY via .env.

Examples (PowerShell):

  python py/tools/local_chat.py --app equipment_evaluator
  # > Media prep vessel, biopharma
  # > 2-1-2-3-1-1
  # > pptx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict


def _bootstrap_sdk() -> None:
    """Allow running this script without an editable install."""
    tools_dir = Path(__file__).resolve().parent
    py_root = tools_dir.parent
    sdk_src = py_root / "libs" / "bpeai_creator_sdk" / "src"
    for path in (str(py_root), str(sdk_src)):
        if path not in sys.path:
            sys.path.insert(0, path)


_bootstrap_sdk()

from bpeai_creator_sdk.local_env import load_dotenv, llm_credentials_present, openai_key_present  # noqa: E402
from bpeai_creator_sdk.local_format import format_result_text, format_selector_json  # noqa: E402
from bpeai_creator_sdk.local_parse import parse_free_text  # noqa: E402
from bpeai_creator_sdk.local_run import resolve_app_id, run_agent  # noqa: E402
from bpeai_creator_sdk.base import default_creator_model, default_creator_provider  # noqa: E402


def _status(message: str) -> None:
    print(message, file=sys.stderr)


def _is_pptx_request(text: str) -> bool:
    return text.strip().lower() in {"y", "yes", "pptx", "ppt", "deck"}


def _is_storable_evaluation(result: Dict[str, Any]) -> bool:
    """True when the result should be kept for a follow-up PPTX request."""
    if not isinstance(result, dict):
        return False
    phase = str(result.get("phase") or "").strip().lower()
    if phase in {"dir_requirements", "dir", "pptx_error"}:
        return False
    if result.get("requirements") and not result.get("selected_model"):
        return False
    return bool(
        result.get("selected_model")
        and (
            result.get("schema_version") == "equipment_selector_v1"
            or result.get("mixing_options")
            or result.get("rationale")
            or phase in {"evaluation", "evaluate"}
        )
    )


def _run_once(
    app_id: str,
    text: str,
    *,
    as_json: bool,
    session: Dict[str, Any] | None = None,
) -> int:
    session = session if session is not None else {}

    if _is_pptx_request(text):
        prior = session.get("last_evaluation")
        if not isinstance(prior, dict):
            print(
                "No evaluation in this session yet. Run a DIR code evaluation first, then reply pptx.",
                file=sys.stderr,
            )
            return 1
        inputs = {
            "system_name": prior.get("system_name") or session.get("system_name") or "Process Vessel",
            "application": prior.get("application") or session.get("application") or "biopharmaceutical",
            "dir_code": prior.get("dir_code") or "",
            "deliverable": "pptx",
            "evaluation_result": prior,
            "phase": "pptx",
        }
        result = run_agent(app_id, inputs, status_callback=_status)
        if as_json:
            sys.stdout.write(format_selector_json(result))
        else:
            sys.stdout.write(format_result_text(result))
        pptx_path = (result.get("artifacts") or {}).get("pptx_path") if isinstance(result.get("artifacts"), dict) else None
        if pptx_path:
            print(f"Wrote PPTX: {pptx_path}", file=sys.stderr)
        return 0

    inputs = parse_free_text(text)

    # Carry system_name / application across turns for DIR code replies.
    if inputs.get("dir_code"):
        if not inputs.get("system_name") and session.get("system_name"):
            inputs["system_name"] = session["system_name"]
        if not inputs.get("application") and session.get("application"):
            inputs["application"] = session["application"]

    if not inputs.get("system_name"):
        print(
            "Could not derive system_name from your text. "
            "Try naming the vessel/tank (DIR codes reuse the last system name).",
            file=sys.stderr,
        )
        return 1

    if inputs.get("system_name"):
        session["system_name"] = inputs["system_name"]
    if inputs.get("application"):
        session["application"] = inputs["application"]

    result = run_agent(app_id, inputs, status_callback=_status)
    # Preserve session fields the schema may not carry through validation alone.
    if not result.get("system_name") and session.get("system_name"):
        result["system_name"] = session["system_name"]
    if not result.get("application") and session.get("application"):
        result["application"] = session["application"]
    if _is_storable_evaluation(result):
        session["last_evaluation"] = result

    if as_json:
        sys.stdout.write(format_selector_json(result))
    else:
        sys.stdout.write(format_result_text(result))
    return 0


def _interactive(app_id: str, *, as_json: bool) -> int:
    provider = default_creator_provider()
    model = default_creator_model()
    if llm_credentials_present(provider):
        key_note = f"{provider} credentials set"
    elif provider == "openai" and openai_key_present():
        key_note = "OPENAI_API_KEY set"
    else:
        key_note = f"no credentials for {provider} (heuristics only)"
    print(f"Local chat — app: {app_id} ({key_note})", file=sys.stderr)
    print(
        f"LLM: {provider}/{model} "
        f"(set CREATOR_LLM_PROVIDER / CREATOR_LLM_MODEL or OPENAI_CREATOR_MODEL in .env)",
        file=sys.stderr,
    )
    print(
        "Type plain English, then a DIR code (e.g. 2-1-2-3-1-1). "
        "After evaluation, reply pptx (or y) for a 7-slide deck. "
        "Commands: quit / exit / blank line to leave.",
        file=sys.stderr,
    )
    session: Dict[str, Any] = {}
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
            return 0
        if not line or line.lower() in {"quit", "exit", "q"}:
            return 0
        try:
            code = _run_once(app_id, line, as_json=as_json, session=session)
        except Exception as exc:  # noqa: BLE001 — show creator-friendly errors
            print(f"Error: {exc}", file=sys.stderr)
            continue
        if code != 0:
            continue
        print(file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Local smart-text chat for BPEAI creator selector apps.",
    )
    parser.add_argument(
        "--app",
        help="App id (snake_case under py/apps/ or py/apps/_templates/). Default: infer from cwd.",
    )
    parser.add_argument(
        "--once",
        metavar="TEXT",
        help="Run a single free-text query and exit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON instead of smart text (DIR or equipment_selector_v1).",
    )
    parser.add_argument(
        "--env",
        metavar="PATH",
        help="Path to .env (default: search upward from cwd).",
    )
    args = parser.parse_args(argv)

    env_path = Path(args.env) if args.env else None
    loaded = load_dotenv(env_path)
    if loaded:
        print(f"Loaded env: {loaded}", file=sys.stderr)

    try:
        app_id = resolve_app_id(args.app)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.once is not None:
        try:
            return _run_once(app_id, args.once, as_json=args.json, session={})
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    return _interactive(app_id, as_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
