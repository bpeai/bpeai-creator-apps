from __future__ import annotations

from pathlib import Path

import pytest

from bpeai_creator_sdk.local_format import format_dir_text, format_result_text
from bpeai_creator_sdk.local_parse import parse_inputs_heuristic
from bpeai_creator_sdk.local_run import is_selector_result, repo_py_root
from bpeai_creator_sdk.sme import (
    append_dir_menu,
    filter_numeric_common_codes,
    is_numeric_dir_code,
    list_missing_pack_files,
    load_knowledge_pack,
    match_dir_menu,
    normalize_bootstrapped_component,
    normalize_generated_menu,
    pack_is_loadable,
    prepare_bootstrapped_component,
    resolve_dir_menu,
    resolve_scenario_id,
    stamp_draft_meta,
    validate_dir_code,
    write_dir_catalog_markdown,
    write_pack_file,
)


@pytest.fixture(scope="module")
def py_root() -> Path:
    # tests/ → bpeai_creator_sdk/ → libs/ → py/
    return Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def examples_root(py_root: Path) -> Path:
    return py_root / "knowledge" / "_examples"


@pytest.fixture(scope="module")
def mixing_stub(py_root: Path, examples_root: Path):
    return load_knowledge_pack("mixing_stub", py_root=py_root, pack_root=examples_root)


def test_repo_has_example_stub_not_production_packs(py_root: Path):
    root = repo_py_root(py_root)
    assert (root / "knowledge" / "_examples" / "mixing_stub" / "pack.yaml").is_file()
    # Production platform seeds are not shipped here. Local creator draft packs
    # under py/knowledge/<id>/ (e.g. LLM-bootstrapped filtration) are allowed.


def test_committed_style_templates_preferred(py_root: Path, monkeypatch: pytest.MonkeyPatch):
    from bpeai_creator_sdk.sme import seed_template_references, template_references_root

    monkeypatch.delenv("BPEAI_TEMPLATE_REFERENCES_ROOT", raising=False)
    monkeypatch.delenv("BPEAI_REFERENCES_ROOT", raising=False)

    shared = template_references_root(py_root)
    assert shared is not None
    assert shared == (py_root / "knowledge" / "_templates" / "references").resolve()
    assert any(shared.glob("*.pptx"))
    assert any(shared.glob("*.pdf"))

    # Any filename in the shared folder seeds; names need not be standardized.
    dest_root = py_root / "knowledge" / "_test_seed_pack_tmp"
    if dest_root.exists():
        import shutil

        shutil.rmtree(dest_root)
    try:
        copied = seed_template_references("_test_seed_pack_tmp", py_root=py_root)
        assert any(p.endswith(".pptx") for p in copied)
        assert any(p.endswith(".pdf") for p in copied)
        assert all("/style/" in p.replace("\\", "/") for p in copied)
        assert (dest_root / "references" / "style").is_dir()
        assert list((dest_root / "references" / "style").glob("*.pptx"))
        assert list((dest_root / "references" / "style").glob("*.pdf"))
        # Second seed must not overwrite / re-copy.
        assert seed_template_references("_test_seed_pack_tmp", py_root=py_root) == []
    finally:
        import shutil

        if dest_root.exists():
            shutil.rmtree(dest_root)


def test_load_mixing_stub(mixing_stub):
    assert mixing_stub.pack_id == "mixing_stub"
    assert mixing_stub.equipment_system == "mixing"
    assert "media_preparation" in mixing_stub.scenarios
    assert mixing_stub.option_names()
    assert mixing_stub.fragment("role")
    assert mixing_stub.fragment("depth_requirements")
    system = mixing_stub.build_system_prompt()
    assert "depth" in system.lower() or "EXAMPLE" in system or "example" in system.lower()


