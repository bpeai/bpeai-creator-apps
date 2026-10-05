# Evidence-based EI presentation visuals

SDK release: 0.2.10. Applies to `equipment_evaluator`, `equipment_sizing`, and
the existing generated apps that use their PPTX renderer.

The title panel uses a reviewed vendor photograph, vendor drawing, or project
drawing only when its scope matches the result. Otherwise it shows an editable
engineering summary from the evaluation/sizing fields. Inferred equipment
sketches and AI-generated equipment images are disabled. A slide LLM cannot
approve an image or supply a path that bypasses the catalog.

## Local and website use

Keep the catalog and its PNG/JPEG assets inside the app's private knowledge pack:

```text
py/apps/equipment_evaluator/<app_id>/agent.py
py/knowledge/equipment_evaluator/<app_id>/
  pack.yaml
  references/visuals/
    catalog.json
    manufacturer-model.png
```

The same arrangement applies to `equipment_sizing`. Paths inside the catalog
are relative to the **knowledge pack**, never to the device's working directory.

- Local Python loads `references/visuals/catalog.json` and reads the image bytes.
- The bundle uploader includes PNG/JPEG files under `references/visuals/`.
- Website ingestion checks image signatures, size, path and SHA-256, then stores
  the catalog and base64 bytes in private pack `content.visual_assets`. This
  travels through the existing Postgres content version and private S3 snapshot.
  No new public image bucket or database schema is required.
- Both the internal runtime API and direct DB fallback carry this content to
  Python. The website does not need a local copy of the knowledge folder.
- JSON download includes the catalog in `files` and image bytes in `binary_files`.
  The updated `download_knowledge_pack.py` restores both. ZIP download restores
  the same ordinary catalog/image files. Use the updated CLI for JSON downloads.
- PPTX embeds the image. Its source, applicability, reviewer and checksum are
  retained in slide notes and `artifacts.visual_evidence`; image bytes are not
  echoed into the result. Offline runs work without reaching the vendor website.

Limits: 50 catalog entries, 5 MB per image, 15 MB total image bytes per pack,
1 MB catalog JSON, 20 million decoded pixels per image at rendering time.
The existing bundle upload limit remains 25 MB. PNG/JPEG only; export a relevant
PDF/CAD drawing view to one of these formats and cite its document/page/revision.

## Authoring and review

An SME supplies and reviews the actual vendor/project asset. Do not bootstrap
visual approval using an LLM. The following is an example of the JSON shape,
with **draft** status; it is not an approved asset:

```json
{
  "schema_version": "ei_visual_assets_v1",
  "assets": [{
    "id": "transfer-pump-family",
    "path": "references/visuals/manufacturer-model.png",
    "kind": "vendor_photo",
    "scope": "product_family",
    "manufacturer": "Actual manufacturer",
    "model": "Actual product family",
    "match": {
      "equipment_name": "Transfer pump",
      "selected_model": "Centrifugal pump"
    },
    "source_url": "https://manufacturer.example/product",
    "source_document": "Catalog title",
    "page": "12",
    "revision": "Catalog revision",
    "applicability": "Describe exactly what this image demonstrates for this recommendation.",
    "attribution": "Manufacturer / document attribution",
    "reuse_basis": "Record the applicable permission or reuse basis",
    "sha256": "SHA-256 of the reviewed image file",
    "review_status": "draft",
    "reviewed_by": "",
    "reviewed_at": ""
  }]
}
```

Get the checksum with `Get-FileHash -Algorithm SHA256 -LiteralPath <image>` or
Python `hashlib.sha256(Path(image).read_bytes()).hexdigest()`. Upper/lowercase
checksum strings are accepted. After checking the source, image, scope, match
criteria and reuse basis, the SME records `review_status: "approved"`, their
name, and an ISO review date such as `2026-10-05`. Changing the image invalidates
the stored checksum and requires a new review. An approved declaration records
the SME's review; it is not independent engineering certification by the SDK.

