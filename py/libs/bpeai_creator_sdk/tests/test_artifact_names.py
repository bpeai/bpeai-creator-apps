from __future__ import annotations

from types import SimpleNamespace

from bpeai_creator_sdk.artifacts.names import (
    attach_evaluation_artifact_name,
    attach_sizing_artifact_name,
    evaluation_artifact_stem,
    infer_evaluated_item,
    infer_evaluated_item_from_pack_id,
    infer_sized_item_from_pack_id,
    sizing_artifact_stem,
)


def test_pack_evaluated_item_wins_over_identity_and_pack_id():
    pack = SimpleNamespace(
        pack_id="pump_selector",
        evaluated_item="pump",
        artifact_filename_pattern="",
        meta={"evaluated_item": "pump"},
    )
    item = infer_evaluated_item(
        pack=pack,
        result={
            "system_name": "Chromatography Skid",
            "equipment_item_name": "Feed pump P-201",
        },
    )
    assert item == "pump"
    assert (
        evaluation_artifact_stem(
            {"system_name": "Chromatography Skid"},
            pack=pack,
        )
        == "Chromatography_Skid_pump_evaluation"
    )


def test_identity_item_used_when_pack_has_no_noun():
    assert (
        infer_evaluated_item(
            result={
                "system_name": "Chromatography Skid",
                "equipment_item_name": "Pump",
            }
        )
        == "Pump"
    )


def test_pack_id_selector_suffix_is_draft_fallback():
    assert infer_evaluated_item_from_pack_id("pump_selector") == "pump"
    assert infer_evaluated_item_from_pack_id("vent_filter_expert") == "vent_filter"
    assert infer_evaluated_item_from_pack_id("demo_pack") == ""
    assert infer_evaluated_item_from_pack_id("equipment_evaluator") == ""


def test_does_not_duplicate_item_already_in_system_name():
    stem = evaluation_artifact_stem(
        {"system_name": "Chromatography Skid Pump", "evaluated_item": "pump"},
        item="pump",
    )
    assert stem == "Chromatography_Skid_Pump_evaluation"


def test_custom_filename_pattern():
    pack = SimpleNamespace(
        pack_id="pump_selector",
        evaluated_item="pump",
        artifact_filename_pattern="{system}_{item}_tech_eval",
        meta={},
    )
    assert (
        evaluation_artifact_stem({"system_name": "Chromatography Skid"}, pack=pack)
        == "Chromatography_Skid_pump_tech_eval"
    )


def test_sizing_stem_uses_spaces_and_sized_item():
    pack = SimpleNamespace(
        pack_id="vessel_agitator",
        sized_item="agitator",
        evaluated_item="",
        artifact_filename_pattern="",
        meta={"sized_item": "agitator"},
    )
    stem = sizing_artifact_stem(
        {"system_name": "Buffer Preparation"},
        pack=pack,
    )
    assert stem == "Buffer Preparation Agitator Sizing"
    result = {"system_name": "Buffer Preparation"}
    attach_sizing_artifact_name(result, pack=pack)
    assert result["sized_item"] == "agitator"
    assert result["artifact_stem"] == "Buffer Preparation Agitator Sizing"


def test_sized_item_inferred_from_vessel_agitator_pack_id():
    assert infer_sized_item_from_pack_id("vessel_agitator") == "agitator"
    assert infer_sized_item_from_pack_id("mixing_sizing_stub") == ""


def test_attach_stamps_result_fields():
    pack = SimpleNamespace(
        pack_id="pump_selector",
        evaluated_item="pump",
        artifact_filename_pattern="",
        meta={"evaluated_item": "pump"},
    )
    result = {"system_name": "Chromatography Skid"}
    attach_evaluation_artifact_name(result, pack=pack)
    assert result["evaluated_item"] == "pump"
    assert result["artifact_stem"] == "Chromatography_Skid_pump_evaluation"