def test_call_fragment_and_search_queries(mixing_stub):
    # calls: may be empty on stub until seed is updated; API must not throw
    assert mixing_stub.call_fragment("missing", "system", default="fallback") == "fallback"
    dir_qs = mixing_stub.build_search_queries(
        "dir_generate",
        system_name="Media prep vessel",
        application="biopharmaceutical",
    )
    assert dir_qs
    assert any("media prep" in q.lower() or "media_prep" in q.lower() or "design" in q.lower() for q in dir_qs)
    eval_qs = mixing_stub.build_search_queries(
        "evaluate",
        system_name="Media prep vessel",
        application="biopharmaceutical",
        decoded=[
            {"label": "Working volume", "option_text": "500–1,000 L"},
            {"label": "Vessel format", "option_text": "stainless CIP/SIP"},
        ],
    )
    assert eval_qs
    assert any("500" in q or "media prep" in q.lower() for q in eval_qs)


def test_search_queries_fallback_without_file():
    from bpeai_creator_sdk.sme.pack_loader import KnowledgePack
    from pathlib import Path

    pack = KnowledgePack(
        pack_id="empty",
        path=Path("<empty>"),
        meta={"equipment_system": "filtration"},
        dir_requirements={},
        equipment_options={},
        validation_rules={},
    )
    qs = pack.build_search_queries(
        "evaluate",
        system_name="Vent filter",
        application="biopharma",
    )
    assert qs
    assert all("Lightnin" not in q for q in qs)


def test_pack_bootstrap_inventory(py_root: Path, examples_root: Path, tmp_path: Path):
    assert pack_is_loadable("mixing_stub", py_root=py_root, pack_root=examples_root)
    assert (
        list_missing_pack_files(
            "mixing_stub",
            py_root=py_root,
            pack_root=examples_root,
            include_optional=False,
        )
        == []
    )
    path = write_pack_file(
        "demo_pack",
        "pack.yaml",
        stamp_draft_meta(
            {"label": "Demo"},
            pack_id="demo_pack",
            equipment_system="demo",
        ),
        py_root=tmp_path,
        draft=True,
    )
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "draft_pending_sme_approval" in text or "DRAFT" in text
    missing = list_missing_pack_files("demo_pack", py_root=tmp_path, include_optional=False)
    assert "dir_requirements.yaml" in missing
    assert not pack_is_loadable("demo_pack", py_root=tmp_path)


def test_normalize_bootstrapped_validation_rules_and_pack_unwrap():
    bad_rules = {
        "application": "vent_filter_expert",
        "dir_code": "validation_rules",
        "equipment_option_name": "vent_filter",
        "fit_enum": {"allowed": ["best", "strong"]},
    }
    fixed = prepare_bootstrapped_component(
        "validation_rules.yaml",
        bad_rules,
        pack_id="filtration",
        equipment_system="filtration",
    )
    assert isinstance(fixed["application"], dict)
    assert fixed["application"]["mode"] == "soft"
    assert fixed["equipment_system_field"]["must_equal"] == "filtration"

    nested_pack = {
        "pack.yaml": {
            "label": "Filtration draft",
            "industries": ["biopharmaceutical"],
            "default_scenario": "sterile_vent",
            "prompt_hooks": {"system_role": "expert", "emphasize": ["draft"]},
        },
        "dir_requirements.yaml": {"scenarios": {}},
        "pack_id": "filtration",
    }
    pack = normalize_bootstrapped_component(
        "pack.yaml", nested_pack, pack_id="filtration", equipment_system="filtration"
    )
    assert "pack.yaml" not in pack
    assert pack["approval_status"] == "draft_pending_sme_approval"
    assert isinstance(pack["prompt_hooks"], dict)


def test_bootstrap_dir_requirements_emits_dir_menus_only():
    dual = {
        "dir_menus": [
            {
                "menu_id": "demo__general__biopharmaceuticals",
                "scenario_id": "demo",
                "requirements": [
                    {"index": 1, "label": "Duty", "options": [{"index": 1, "text": "A"}]}
                ],
                "common_codes": ["1"],
            }
        ],
        "menus": [{"scenario_id": "demo", "label": "legacy index"}],
        "scenarios": {
            "demo": {
                "label": "legacy copy",
                "requirements": [
                    {"index": 1, "label": "Duty", "options": [{"index": 1, "text": "A"}]}
                ],
            }
        },
    }
    fixed = prepare_bootstrapped_component(
        "dir_requirements.yaml",
        dual,
        pack_id="demo",
        equipment_system="demo",
    )
    assert "dir_menus" in fixed
    assert "menus" not in fixed
    assert "scenarios" not in fixed
    assert fixed["dir_menus"][0]["scenario_id"] == "demo"
    assert fixed["dir_menus"][0]["common_codes"][0]["code"] == "1"


