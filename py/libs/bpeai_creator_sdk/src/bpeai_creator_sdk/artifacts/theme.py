"""Pack-local report branding (colors, fonts, optional logo).

Creators customize ``references/style/brand.yaml`` and optionally drop
``logo.png`` (or ``.jpg`` / ``.jpeg`` / ``.webp``). Generators load this theme
at render time. Reseed never overwrites an existing pack brand file.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any, Mapping

import yaml

LOGO_NAMES = ("logo.png", "logo.jpg", "logo.jpeg", "logo.webp")

# Matches family style reference PPTX chrome (navy/teal Aptos).
_DEFAULT_COLORS = {
    "navy": "17324D",
    "teal": "00A398",
    "blue": "2962A3",
    "gray": "6B7280",
    "body": "1F2937",
    "white": "FFFFFF",
    "card_fill": "F3F6F9",
    "header_bg": "17324D",
    "muted": "5B6770",
    "chip_blue_fill": "E8F1FB",
    "chip_teal_fill": "E6F7F6",
    "panel_right": "F7FAFC",
    "row_alt": "F5F8FC",
    "callout_bg": "E8EFF7",
    "grid": "C5CDD4",
}

_DEFAULT_FONTS = {
    "display": "Aptos Display",
    "body": "Aptos",
    "docx_font": "Calibri",
    "xlsx_font": "Calibri",
}


@dataclass(frozen=True)
class ReportTheme:
    navy: str = _DEFAULT_COLORS["navy"]
    teal: str = _DEFAULT_COLORS["teal"]
    blue: str = _DEFAULT_COLORS["blue"]
    gray: str = _DEFAULT_COLORS["gray"]
    body: str = _DEFAULT_COLORS["body"]
    white: str = _DEFAULT_COLORS["white"]
    card_fill: str = _DEFAULT_COLORS["card_fill"]
    header_bg: str = _DEFAULT_COLORS["header_bg"]
    muted: str = _DEFAULT_COLORS["muted"]
    chip_blue_fill: str = _DEFAULT_COLORS["chip_blue_fill"]
    chip_teal_fill: str = _DEFAULT_COLORS["chip_teal_fill"]
    panel_right: str = _DEFAULT_COLORS["panel_right"]
    row_alt: str = _DEFAULT_COLORS["row_alt"]
    callout_bg: str = _DEFAULT_COLORS["callout_bg"]
    grid: str = _DEFAULT_COLORS["grid"]
    display_font: str = _DEFAULT_FONTS["display"]
    body_font: str = _DEFAULT_FONTS["body"]
    docx_font: str = _DEFAULT_FONTS["docx_font"]
    xlsx_font: str = _DEFAULT_FONTS["xlsx_font"]
    logo_path: Path | None = None

    def hex(self, name: str) -> str:
        """Return a color field without leading ``#``."""
        value = getattr(self, name, None)
        if value is None:
            return _DEFAULT_COLORS.get(name, "000000")
        return _normalize_hex(str(value))


def default_brand_yaml_dict() -> dict[str, Any]:
    """Canonical brand.yaml payload seeded into family style stubs."""
    return {
        "fonts": {
            "display": _DEFAULT_FONTS["display"],
            "body": _DEFAULT_FONTS["body"],
            "docx_font": _DEFAULT_FONTS["docx_font"],
            "xlsx_font": _DEFAULT_FONTS["xlsx_font"],
        },
        "colors": {
            "navy": _DEFAULT_COLORS["navy"],
            "teal": _DEFAULT_COLORS["teal"],
            "blue": _DEFAULT_COLORS["blue"],
            "gray": _DEFAULT_COLORS["gray"],
            "body": _DEFAULT_COLORS["body"],
            "white": _DEFAULT_COLORS["white"],
            "card_fill": _DEFAULT_COLORS["card_fill"],
            "header_bg": _DEFAULT_COLORS["header_bg"],
            "muted": _DEFAULT_COLORS["muted"],
        },
        "notes": [
            "Edit colors/fonts to match your company brand.",
            "Optional: drop logo.png (or .jpg/.jpeg/.webp) in this folder.",
            "Reseed does not overwrite an existing brand.yaml or logo.",
        ],
    }


def default_brand_yaml_text() -> str:
    return yaml.safe_dump(default_brand_yaml_dict(), sort_keys=False, allow_unicode=True)


def _normalize_hex(value: str) -> str:
    h = str(value or "").strip().lstrip("#").upper()
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        return "000000"
    try:
        int(h, 16)
    except ValueError:
        return "000000"
    return h


