"""Artifact helpers for creator apps (PPTX / DOCX evaluation deliverables)."""

from .hero_image import attach_title_hero_image, render_title_hero
from .names import (
    attach_evaluation_artifact_name,
    attach_sizing_artifact_name,
    deliverable_title_lines,
    evaluation_artifact_stem,
    evaluation_display_title,
    infer_evaluated_item,
    sizing_artifact_stem,
    sizing_display_title,
    sizing_title_lines,
)
from .docx_eval import (
    build_evaluation_docx,
    evaluation_docx_text,
    write_evaluation_report_docx,
)
from .docx_sizing import build_sizing_docx, sizing_docx_text, write_sizing_report_docx
from .xlsx_sizing import build_sizing_xlsx, parse_markdown_table
from .pptx_eval import build_evaluation_pptx, build_slide_pack_from_evaluation
from .reference_decks import (
    list_reference_decks,
    replace_reference_deck,
    resolve_reference_deck,
)

__all__ = [
    "attach_evaluation_artifact_name",
    "attach_sizing_artifact_name",
    "attach_title_hero_image",
    "deliverable_title_lines",
    "evaluation_artifact_stem",
    "evaluation_display_title",
    "infer_evaluated_item",
    "sizing_artifact_stem",
    "sizing_display_title",
    "sizing_title_lines",
    "build_evaluation_docx",
    "evaluation_docx_text",
    "write_evaluation_report_docx",
    "build_sizing_docx",
    "sizing_docx_text",
    "write_sizing_report_docx",
    "build_sizing_xlsx",
    "parse_markdown_table",
    "build_evaluation_pptx",
    "build_slide_pack_from_evaluation",
    "list_reference_decks",
    "render_title_hero",
    "replace_reference_deck",
    "resolve_reference_deck",
]