def test_bootstrap_dir_requirements_promotes_legacy_scenarios():
    legacy_only = {
        "scenarios": {
            "demo": {
                "label": "Legacy",
                "requirements": [
                    {"index": 1, "label": "Duty", "options": ["Low", "High"]}
                ],
            }
        }
    }
    fixed = prepare_bootstrapped_component(
        "dir_requirements.yaml",
        legacy_only,
        pack_id="demo",
        equipment_system="demo",
    )
    assert "scenarios" not in fixed
    assert fixed["dir_menus"][0]["scenario_id"] == "demo"
    assert fixed["dir_menus"][0]["requirements"][0]["options"][0]["text"] == "Low"


def test_write_pack_file_round_trips_colon_in_strings(tmp_path: Path):
    """PyYAML plain scalars with ': ' must not be written — they fail safe_load."""
    payload = {
        "fragments": {"role": "TFF SME"},
        "calls": {
            "evaluate": {
                "user_instructions": (
                    'Emit preliminary_specs as strings '
                    '(e.g. "Material: 316L stainless", "Cleaning: CIP/SIP capable"), '
                    "never {key, value} objects."
                )
            }
        },
    }
    path = write_pack_file(
        "colon_pack",
        "prompt_fragments.yaml",
        payload,
        py_root=tmp_path,
        draft=True,
    )
    import yaml

    reloaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert reloaded["calls"]["evaluate"]["user_instructions"] == payload["calls"]["evaluate"][
        "user_instructions"
    ]


def test_unwrap_filename_yaml_string_payload():
    from bpeai_creator_sdk.sme.pack_bootstrap import unwrap_component_payload

    inner = (
        "dir_generate:\n"
        "  templates:\n"
        '    - "{system_name} TFF DIR {application}"\n'
        "evaluate:\n"
        "  templates:\n"
        '    - "{system_name} TFF skid {application}"\n'
    )
    unwrapped = unwrap_component_payload(
        "search_queries.yaml",
        {"search_queries.yaml": inner},
    )
    assert "search_queries.yaml" not in unwrapped
    assert unwrapped["dir_generate"]["templates"][0].endswith("TFF DIR {application}")


def test_load_unwraps_filename_string_envelope(py_root: Path, mixing_stub, tmp_path: Path):
    import shutil

    from bpeai_creator_sdk.sme.pack_loader import unwrap_loaded_component

    dest = tmp_path / "mixing_stub"
    shutil.copytree(mixing_stub.path, dest)
    wrapped = (
        'search_queries.yaml: |\n'
        "  dir_generate:\n"
        "    templates:\n"
        '      - "{system_name} wrapped DIR {application}"\n'
        "  evaluate:\n"
        "    templates:\n"
        '      - "{system_name} wrapped eval {application}"\n'
    )
    (dest / "search_queries.yaml").write_text(wrapped, encoding="utf-8")
    pack = load_knowledge_pack("mixing_stub", pack_root=tmp_path)
    qs = pack.build_search_queries(
        "dir_generate",
        system_name="Media prep vessel",
        application="biopharmaceutical",
    )
    assert any("wrapped DIR" in q for q in qs)
    envelope = unwrap_loaded_component(
        "report_outline.yaml",
        {
            "report_outline.yaml": "required_headings:\n  - Design basis\n",
            "min_counts": {"sections": 1},
        },
    )
    assert envelope["required_headings"] == ["Design basis"]
    assert envelope["min_counts"]["sections"] == 1


