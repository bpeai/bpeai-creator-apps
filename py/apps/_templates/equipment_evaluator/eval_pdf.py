"""Evaluation report PDF — same role as vessel_agitator/urs_pdf.py.

The evaluate LLM still writes ``datasheet_markdown``. Fonts, navy tables,
recommendation callout, and header/footer live in the SDK writer. Copy this
file into a first-party app if you need a local override.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from bpeai_creator_sdk.artifacts.pdf_eval import (
    build_evaluation_pdf,
    write_evaluation_report_pdf,
)

__all__ = ["build_evaluation_pdf", "write_evaluation_report_pdf"]


def write_pdf(result: Mapping[str, Any], output_path: Path | str, **kwargs: Any) -> Path:
    return write_evaluation_report_pdf(result, output_path, **kwargs)
