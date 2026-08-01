"""SME-readable DIR catalog: list menus, fingerprint match, append, markdown table."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence

import yaml

from .pack_loader import (
    DirMenu,
    KnowledgePack,
    _alias_match_text,
    _best_alias_match,
    _norm,
    resolve_industry,
    resolve_variant_id,
)
from .validate import is_numeric_dir_code, validate_dir_code

DRAFT_USABLE_STATUSES = frozenset(
    {
        "draft_generated",
        "generated",
        "pending_review",
        "approved",
        "APPROVED",
        "GENERATED",
        "PENDING_REVIEW",
    }
)
APPROVED_STATUSES = frozenset({"approved", "APPROVED"})
# Creator private packs often land as pending_review after portal upload — still usable for Test.
CREATOR_USABLE_DRAFT = frozenset(
    {"draft_generated", "generated", "pending_review", "GENERATED", "PENDING_REVIEW"}
)


def dir_menus(pack: KnowledgePack) -> List[Dict[str, Any]]:
    """Return list catalog rows (``dir_menus``) or empty if pack uses legacy shape only."""
    raw = pack.dir_requirements.get("dir_menus") or []
    if isinstance(raw, list):
        return [m for m in raw if isinstance(m, dict)]
    return []


def filter_numeric_common_codes(
    common_codes: Sequence[Any],
    *,
    requirements: Sequence[Mapping[str, Any]],
) -> List[Dict[str, str]]:
    """Keep only common codes that hard-validate against ``requirements``."""
    n = len(requirements) if isinstance(requirements, list) else 0
    out: List[Dict[str, str]] = []
    for item in common_codes or []:
        if isinstance(item, str):
            code, caption = item, ""
        elif isinstance(item, Mapping) and item.get("code"):
            code, caption = str(item["code"]), str(item.get("caption") or "")
        else:
            continue
        if not is_numeric_dir_code(code, requirement_count=n if n else None):
            continue
        # Soft structural check without pack when n known
        if n:
            parts = [int(p) for p in code.split("-")]
            ok = True
            for i, idx in enumerate(parts):
                req = requirements[i] if i < len(requirements) else {}
                opts = req.get("options") if isinstance(req, Mapping) else None
                max_idx = 0
                if isinstance(opts, list) and opts:
                    for opt in opts:
                        if isinstance(opt, Mapping) and "index" in opt:
                            try:
                                max_idx = max(max_idx, int(opt["index"]))
                            except (TypeError, ValueError):
                                continue
                    if not max_idx:
                        max_idx = len(opts)
                if max_idx and (idx < 1 or idx > max_idx):
                    ok = False
                    break
            if not ok:
                continue
        out.append({"code": code, "caption": caption})
    return out


def menu_id_for(
    *,
    scenario_id: str,
    variant: str,
    industry: str,
    system_name: str = "",
) -> str:
    base = f"{scenario_id}__{_slug(variant)}__{_slug(industry)}"
    extra = _slug(system_name)
    if extra and extra not in base:
        base = f"{base}__{extra}"
    return base[:120]


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").strip().lower()).strip("_")
    return s or "x"


def catalog_row_to_dir_menu(row: Mapping[str, Any]) -> DirMenu:
    status = str(row.get("status") or row.get("lifecycle") or "approved")
    return DirMenu(
        scenario_id=str(row.get("scenario_id") or "default"),
        equipment_system_variant=str(row.get("equipment_system_variant") or ""),
        industry=str(row.get("industry") or ""),
        label=str(row.get("label") or row.get("scenario_id") or "DIR menu"),
        lifecycle=status,
        requirements=[r for r in (row.get("requirements") or []) if isinstance(r, dict)],
        common_codes=list(row.get("common_codes") or [])
        if isinstance(row.get("common_codes"), list)
        else [],
        source="dir_catalog",
        menu_id=str(row.get("menu_id") or ""),
        summary=str(row.get("summary") or ""),
    )


def match_dir_menu(
    pack: KnowledgePack,
    *,
    system_name: str = "",
    scenario_id: str | None = None,
    equipment_system_variant: str | None = None,
    industry: str | None = None,
    application: str | None = None,
    allow_draft: bool = True,
) -> DirMenu | None:
    """Find best catalog row for the run fingerprint, or None if no usable match.

    Does **not** fall back to ``default_scenario`` alone — that would reuse an
    unrelated menu for unique systems. Match requires an explicit ``scenario_id``,
    a ``scenario_aliases`` hit, and/or a ``system_examples`` hit on a catalog row.
    """
    rows = dir_menus(pack)
    if not rows:
        return None

    text = _alias_match_text(system_name, application)
    explicit_sid = (scenario_id or "").strip()
    aliases = pack.meta.get("scenario_aliases") or {}
    alias_sid = _best_alias_match(
        aliases if isinstance(aliases, dict) else {},
        text,
        allowed_ids=set(pack.scenarios.keys()),
    )
    sid = explicit_sid or alias_sid or ""

    variant = resolve_variant_id(
        pack, system_name, equipment_system_variant, application=application
    )
    ind = resolve_industry(pack, industry=industry, application=application)

    scored: list[tuple[int, Dict[str, Any]]] = []
    for row in rows:
        status_raw = str(row.get("status") or row.get("lifecycle") or "approved")
        status = _norm(status_raw)
        if status in {_norm(s) for s in APPROVED_STATUSES}:
            status_ok = True
            status_bonus = 20
        elif allow_draft and status in {_norm(s) for s in CREATOR_USABLE_DRAFT}:
            status_ok = True
            status_bonus = 5
        else:
            status_ok = False
        if not status_ok:
            continue
        if not isinstance(row.get("requirements"), list) or not row.get("requirements"):
            continue

        score = status_bonus
        scenario_hit = bool(sid) and _norm(str(row.get("scenario_id") or "")) == _norm(sid)
        if scenario_hit:
            score += 100
        if _norm(str(row.get("equipment_system_variant") or "")) == _norm(variant):
            score += 40
        if _norm(str(row.get("industry") or "")) == _norm(ind):
            score += 40

        example_bonus = 0
        examples = row.get("system_examples") or []
        if isinstance(examples, list) and text:
            for ex in examples:
                t = str(ex).strip().lower()
                if not t:
                    continue
                # Full example appears in user text, or shared significant tokens (either direction).
                if t in text or text in t:
                    example_bonus = max(example_bonus, min(40, max(len(t), len(text))))
                    continue
                ex_tokens = {w for w in t.replace("/", " ").split() if len(w) >= 4}
                text_tokens = {w for w in text.replace("/", " ").split() if len(w) >= 4}
                overlap = ex_tokens & text_tokens
                if len(overlap) >= 2:
                    example_bonus = max(example_bonus, 12 + 4 * len(overlap))
        score += example_bonus

        # Accept: scenario fingerprint match, or strong system_examples evidence.
        if not scenario_hit and example_bonus < 12:
            continue
        scored.append((score, row))

    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    return catalog_row_to_dir_menu(scored[0][1])


def normalize_generated_menu(
    raw: Mapping[str, Any],
    *,
    system_name: str,
    application: str,
    scenario_id: str,
    variant: str,
    industry: str,
) -> Dict[str, Any]:
    """Normalize LLM output into a catalog row; raise ValueError if unusable."""
    requirements = raw.get("requirements") or []
    if not isinstance(requirements, list) or len(requirements) < 3:
        raise ValueError("Generated DIR must include at least 3 requirements.")

    norm_reqs: List[Dict[str, Any]] = []
    for i, req in enumerate(requirements):
        if not isinstance(req, Mapping):
            continue
        opts_in = req.get("options") or []
        opts: List[Dict[str, Any]] = []
        if isinstance(opts_in, list):
            for j, opt in enumerate(opts_in):
                if isinstance(opt, str):
                    opts.append({"index": j + 1, "text": opt})
                elif isinstance(opt, Mapping):
                    opts.append(
                        {
                            "index": int(opt.get("index") or j + 1),
                            "text": str(opt.get("text") or opt.get("label") or ""),
                        }
                    )
        if len(opts) < 2:
            continue
        norm_reqs.append(
            {
                "index": int(req.get("index") or i + 1),
                "label": str(req.get("label") or f"Requirement {i + 1}"),
                "options": opts,
            }
        )
    if len(norm_reqs) < 3:
        raise ValueError("Generated DIR requirements missing usable options.")

    codes = filter_numeric_common_codes(raw.get("common_codes") or [], requirements=norm_reqs)
    if len(codes) < 2:
        # Prefer varied, captioned starters — never emit all-1s / all-2s placeholders.
        n = len(norm_reqs)

        def _pick(indices: list[int], caption: str) -> Dict[str, Any]:
            parts = []
            for i, req in enumerate(norm_reqs):
                opts = req.get("options") or []
                max_i = len(opts) if opts else 1
                want = indices[i] if i < len(indices) else 1
                parts.append(str(min(max(1, want), max_i)))
            return {"code": "-".join(parts), "caption": caption}

        gmp = _pick(
            [3] * n,
            f"Large-scale GMP production bias for {system_name}: prefer stainless / SIP / FIT-capable choices where available.",
        )
        mid_c = _pick(
            [2] * n,
            f"Pilot/production reusable housing bias for {system_name} ({application}).",
        )
        su = _pick(
            [1] * n,
            f"Single-use / smaller-scale bias for {system_name} ({application}).",
        )
        for label, target_words in (
            (gmp, ("stainless", "316", "sip", "steam", "integrity", "fit", "gmp", "production", "large")),
            (mid_c, ("reusable", "cartridge", "housing", "moderate", "pilot")),
            (su, ("single-use", "disposable", "capsule", "gamma")),
        ):
            parts = label["code"].split("-")
            for i, req in enumerate(norm_reqs):
                opts = req.get("options") or []
                for opt in opts:
                    ot = str(opt.get("text") or "").lower()
                    if any(w in ot for w in target_words):
                        parts[i] = str(int(opt.get("index") or parts[i]))
                        break
            label["code"] = "-".join(parts)
        codes = []
        seen: set[str] = set()
        for c in (gmp, mid_c, su):
            if c["code"] in seen:
                continue
            seen.add(c["code"])
            codes.append(c)

    mid = str(raw.get("menu_id") or "").strip() or menu_id_for(
        scenario_id=scenario_id,
        variant=variant,
        industry=industry,
        system_name=system_name,
    )
    examples = raw.get("system_examples") or [system_name]
    if not isinstance(examples, list):
        examples = [system_name]
    examples = [str(x).strip() for x in examples if str(x).strip()]
    if system_name and system_name not in examples:
        examples.insert(0, system_name)

    return {
        "menu_id": mid,
        "status": "draft_generated",
        "scenario_id": scenario_id,
        "equipment_system_variant": variant,
        "industry": industry,
        "system_examples": examples[:8],
        "label": str(raw.get("label") or f"{system_name} DIR ({industry})"),
        "summary": str(raw.get("summary") or f"Draft DIR for {system_name} / {application}."),
        "generated_from": "runtime",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "common_codes": codes,
        "requirements": norm_reqs,
    }


def append_dir_menu(
    pack: KnowledgePack,
    row: Mapping[str, Any],
    *,
    write_markdown: bool = True,
) -> Path:
    """Append (or replace same menu_id) a catalog row and persist YAML (+ optional md)."""
    if not pack.path.exists() or str(pack.path).startswith("<"):
        raise FileNotFoundError(f"Pack path is not a filesystem directory: {pack.path}")

    path = pack.path / "dir_requirements.yaml"
    data: MutableMapping[str, Any]
    if path.is_file():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise TypeError("dir_requirements.yaml must be a mapping")
        data = loaded
    else:
        data = {"pack_id": pack.pack_id}

    menus = data.get("dir_menus")
    if not isinstance(menus, list):
        menus = []
        # Preserve legacy scenarios/menus if present
        data["dir_menus"] = menus

    mid = str(row.get("menu_id") or "")
    replaced = False
    for i, existing in enumerate(menus):
        if isinstance(existing, dict) and str(existing.get("menu_id") or "") == mid and mid:
            menus[i] = dict(row)
            replaced = True
            break
    if not replaced:
        menus.append(dict(row))
    data["dir_menus"] = menus

    # Keep in-memory pack in sync
    pack.dir_requirements = dict(data)

    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    if write_markdown:
        write_dir_catalog_markdown(pack)
    return path


def write_dir_catalog_markdown(pack: KnowledgePack) -> Path:
    """Write SME-readable ``dir_catalog.md`` beside the pack YAML."""
    rows = dir_menus(pack)
    lines = [
        f"# DIR catalog — {pack.pack_id}",
        "",
        "SME review table. `status`: `approved` usable for production reuse; "
        "`draft_generated` created at runtime and pending review.",
        "",
        "| menu_id | status | variant | industry | label | starter codes | summary |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        codes = row.get("common_codes") or []
        code_bits: List[str] = []
        if isinstance(codes, list):
            for c in codes[:3]:
                if isinstance(c, str):
                    code_bits.append(f"`{c}`")
                elif isinstance(c, Mapping) and c.get("code"):
                    code_bits.append(f"`{c['code']}`")
        summary = str(row.get("summary") or "").replace("|", "/").replace("\n", " ")
        label = str(row.get("label") or "").replace("|", "/")
        lines.append(
            "| {mid} | {status} | {variant} | {industry} | {label} | {codes} | {summary} |".format(
                mid=str(row.get("menu_id") or ""),
                status=str(row.get("status") or row.get("lifecycle") or ""),
                variant=str(row.get("equipment_system_variant") or ""),
                industry=str(row.get("industry") or ""),
                label=label,
                codes=", ".join(code_bits) or "—",
                summary=summary or "—",
            )
        )
    lines.append("")
    out = pack.path / "dir_catalog.md"
    if pack.path.exists() and not str(pack.path).startswith("<"):
        out.write_text("\n".join(lines), encoding="utf-8")
    return out


def validate_common_codes_for_menu(
    pack: KnowledgePack,
    *,
    scenario_id: str,
    requirements: Sequence[Mapping[str, Any]],
    common_codes: Sequence[Any],
) -> List[str]:
    """Return list of invalid common-code strings (empty if all good)."""
    bad: List[str] = []
    for item in common_codes or []:
        code = item if isinstance(item, str) else str((item or {}).get("code") or "")
        if not code:
            continue
        check = validate_dir_code(
            pack,
            scenario_id,
            code,
            requirements=requirements,
            common_codes=[],
        )
        if not check.ok:
            bad.append(code)
    return bad