def test_thin_report_sections():
    from bpeai_creator_sdk.sme import thin_report_sections

    headings = ["Design basis", "Option evaluation"]
    thin_md = "## Design basis\nShort.\n\n## Option evaluation\nAlso thin.\n"
    assert thin_report_sections(thin_md, headings, min_chars=120) == headings

    rich_md = (
        "## Design basis\n"
        + ("This selection implication explains volume, vessel format, solids handling, "
           "and why axial hydrofoil agitation is preferred for this DIR. " * 3)
        + "\n\n## Option evaluation\n"
        + ("Each option is compared on industrial applications, pros, cons, and vendors. " * 4)
    )
    assert thin_report_sections(rich_md, headings, min_chars=120) == []

    nested = (
        "# Option evaluation\n"
        "## Option 1\n"
        + ("Detailed industrial applications pros cons manufacturers and DIR fit. " * 5)
        + "\n# Do not specify\n"
        + ("Exclude high-shear options for this DIR. " * 3)
    )
    assert thin_report_sections(nested, ["Option evaluation"], min_chars=120) == []


def test_resolve_scenario_aliases(mixing_stub):
    assert resolve_scenario_id(mixing_stub, "Media Preparation Vessel") == "media_preparation"


def test_resolve_dir_menu_industry_variant(mixing_stub):
    menu = resolve_dir_menu(
        mixing_stub,
        system_name="Media Preparation Vessel",
        industry="Biopharmaceuticals",
        equipment_system_variant="general_mixing",
        require_approved=True,
    )
    assert menu.scenario_id == "media_preparation"
    assert menu.industry == "Biopharmaceuticals"
    assert menu.is_approved
    assert len(menu.requirements) == 3
    assert menu.source == "dir_catalog"
    assert menu.common_codes
    assert is_numeric_dir_code(str(menu.common_codes[0]["code"] if isinstance(menu.common_codes[0], dict) else menu.common_codes[0]), requirement_count=3)


def test_match_dir_menu_from_list_catalog(mixing_stub):
    hit = match_dir_menu(
        mixing_stub,
        system_name="Media Preparation Vessel",
        application="Biopharmaceuticals",
        allow_draft=True,
    )
    assert hit is not None
    assert hit.scenario_id == "media_preparation"
    assert hit.menu_id


def test_normalize_generated_menu_requires_numeric_common_codes():
    raw = {
        "label": "Demo",
        "summary": "Demo summary",
        "common_codes": [{"code": "SIP", "caption": "bad tag"}],
        "requirements": [
            {
                "index": 1,
                "label": "A",
                "options": [{"index": 1, "text": "a1"}, {"index": 2, "text": "a2"}],
            },
            {
                "index": 2,
                "label": "B",
                "options": [{"index": 1, "text": "b1"}, {"index": 2, "text": "b2"}],
            },
            {
                "index": 3,
                "label": "C",
                "options": [{"index": 1, "text": "c1"}, {"index": 2, "text": "c2"}],
            },
        ],
    }
    row = normalize_generated_menu(
        raw,
        system_name="Demo Vessel",
        application="biopharmaceutical",
        scenario_id="demo_dir",
        variant="general",
        industry="biopharmaceutical",
    )
    assert row["status"] == "draft_generated"
    assert len(row["common_codes"]) >= 2
    assert all(is_numeric_dir_code(c["code"], requirement_count=3) for c in row["common_codes"])
    assert filter_numeric_common_codes([{"code": "SIP"}], requirements=row["requirements"]) == []


