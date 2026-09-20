from __future__ import annotations

from types import SimpleNamespace

from bpeai_creator_sdk.artifacts.names import (
    attach_evaluation_artifact_name,
    attach_sizing_artifact_name,
    evaluation_artifact_stem,
    evaluation_display_title,
    infer_evaluated_item,
    infer_evaluated_item_from_pack_id,
    infer_sized_item_from_pack_id,
    sizing_artifact_stem,
    sizing_display_title,
    sizing_title_lines,
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
        == "Chromatography Skid Pump Evaluation"
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
    assert infer_evaluated_item_from_pack_id("pump-selector") == "pump"
    assert infer_evaluated_item_from_pack_id("vent_filter_expert") == "vent_filter"
    assert infer_evaluated_item_from_pack_id("demo_pack") == ""
    assert infer_evaluated_item_from_pack_id("equipment_evaluator") == ""
    assert infer_evaluated_item_from_pack_id("equipment_evaluator_stub") == ""
    assert infer_evaluated_item_from_pack_id("equipment_evaluator/pump_selector") == "pump"


def test_does_not_duplicate_item_already_in_system_name():
    stem = evaluation_artifact_stem(
        {"system_name": "Chromatography Skid Pump", "evaluated_item": "pump"},
        item="pump",
    )
    assert stem == "Chromatography Skid Pump Evaluation"
    assert (
        evaluation_artifact_stem(
            {"system_name": "CIP Return Pump"},
            pack_id="pump_selector",
        )
        == "CIP Return Pump Evaluation"
    )


def test_app_id_supplies_pump_when_pack_field_and_identity_are_missing():
    stem = evaluation_artifact_stem(
        {
            "system_name": "Chromatography Skid",
            "equipment_item_name": "Chromatography Skid",
            "creator_attribution": {"app_id": "pump_selector"},
        }
    )
    assert stem == "Chromatography Skid Pump Evaluation"


def test_identity_instance_name_does_not_override_selector_app_id():
    item = infer_evaluated_item(
        pack_id="pump_selector",
        result={
            "system_name": "Chromatography Skid",
            "equipment_item_name": "Feed pump P-201",
        },
    )
    assert item == "pump"
    assert (
        evaluation_artifact_stem(
            {
                "system_name": "Chromatography Skid",
                "equipment_name": "Chromatography Skid — Quattroflow 1200",
            },
            pack_id="pump_selector",
        )
        == "Chromatography Skid Pump Evaluation"
    )


def test_custom_filename_pattern():
    pack = SimpleNamespace(
        pack_id="pump_selector",
        evaluated_item="pump",
        artifact_filename_pattern="{system}_{item}_tech_eval",
        meta={},
    )
    assert (
        evaluation_artifact_stem({"system_name": "Chromatography Skid"}, pack=pack)
        == "Chromatography Skid Pump tech eval"
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


def test_sizing_display_title_uses_sizing_not_evaluation():
    result = {
        "schema_version": "equipment_sizing_v1",
        "template_family": "equipment_sizing",
        "system_name": "Buffer Preparation Vessel",
        "sized_item": "agitator",
        "knowledge_pack": "vessel_agitator",
        "creator_attribution": {"app_id": "vessel_agitator"},
    }
    attach_sizing_artifact_name(result)
    assert sizing_display_title(result) == "Buffer Preparation Vessel Agitator Sizing"
    assert sizing_title_lines(result) == [
        "Buffer Preparation Vessel Agitator",
        "Sizing",
    ]
    assert "Evaluation" not in sizing_display_title(result)


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
    assert result["artifact_stem"] == "Chromatography Skid Pump Evaluation"


def test_cip_system_title_includes_pump():
    pack = SimpleNamespace(
        pack_id="pump_selector",
        evaluated_item="pump",
        artifact_filename_pattern="",
        meta={"evaluated_item": "pump"},
    )
    result = {"system_name": "CIP system"}
    assert evaluation_display_title(result, pack=pack) == "CIP System Pump Evaluation"
    assert evaluation_artifact_stem(result, pack=pack) == "CIP System Pump Evaluation"
    attach_evaluation_artifact_name(result, pack=pack)
    assert result["artifact_stem"] == "CIP System Pump Evaluation"


def test_typed_system_name_wins_over_llm_equipment_system_name():
    pack = SimpleNamespace(
        pack_id="pump_selector",
        evaluated_item="pump",
        artifact_filename_pattern="{system} {item} {family}",
        meta={"evaluated_item": "pump"},
    )
    result = {
        "system_name": "CIP Return Pump",
        "equipment_system_name": "CIP Pump",
        "evaluated_item": "pump",
    }
    assert evaluation_display_title(result, pack=pack) == "CIP Return Pump Evaluation"
    assert evaluation_artifact_stem(result, pack=pack) == "CIP Return Pump Evaluation"


def test_artifact_placeholder_in_filename_pattern():
    pack = SimpleNamespace(
        pack_id="pump_selector",
        evaluated_item="pump",
        artifact_filename_pattern="{system} {item} {artifact}",
        meta={"evaluated_item": "pump"},
    )
    assert (
        evaluation_artifact_stem({"system_name": "CIP Return Pump"}, pack=pack)
        == "CIP Return Pump Evaluation"
    )
