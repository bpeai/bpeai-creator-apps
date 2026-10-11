# Opaque App ID cutover — wipe notes

After switching to platform-assigned opaque EI App IDs, the eight demo creator apps were removed from git (`bpeai-creator-apps` leaf folders under `equipment_evaluator` / `equipment_sizing` and matching knowledge packs).

## Also wipe outside git (ops)

If these still exist in a deployed environment, delete:

- Postgres `creator_apps` rows for the old demo ids/slugs (`pump_selector`, `tff_system`, `vent_collection`, `vent_filter`, `vessel_mixing`, `chrom_column`, `heat_exchanger`, `vessel_agitator` and kebab slugs)
- Private `knowledge_packs` bound to those apps
- S3 keys `creators/*/apps/<id>/bundle.zip` for those ids
- Hot cache folders under `creator_runtime/apps/**/<id>/`

## Keep

- First-party Mixing Systems Expert (`agitator_duty_impeller_matcher` / `mixing-agitator-matcher`)
- Platform packs `mixing`, `filtration`
- Templates under `py/apps/_templates/` and knowledge `_examples/` / `_templates/`