def test_append_dir_menu_and_catalog_md(mixing_stub, tmp_path: Path):
    # Copy stub into temp pack path for write tests
    import shutil

    dest = tmp_path / "mixing_stub"
    shutil.copytree(mixing_stub.path, dest)
    pack = load_knowledge_pack("mixing_stub", pack_root=tmp_path)
    row = {
        "menu_id": "demo_dir__general__biopharmaceuticals",
        "status": "draft_generated",
        "scenario_id": "demo_dir",
        "equipment_system_variant": "general_mixing",
        "industry": "Biopharmaceuticals",
        "system_examples": ["Demo Vessel"],
        "label": "Demo DIR",
        "summary": "Appended draft for tests.",
        "generated_from": "runtime",
        "common_codes": [
            {"code": "1-1-1", "caption": "Baseline demo starter."},
            {"code": "2-1-2", "caption": "Alternate demo starter."},
        ],
        "requirements": pack.scenario("media_preparation")["requirements"],
    }
    append_dir_menu(pack, row, write_markdown=True)
    reloaded = load_knowledge_pack("mixing_stub", pack_root=tmp_path)
    assert any(m.get("menu_id") == row["menu_id"] for m in reloaded.dir_menus)
    md = write_dir_catalog_markdown(reloaded)
    assert md.is_file()
    text = md.read_text(encoding="utf-8")
    assert "demo_dir__general__biopharmaceuticals" in text
    assert "draft_generated" in text


def test_equipment_evaluator_generates_dir_on_catalog_miss(mixing_stub, tmp_path: Path, monkeypatch):
    """Template match-or-generate path with mocked Serper + LLM (no network)."""
    import shutil
    import sys

    py_root = Path(__file__).resolve().parents[3]
    if str(py_root) not in sys.path:
        sys.path.insert(0, str(py_root))

    from apps._templates.equipment_evaluator.agent import EquipmentEvaluatorAgent

    dest = tmp_path / "mixing_stub"
    shutil.copytree(mixing_stub.path, dest)
    pack = load_knowledge_pack("mixing_stub", pack_root=tmp_path)

    fake_dir = {
        "label": "Resin slurry mix DIR",
        "summary": "Draft DIR for chromatography resin slurry mixing.",
        "system_examples": ["Chromatography Resin Slurry Tank"],
        "common_codes": [
            {
                "code": "2-1-1-1-1",
                "caption": "Mid-scale stainless CIP/SIP slurry suspension, low shear, GMP.",
            },
            {
                "code": "3-1-2-1-2",
                "caption": "Large stainless vessel, gentle resuspension, moderate DP OK.",
            },
        ],
        "requirements": [
            {
                "index": 1,
                "label": "Working volume",
                "options": [
                    {"index": 1, "text": "50–250 L"},
                    {"index": 2, "text": "250–1,000 L"},
                    {"index": 3, "text": "> 1,000 L"},
                ],
            },
            {
                "index": 2,
                "label": "Vessel format",
                "options": [
                    {"index": 1, "text": "Stainless CIP/SIP"},
                    {"index": 2, "text": "Single-use"},
                ],
            },
            {
                "index": 3,
                "label": "Solids challenge",
                "options": [
                    {"index": 1, "text": "Resin slurry"},
                    {"index": 2, "text": "Low solids"},
                ],
            },
            {
                "index": 4,
                "label": "Shear sensitivity",
                "options": [
                    {"index": 1, "text": "Low shear required"},
                    {"index": 2, "text": "Moderate shear OK"},
                ],
            },
            {
                "index": 5,
                "label": "Documentation",
                "options": [
                    {"index": 1, "text": "GMP/aseptic"},
                    {"index": 2, "text": "GMP-lite"},
                ],
            },
        ],
    }

    agent = EquipmentEvaluatorAgent()
    monkeypatch.setattr(agent, "serper_search", lambda *a, **k: [])
    monkeypatch.setattr(agent, "call_openai_json", lambda **kwargs: fake_dir)
    monkeypatch.setattr(agent, "status", lambda *a, **k: None)

    # Unrelated system must not reuse media_preparation via default_scenario.
    assert (
        match_dir_menu(
            pack,
            system_name="Chromatography Resin Slurry Tank",
            application="biopharmaceutical",
            allow_draft=True,
        )
        is None
    )

    menu, notes = agent._resolve_or_generate_dir_menu(
        pack,
        system_name="Chromatography Resin Slurry Tank",
        application="biopharmaceutical",
        scenario_id=None,
        equipment_system_variant=None,
        industry=None,
        force_generate=False,
    )
    assert menu.lifecycle == "draft_generated"
    assert menu.source == "generated"
    assert menu.scenario_id == "chromatography_resin_slurry_tank"
    assert not str(menu.scenario_id).endswith("_dir")
    assert len(menu.requirements) >= 5
    assert any("Generated draft DIR" in n for n in notes)
    reloaded = load_knowledge_pack("mixing_stub", pack_root=tmp_path)
    assert any(
        str(m.get("status") or "") == "draft_generated" for m in reloaded.dir_menus
    )