`match` requires at least one of `equipment_name`, `equipment_item_name`, or
`system_name`, and at least one of `selected_model`, `recommended_basis`,
`equipment_type`, or `sized_item`. `dir_code` may further restrict applicability.
Every supplied match must equal the corresponding result field, ignoring only
case and repeated whitespace. Unknown fields, missing values and keyword-only
matches are rejected. Separate entries can cover explicitly reviewed cases.

Scopes, in preference order:

1. `project_configuration`: a reviewed project-specific drawing. Include a
   `dir_code` match and `result_sha256`, obtained using
   `bpeai_creator_sdk.artifacts.hero_image.engineering_basis_sha256(result)` on
   the actual evaluation/sizing JSON. Changes to equipment identity, duty,
   dimensions, connections, assumptions or other included basis fields disable
   the drawing until it is reviewed again.
2. `exact_model`: a model reference. `match.selected_model` must equal `model`
   and the result's `selected_model`. This does not confirm the project-specific
   configuration. Generic technology recommendations cannot use this scope.
3. `product_family`: a real family-level example for the recommended technology.
   The slide explicitly states **Product-family example** and **Configuration is
   not confirmed**. Do not claim exact dimensions, internals or accessories.

Kinds are `vendor_photo`, `vendor_drawing`, and `project_drawing`. Vendor assets
require manufacturer/model metadata. All require provenance, attribution,
applicability, reuse basis and review metadata. No external image search or
automatic downloading is performed. Unavailable, corrupt, oversized, mismatched,
unreviewed or stale assets fall back to the engineering summary during rendering.
Invalid uploads fail with a specific error rather than silently dropping assets.

The summary shows supported recommendation/criteria/limitations for evaluators,
or capacity/basis/dimensions/connections/open items for sizing. Unknown physical
values are omitted. Full selected summary text is retained in speaker notes when
the visible panel must shorten long text. Source drawings retain their aspect
ratio and are neither cropped nor annotated with inferred component callouts.

## Release and existing apps

Author SDK/templates/tools here and mirror the shared files into `bpeai`.
Deploy the matching `bpeai` web and Python runtime before uploading updated
agents, since they pass the new optional `knowledge_pack` renderer argument.
The handshake, output schema versions, run phases and existing UI stay intact.

Both templates and these local, gitignored app copies were updated:

- Evaluators: `pump_selector`, `tff_system`, `vent_collection`, `vent_filter`,
  `vessel_mixing`.
- Sizing: `chrom_column`, `heat_exchanger`, `vessel_agitator`.

Existing published agents importing the shared helper stop generating inferred
sketches after the SDK deploy; they use the summary until their updated app code
is uploaded. Legacy `hero_image_path`, `hero_image_prompt` and `hero_callouts`
cannot activate an image. Custom applications using a separate renderer require
their own audit. Previously exported decks must be regenerated.

Use the normal Upload → Test → Submit → Publish workflow. Download the current
cloud pack before editing/uploading pack content; do not overwrite newer DIR
menus with a stale local pack. For the eight updated apps without new visual
assets, an **app-only** bundle is sufficient and preserves cloud knowledge packs.
When adding reviewed images, upload the app's current matching knowledge folder.
Keep generated apps/packs and artifact ZIPs out of Git, per the existing design.

## Validation

`test_visual_evidence.py` covers local/filesystem and DB hydration parity,
template `phase=pptx` execution in both modes, legacy/LLM bypass attempts, wrong
identity/model, missing/corrupt/stale assets, project-basis changes, image aspect
ratio, source notes, unknown-value omission and CLI binary packaging.
`eiVisualAssets.node.test.ts` covers upload/storage/download/reupload, unchanged
review metadata, missing/corrupt/oversized assets and portable path validation.

Rendered title-slide checks use PowerPoint for evaluator and sizing summaries
and a clearly marked synthetic image fixture; the fixture is never distributed
as a vendor asset. Production vendor assets still require SME review.
