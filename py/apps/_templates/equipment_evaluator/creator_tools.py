"""Optional creator helpers for equipment_evaluator apps.

Copy this file with the template. Non-coders can ignore it — pack YAML
(``prompt_fragments.yaml``, outlines, options) is the primary dial.

HANDSHAKE: helpers must stay inside existing run phases (dir / evaluate / pptx /
generate_dir) and known result shapes (dir_requirements JSON or
equipment_selector_v1). They may call ``agent.status(...)`` (SSE ``status``).
They must NOT invent new SSE event names or assume custom hub UI buttons.

See ``EXTENSIONS.md`` and ``docs/EI_CREATOR_EXTENSIONS.md``.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, MutableMapping


def research_context_note(system_name: str, application: str) -> str:
    """Build a short note you can append to a user prompt (evaluate / DIR).

    HANDSHAKE: prompt text only — does not emit SSE or change result schema.
    """
    name = (system_name or "equipment").strip()
    app = (application or "biopharmaceutical").strip()
    return (
        f"Creator research focus: prioritize industrial references for {name} "
        f"in a {app} context; cite title + URL when used."
    )


def postprocess_evaluation_result(
    result: MutableMapping[str, Any],
    *,
    extra_warning: str = "",
) -> Dict[str, Any]:
    """Light post-process after ``validate_output`` / model_dump.

    HANDSHAKE: may add ``sme_warnings`` entries; must keep ``phase`` =
    ``evaluation`` and ``equipment_selector_v1`` fields intact. Prefer
    ``evaluation_options`` over the ``mixing_options`` alias when reading.
    """
    out = dict(result)
    if extra_warning.strip():
        warnings = list(out.get("sme_warnings") or [])
        if not isinstance(warnings, list):
            warnings = []
        warnings.append(extra_warning.strip())
        out["sme_warnings"] = warnings
    return out


def merge_status_prefix(message: str, *, app_label: str = "") -> str:
    """Format a status line for ``self.status(...)``.

    HANDSHAKE: ``self.status(text)`` → SSE event ``status`` (string payload).
    """
    label = (app_label or "").strip()
    msg = (message or "").strip()
    if label:
        return f"[{label}] {msg}"
    return msg


def optional_dir_enrichment(
    dir_payload: Mapping[str, Any],
    *,
    note: str = "",
) -> Dict[str, Any]:
    """Optionally annotate a DIR questionnaire payload before return.

    HANDSHAKE: return must keep ``phase`` = ``dir_requirements`` and the
    fields the generic UI reads (``requirements``, ``common_codes``,
    ``message``, etc.). Extra keys are additive only.
    """
    out = dict(dir_payload)
    if note.strip():
        existing = str(out.get("message") or "").rstrip()
        out["message"] = f"{existing}\n\n{note.strip()}" if existing else note.strip()
    return out


# Example wiring (do not enable by default — copy into your agent when needed):
#
#   from .creator_tools import (
#       merge_status_prefix,
#       postprocess_evaluation_result,
#       research_context_note,
#   )
#
#   self.status(merge_status_prefix("Starting evaluation…", app_label=self.app_id))
#   # … after validate_output / model_dump …
#   result = postprocess_evaluation_result(result, extra_warning="Creator note: review CIP assumptions.")