def test_validate_dir_code_ok(mixing_stub):
    result = validate_dir_code(mixing_stub, "media_preparation", "2-1-2")
    assert result.ok
    assert len(result.decoded) == 3


def test_validate_dir_code_bad_length(mixing_stub):
    result = validate_dir_code(mixing_stub, "media_preparation", "2-1")
    assert not result.ok
    assert "Expected 3" in result.error
    assert result.suggested_correction


def test_validate_dir_code_out_of_range(mixing_stub):
    result = validate_dir_code(mixing_stub, "media_preparation", "9-1-2")
    assert not result.ok


def test_parse_dir_code_heuristic():
    parsed = parse_inputs_heuristic("2-1-2-3-1-1")
    assert parsed.get("dir_code") == "2-1-2-3-1-1"
    assert parsed.get("phase") == "evaluate"
    assert "system_name" not in parsed


def test_is_selector_result_skips_dir():
    assert not is_selector_result({"phase": "dir_requirements", "requirements": []})
    assert is_selector_result(
        {
            "schema_version": "equipment_selector_v1",
            "equipment_tag": "MX-101",
            "selected_model": "Hydrofoil",
            "rationale": "fit",
        }
    )


def test_format_dir_text():
    text = format_dir_text(
        {
            "phase": "dir_requirements",
            "system_name": "Media Prep",
            "application": "biopharmaceutical",
            "scenario_id": "hold_tank_vent_aseptic",
            "dir_menu_label": "Hold tank sterile vent",
            "equipment_system_variant": "hold_tank_vent",
            "industry": "biopharmaceutical",
            "requirements": [
                {
                    "index": 1,
                    "label": "Working volume",
                    "options": [{"index": 1, "text": "50–250 L"}],
                }
            ],
            "common_codes": ["2-1-2"],
            "message": "Reply with a DIR code.",
        }
    )
    assert "Design Input Requirements" in text
    assert "Working volume" in text
    assert "2-1-2" in text
    assert "hold_tank_vent_aseptic" in text
    assert "Hold tank sterile vent" in text
    assert "equipment options" in text
    assert format_result_text({"phase": "dir_requirements", "requirements": []}).startswith(
        "Design Input"
    )


def test_align_pack_to_app_renames_folder_and_rewrites_pointers(tmp_path: Path):
    from bpeai_creator_sdk.sme import align_pack_to_app

    app_id = "vent_filter_expert"
    app_dir = tmp_path / "apps" / app_id
    app_dir.mkdir(parents=True)
    (app_dir / "manifest.json").write_text(
        '{"id": "vent_filter_expert", "knowledge_pack": "filtration"}\n',
        encoding="utf-8",
    )
    (app_dir / "agent.py").write_text(
        'class Agent:\n    app_id = "vent_filter_expert"\n    knowledge_pack_id = "filtration"\n',
        encoding="utf-8",
    )
    old_pack = tmp_path / "knowledge" / "filtration"
    old_pack.mkdir(parents=True)
    (old_pack / "pack.yaml").write_text("pack_id: filtration\nequipment_system: filtration\n")

    result = align_pack_to_app(app_id, py_root=tmp_path, pack_id="filtration")
    assert result.pack_id == app_id
    assert not result.collision
    assert (tmp_path / "knowledge" / app_id / "pack.yaml").is_file()
    assert not (tmp_path / "knowledge" / "filtration").exists()
    meta = (tmp_path / "knowledge" / app_id / "pack.yaml").read_text(encoding="utf-8")
    assert "pack_id: vent_filter_expert" in meta
    manifest = (app_dir / "manifest.json").read_text(encoding="utf-8")
    assert '"knowledge_pack": "vent_filter_expert"' in manifest
    agent = (app_dir / "agent.py").read_text(encoding="utf-8")
    assert 'knowledge_pack_id = "vent_filter_expert"' in agent


