from __future__ import annotations

import re
from typing import List, Sequence, Tuple


def missing_report_headings(markdown: str, required: Sequence[str]) -> List[str]:
    """Return required heading strings not found (case-insensitive) in markdown."""
    text = (markdown or "").lower()
    missing: List[str] = []
    for heading in required:
        h = str(heading or "").strip()
        if not h:
            continue
        if h.lower() not in text:
            missing.append(h)
    return missing


def _heading_match(text: str, heading: str) -> Tuple[int, int] | None:
    """Return (start, end) of the heading occurrence, preferring a markdown title line."""
    h = heading.strip()
    if not h:
        return None
    pattern = re.compile(r"(?im)^(#{1,3})\s+.*" + re.escape(h) + r".*$")
    md = pattern.search(text)
    if md:
        return md.start(), md.end()
    idx = text.lower().find(h.lower())
    if idx < 0:
        return None
    return idx, idx + len(h)


def thin_report_sections(
    markdown: str,
    required: Sequence[str],
    *,
    min_chars: int = 120,
) -> List[str]:
    """Return required headings whose body text is thinner than min_chars.

    Body runs until the next markdown heading of the same or higher level
    (so ``##`` subsections under ``# Option evaluation`` count toward depth).
    """
    text = markdown or ""
    if not text.strip():
        return [str(h).strip() for h in required if str(h).strip()]

    thin: List[str] = []
    for heading in required:
        h = str(heading or "").strip()
        if not h:
            continue
        match = _heading_match(text, h)
        if match is None:
            thin.append(h)
            continue
        start, end = match
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", end)
        line = text[line_start : line_end if line_end >= 0 else len(text)]
        level_m = re.match(r"^(#{1,3})\s+", line)
        level = len(level_m.group(1)) if level_m else 1

        body = text[end:]
        nl = body.find("\n")
        body = body[nl + 1 :] if nl >= 0 else body

        next_h = re.search(rf"(?m)^#{{{1},{level}}}\s+\S", body)
        if next_h:
            body = body[: next_h.start()]
        body_len = len(" ".join(body.split()))
        if body_len < min_chars:
            thin.append(h)
    return thin
