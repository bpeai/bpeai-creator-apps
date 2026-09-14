"""Artifact helpers for creator apps (PPTX / PDF evaluation deliverables)."""

from .hero_image import attach_title_hero_image, render_title_hero
from .names import (
    attach_evaluation_artifact_name,
    evaluation_artifact_stem,
    infer_evaluated_item,
)
from .pdf_eval import build_evaluation_pdf, write_evaluation_report_pdf
from .pptx_eval import build_evaluation_pptx, build_slide_pack_from_evaluation
from .reference_decks import (
    list_reference_decks,
    replace_reference_deck,
    resolve_reference_deck,
)

__all__ = [
    "attach_evaluation_artifact_name",
    "attach_title_hero_image",
    "evaluation_artifact_stem",
    "infer_evaluated_item",
    "build_evaluation_pdf",
    "write_evaluation_report_pdf",
    "build_evaluation_pptx",
    "build_slide_pack_from_evaluation",
    "list_reference_decks",
    "render_title_hero",
    "replace_reference_deck",
    "resolve_reference_deck",
]