def test_align_pack_to_app_collision_keeps_both_folders(tmp_path: Path):
    from bpeai_creator_sdk.sme import align_pack_to_app

    app_id = "heat_exchanger_evaluator"
    app_dir = tmp_path / "apps" / app_id
    app_dir.mkdir(parents=True)
    (app_dir / "manifest.json").write_text(
        '{"id": "heat_exchanger_evaluator", "knowledge_pack": "heat_transfer"}\n',
        encoding="utf-8",
    )
    dest = tmp_path / "knowledge" / app_id
    dest.mkdir(parents=True)
    (dest / "pack.yaml").write_text(f"pack_id: {app_id}\n")
    other = tmp_path / "knowledge" / "heat_transfer"
    other.mkdir(parents=True)
    (other / "pack.yaml").write_text("pack_id: heat_transfer\n")

    result = align_pack_to_app(app_id, py_root=tmp_path, pack_id="heat_transfer")
    assert result.collision
    assert result.pack_id == app_id
    assert dest.is_dir()
    assert other.is_dir()


def test_migrate_legacy_references_and_content_index(tmp_path: Path):
    from bpeai_creator_sdk.sme import (
        build_content_index,
        creator_content_prompt_block,
        knowledge_pack_from_dict,
        migrate_legacy_references,
        retrieve_creator_chunks,
        seed_template_references,
    )
    from bpeai_creator_sdk.sme.pack_bootstrap import pack_dir

    pack_id = "demo_content_pack"
    root = pack_dir(pack_id, py_root=tmp_path)
    ref = root / "references"
    ref.mkdir(parents=True)
    (ref / "style_deck.pptx").write_bytes(b"PK")
    (ref / "sme_notes.md").write_text(
        "Sterile vent filters for hold tanks require hydrophobic PTFE membranes "
        "and SIP-capable housings for biopharmaceutical buffer prep.",
        encoding="utf-8",
    )

    moved = migrate_legacy_references(pack_id, py_root=tmp_path)
    assert "references/style/style_deck.pptx" in moved
    assert "references/content/sme_notes.md" in moved
    assert (root / "references" / "style" / "style_deck.pptx").is_file()
    assert (root / "references" / "content" / "sme_notes.md").is_file()

    index = build_content_index(pack_id, py_root=tmp_path)
    assert index["chunks"]
    again = build_content_index(pack_id, py_root=tmp_path)
    assert again["files"][0]["sha256"] == index["files"][0]["sha256"]

    query = "sterile vent filter hold tank PTFE biopharmaceutical"
    hits = retrieve_creator_chunks(index, query)
    assert hits
    assert "PTFE" in hits[0]["text"] or "ptfe" in hits[0]["text"].lower()
    block = creator_content_prompt_block(index, [query])
    assert "Creator reference content" in block
    assert "supplemental SME" in block

    hydrated = knowledge_pack_from_dict(
        pack_id,
        {"meta": {"pack_id": pack_id}, "content": {"content_index": index}},
    )
    assert hydrated.content_index.get("chunks")


def test_seed_does_not_clobber_nested_style(tmp_path: Path, py_root: Path, monkeypatch: pytest.MonkeyPatch):
    from bpeai_creator_sdk.sme import seed_template_references, template_references_root

    monkeypatch.delenv("BPEAI_TEMPLATE_REFERENCES_ROOT", raising=False)
    monkeypatch.delenv("BPEAI_REFERENCES_ROOT", raising=False)
    shared = template_references_root(py_root)
    assert shared is not None
    copied = seed_template_references("_nested_seed_tmp", py_root=tmp_path, template_root=shared)
    dest = tmp_path / "knowledge" / "_nested_seed_tmp" / "references" / "style"
    assert copied
    assert dest.is_dir()
    assert list(dest.glob("*.pptx"))
    assert seed_template_references("_nested_seed_tmp", py_root=tmp_path, template_root=shared) == []
