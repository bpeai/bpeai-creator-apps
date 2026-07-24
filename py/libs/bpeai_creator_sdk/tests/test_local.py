from __future__ import annotations

import os
from pathlib import Path

from bpeai_creator_sdk.local_env import load_dotenv, openai_key_present
from bpeai_creator_sdk.local_format import format_selector_json, format_selector_text
from bpeai_creator_sdk.local_parse import (
    heuristics_look_thin,
    parse_free_text,
    parse_inputs_heuristic,
)


def test_format_selector_text_includes_core_fields():
    result = {
        "equipment_tag": "VF-101",
        "selected_model": "0.2 µm hydrophobic PTFE vent filter",
        "equipment_system": "filtration",
        "equipment_name": "Vent filter for Media Prep Vessel",
        "equipment_category": "Filtration",
        "key_specs": [
            {"key": "Application", "value": "biopharma", "unit": None},
            {"key": "System", "value": "Media Prep Vessel", "unit": None},
        ],
        "rationale": "Recommend sterilizing-grade vent filter.",
        "creator_attribution": {"display_name": "Test", "app_id": "vent_filter_expert"},
        "source_basis": ["rules v1"],
    }
    text = format_selector_text(result)
    assert "VF-101" in text
    assert "0.2 µm hydrophobic PTFE vent filter" in text
    assert "Application: biopharma" in text
    assert "Recommend sterilizing-grade vent filter." in text
    assert "vent_filter_expert" in text


def test_format_selector_json_is_pretty():
    raw = format_selector_json({"equipment_tag": "VF-101", "selected_model": "A"})
    assert '"equipment_tag": "VF-101"' in raw
    assert raw.endswith("\n")


def test_parse_inputs_heuristic_media_prep_biopharma():
    inputs = parse_inputs_heuristic("Media Prep Vessel, biopharma")
    assert inputs["system_name"] == "Media Prep Vessel"
    assert inputs["application"] == "biopharma"
    assert "raw_text" in inputs


def test_parse_inputs_heuristic_sterile_nitrogen():
    inputs = parse_inputs_heuristic("buffer tank sterile nitrogen vent")
    assert "Buffer" in inputs["system_name"] or "Tank" in inputs["system_name"]
    assert inputs["application"] == "sterile"
    assert inputs["fluid"] == "nitrogen"


def test_heuristics_look_thin_for_bare_phrase():
    thin = parse_inputs_heuristic("something vague")
    assert heuristics_look_thin(thin) is True
    rich = parse_inputs_heuristic("Media Prep Vessel, biopharma")
    assert heuristics_look_thin(rich) is False


def test_parse_free_text_without_openai_uses_heuristics(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    inputs = parse_free_text("Media Prep Vessel, biopharma")
    assert inputs["system_name"] == "Media Prep Vessel"
    assert inputs["application"] == "biopharma"


def test_load_dotenv_does_not_override(tmp_path: Path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=from-file\nCUSTOM_FLAG=yes\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "already-set")
    monkeypatch.delenv("CUSTOM_FLAG", raising=False)
    loaded = load_dotenv(env_file, override=False)
    assert loaded == env_file
    assert os.environ["OPENAI_API_KEY"] == "already-set"
    assert os.environ["CUSTOM_FLAG"] == "yes"
    assert openai_key_present() is True
