"""Live DIR QA across allowlisted creator LLM providers.

Ship bar (per provider): evaluate DIR ``2-1-2-3-1-1`` / media_preparation and
produce schema-valid JSON with required report headings after ≤1 repair.

Run (from bpeai-creator-apps):

  pytest py/libs/bpeai_creator_sdk/tests/test_provider_dir_qa.py -m llm -v

Skipped automatically when the provider API key is missing.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from bpeai_creator_sdk.llm.allowlist import ALLOWLIST, DEFAULT_MODELS
from bpeai_creator_sdk.llm.resolve import llm_credentials_present
from bpeai_creator_sdk.local_run import ensure_import_paths, run_agent
from bpeai_creator_sdk.output import validate_output
from bpeai_creator_sdk.sme import (
    missing_report_headings,
    validate_dir_code,
)

from pack_paths import load_platform_pack_or_skip

DIR_CODE = "2-1-2-3-1-1"
SCENARIO = "media_preparation"
SYSTEM_NAME = "Media Prep Vessel"


def _provider_cases() -> list[tuple[str, str]]:
    cases: list[tuple[str, str]] = []
    for provider, allowed in ALLOWLIST.items():
        if allowed is None:
            model = (
                (os.getenv("CREATOR_LLM_MODEL") or "").strip()
                or (os.getenv("OPENAI_CREATOR_MODEL") or "").strip()
                or DEFAULT_MODELS["openai"]
            )
            cases.append((provider, model))
        else:
            for model in sorted(allowed):
                cases.append((provider, model))
    return cases


@pytest.fixture(scope="module")
def py_root() -> Path:
    return ensure_import_paths()


@pytest.fixture(scope="module")
def mixing_pack(py_root: Path):
    return load_platform_pack_or_skip("mixing", py_root)


@pytest.mark.llm
@pytest.mark.parametrize(
    "provider,model",
    list(_provider_cases()),
    ids=[f"{p}/{m}" for p, m in _provider_cases()],
)
def test_provider_dir_qa_evaluate(provider: str, model: str, mixing_pack, monkeypatch, py_root: Path):
    if not llm_credentials_present(provider):
        pytest.skip(f"No API credentials for provider={provider}")

    check = validate_dir_code(mixing_pack, SCENARIO, DIR_CODE)
    assert check.ok, check.error

    monkeypatch.setenv("CREATOR_LLM_PROVIDER", provider)
    monkeypatch.setenv("CREATOR_LLM_MODEL", model)

    inputs = {
        "system_name": SYSTEM_NAME,
        "application": "biopharma",
        "dir_code": DIR_CODE,
        "phase": "evaluate",
    }
    result = run_agent("equipment_evaluator", inputs, py_root=py_root)

    assert result.get("phase") != "dir_requirements", result
    assert not result.get("validation_error"), result.get("validation_error")

    validated = validate_output(result)
    assert validated.selected_model
    assert validated.schema_version == "equipment_selector_v1"

    md = str(result.get("datasheet_markdown") or result.get("rationale") or "")
    headings = mixing_pack.required_report_headings()
    if headings and md:
        missing = missing_report_headings(md, headings)
        assert missing == [], f"missing headings after repair: {missing}"

    for opt in result.get("mixing_options") or []:
        if isinstance(opt, dict) and opt.get("fit"):
            assert str(opt["fit"]).lower() in {
                "best",
                "strong",
                "conditional",
                "limited",
                "add-on",
                "special-case",
                "acceptable",
                "poor",
            }