def _merge_mapping(base: dict[str, Any], overlay: Mapping[str, Any] | None) -> dict[str, Any]:
    out = dict(base)
    if not isinstance(overlay, Mapping):
        return out
    for key, value in overlay.items():
        if value is None:
            continue
        out[str(key)] = value
    return out


def _theme_kwargs_from_maps(
    colors: Mapping[str, Any],
    fonts: Mapping[str, Any],
) -> dict[str, Any]:
    color_keys = {
        "navy",
        "teal",
        "blue",
        "gray",
        "body",
        "white",
        "card_fill",
        "header_bg",
        "muted",
        "chip_blue_fill",
        "chip_teal_fill",
        "panel_right",
        "row_alt",
        "callout_bg",
        "grid",
    }
    kwargs: dict[str, Any] = {}
    for key in color_keys:
        if key in colors and colors[key] is not None:
            kwargs[key] = _normalize_hex(str(colors[key]))
    # header_bg defaults to navy when only navy is customized
    if "header_bg" not in kwargs and "navy" in kwargs:
        kwargs["header_bg"] = kwargs["navy"]

    font_map = {
        "display": "display_font",
        "body": "body_font",
        "display_font": "display_font",
        "body_font": "body_font",
        "docx_font": "docx_font",
        "xlsx_font": "xlsx_font",
    }
    for src, dest in font_map.items():
        if src in fonts and str(fonts[src] or "").strip():
            kwargs[dest] = str(fonts[src]).strip()
    return kwargs


def resolve_style_logo(pack_path: Path | str | None) -> Path | None:
    if pack_path is None:
        return None
    style = Path(pack_path) / "references" / "style"
    if not style.is_dir():
        return None
    for name in LOGO_NAMES:
        candidate = style / name
        if candidate.is_file():
            return candidate.resolve()
    return None


def _load_brand_yaml(pack_path: Path | None) -> dict[str, Any]:
    if pack_path is None:
        return {}
    path = Path(pack_path) / "references" / "style" / "brand.yaml"
    if not path.is_file():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _outline_style(outline: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(outline, Mapping):
        return {}
    style = outline.get("style")
    return style if isinstance(style, dict) else {}


def load_report_theme(
    pack_path: Path | str | None = None,
    *,
    template_family: str | None = None,
    outline: Mapping[str, Any] | None = None,
) -> ReportTheme:
    """Load branding for artifact builders.

    Preference: pack ``references/style/brand.yaml`` overrides, then
    ``pptx_outline.yaml`` ``style:``, then family defaults. Logo is resolved
    from ``references/style/logo.*`` when present.

    ``template_family`` is accepted for future per-family defaults; both
    evaluator and sizing currently share the same chrome palette.
    """
    _ = template_family  # shared defaults today; reserved for family-specific chrome
    root = Path(pack_path) if pack_path is not None else None

    colors = dict(_DEFAULT_COLORS)
    fonts = dict(_DEFAULT_FONTS)

    outline_style = _outline_style(outline)
    colors = _merge_mapping(colors, outline_style.get("colors") if isinstance(outline_style.get("colors"), Mapping) else None)
    fonts = _merge_mapping(fonts, outline_style.get("fonts") if isinstance(outline_style.get("fonts"), Mapping) else None)

    brand = _load_brand_yaml(root)
    brand_colors = brand.get("colors") if isinstance(brand.get("colors"), Mapping) else {}
    brand_fonts = brand.get("fonts") if isinstance(brand.get("fonts"), Mapping) else {}
    colors = _merge_mapping(colors, brand_colors)
    fonts = _merge_mapping(fonts, brand_fonts)
    # Allow top-level color/font keys in brand.yaml for convenience.
    top_colors = {k: brand[k] for k in _DEFAULT_COLORS if k in brand}
    top_fonts = {
        k: brand[k]
        for k in ("display", "body", "display_font", "body_font", "docx_font", "xlsx_font")
        if k in brand
    }
    colors = _merge_mapping(colors, top_colors)
    fonts = _merge_mapping(fonts, top_fonts)
    # If creator sets navy without header_bg, keep table/header chrome in sync.
    explicit_header = "header_bg" in brand_colors or "header_bg" in top_colors
    explicit_navy = "navy" in brand_colors or "navy" in top_colors
    if explicit_navy and not explicit_header:
        colors["header_bg"] = colors["navy"]

    theme = ReportTheme(**_theme_kwargs_from_maps(colors, fonts))
    logo = resolve_style_logo(root)
    if logo is not None:
        theme = replace(theme, logo_path=logo)
    # Drop unknown kwargs safety: ReportTheme only accepts known fields
    allowed = {f.name for f in fields(ReportTheme)}
    data = {k: getattr(theme, k) for k in allowed}
    return ReportTheme(**data)
