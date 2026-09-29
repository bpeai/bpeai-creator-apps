"""Title-slide hero: a labeled engineering line sketch.

Shared by equipment_evaluator and equipment_sizing. The picture is drawn in
code (real fonts, leader lines). It does not call an image model.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

from PIL import Image, ImageDraw, ImageFont

_BG = (247, 250, 252)
_INK = (23, 50, 77)
_STEEL = (87, 98, 109)
_LEADER = (170, 179, 176)
_TEAL = (15, 198, 90)
_CANVAS = (1024, 1365)


def infer_sketch_family(result: Mapping[str, Any]) -> str:
    """Pick a line-sketch geometry from the equipment identity already on the result."""
    blob = " ".join(
        str(result.get(key) or "")
        for key in (
            "system_name",
            "equipment_name",
            "equipment_type",
            "equipment_system",
            "sized_item",
            "selected_model",
            "recommended_basis",
        )
    ).lower()
    if any(token in blob for token in ("heat exchanger", "exchanger", "phex", "condenser")):
        return "heat_exchanger"
    if any(token in blob for token in ("chromatograph", "column", "packed bed")):
        return "column"
    if any(
        token in blob
        for token in ("agitator", "mixing", "vessel", "tank", "bioreactor", "ferment", "impeller")
    ):
        return "vessel"
    return "generic"


def resolve_hero_callouts(
    result: Mapping[str, Any],
    callouts: Sequence[Any] | None = None,
) -> list[dict[str, str]]:
    """Up to four label/detail pairs. Empty when the slide and specs name no components."""
    items: list[dict[str, str]] = []
    for item in callouts or []:
        if isinstance(item, Mapping):
            label = str(item.get("label") or "").strip()
            detail = str(item.get("detail") or item.get("value") or "").strip()
        else:
            label = str(item or "").strip()
            detail = ""
        if label:
            items.append({"label": label[:32], "detail": detail[:36]})
    if items:
        return items[:4]
    for spec in result.get("key_specs") or []:
        if not isinstance(spec, Mapping):
            continue
        label = str(spec.get("key") or "").strip()
        if not label:
            continue
        value = str(spec.get("value") or "").strip()
        unit = str(spec.get("unit") or "").strip()
        detail = " ".join(part for part in (value, unit) if part)
        items.append({"label": label[:32], "detail": detail[:36]})
        if len(items) == 4:
            break
    return items


def render_title_hero(
    result: Mapping[str, Any],
    *,
    output_path: Path | str,
    callouts: Sequence[Any] | None = None,
) -> Path:
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    family = infer_sketch_family(result)
    labels = resolve_hero_callouts(result, callouts)
    img = Image.new("RGB", _CANVAS, _BG)
    draw = ImageDraw.Draw(img)
    anchors = _draw_family(draw, family)
    _draw_callouts(draw, anchors, labels)
    img.save(dest, format="PNG")
    return dest


def attach_title_hero_image(
    result: Mapping[str, Any],
    slide_pack: MutableMapping[str, Any],
    *,
    output_path: Path | str,
) -> Path | None:
    """Draw a hero PNG and stamp ``hero_image_path`` onto the slide pack."""
    title0: Mapping[str, Any] = {}
    slides = slide_pack.get("slides")
    if isinstance(slides, list) and slides and isinstance(slides[0], Mapping):
        title0 = slides[0]
    raw_callouts = title0.get("hero_callouts")
    callouts = raw_callouts if isinstance(raw_callouts, list) else None
    path = render_title_hero(result, output_path=output_path, callouts=callouts)
    slide_pack["hero_image_path"] = str(path)
    return path


def _font(size: int) -> ImageFont.ImageFont:
    candidates = [
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "consola.ttf"),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _draw_family(draw: ImageDraw.ImageDraw, family: str) -> list[tuple[int, int]]:
    if family == "heat_exchanger":
        return _draw_heat_exchanger(draw)
    if family == "column":
        return _draw_column(draw)
    if family == "vessel":
        return _draw_vessel(draw)
    return _draw_generic(draw)


def _draw_vessel(draw: ImageDraw.ImageDraw) -> list[tuple[int, int]]:
    left, right = 340, 700
    top, bot = 300, 1100
    draw.arc([left, top - 50, right, top + 70], 180, 360, fill=_INK, width=4)
    draw.line([left, top, left, bot - 40], fill=_INK, width=4)
    draw.line([right, top, right, bot - 40], fill=_INK, width=4)
    draw.arc([left, bot - 110, right, bot + 20], 0, 180, fill=_INK, width=4)
    draw.line([left - 16, top, right + 16, top], fill=_INK, width=5)
    # Shaft and impeller.
    draw.line([512, 150, 512, 980], fill=_INK, width=5)
    draw.line([390, 940, 634, 940], fill=_INK, width=6)
    draw.line([420, 980, 604, 980], fill=_INK, width=5)
    draw.rectangle([452, 70, 572, 150], outline=_INK, width=4)
    # Fill level.
    for x in range(left + 12, right - 8, 16):
        draw.line([x, 640, x + 8, 640], fill=_STEEL, width=2)
    draw.ellipse([500, 928, 524, 952], fill=_TEAL)
    return [(512, 110), (left, 640), (420, 960), (524, 940)]


def _draw_column(draw: ImageDraw.ImageDraw) -> list[tuple[int, int]]:
    left, right = 390, 634
    top, bot = 280, 1080
    draw.ellipse([left, top - 36, right, top + 48], outline=_INK, width=4)
    draw.ellipse([left, bot - 48, right, bot + 36], outline=_INK, width=4)
    draw.line([left, top, left, bot], fill=_INK, width=4)
    draw.line([right, top, right, bot], fill=_INK, width=4)
    bed_top, bed_bot = 620, 920
    draw.line([left + 8, bed_top, right - 8, bed_top], fill=_INK, width=3)
    draw.line([left + 8, bed_bot, right - 8, bed_bot], fill=_INK, width=3)
    for y in range(bed_top + 28, bed_bot, 28):
        draw.line([left + 16, y, right - 16, y], fill=_STEEL, width=2)
    # Top and bottom nozzles.
    draw.line([512, 140, 512, top - 20], fill=_INK, width=4)
    draw.rectangle([488, 110, 536, 150], outline=_INK, width=3)
    draw.line([512, bot + 20, 512, 1220], fill=_INK, width=4)
    draw.rectangle([488, 1200, 536, 1240], outline=_INK, width=3)
    # Side port.
    draw.line([right, 480, 760, 480], fill=_INK, width=4)
    draw.rectangle([760, 460, 800, 500], outline=_INK, width=3)
    return [(512, 130), (512, 760), (512, 1220), (780, 480)]


def _draw_heat_exchanger(draw: ImageDraw.ImageDraw) -> list[tuple[int, int]]:
    # End frames.
    draw.rectangle([300, 360, 360, 1040], outline=_INK, width=4)
    draw.rectangle([664, 360, 724, 1040], outline=_INK, width=4)
    # Plate pack.
    x = 370
    while x < 660:
        draw.line([x, 400, x, 1000], fill=_STEEL, width=3)
        x += 16
    draw.rectangle([370, 400, 654, 1000], outline=_INK, width=3)
    # Tie rods.
    for y in (430, 970):
        draw.line([280, y, 744, y], fill=_INK, width=3)
    # Nozzles.
    draw.line([250, 480, 300, 480], fill=_INK, width=4)
    draw.arc([190, 440, 270, 560], 90, 270, fill=_INK, width=4)
    draw.line([724, 560, 800, 560], fill=_INK, width=4)
    draw.arc([760, 520, 840, 640], 270, 90, fill=_INK, width=4)
    draw.line([250, 900, 300, 900], fill=_INK, width=4)
    draw.line([724, 820, 800, 820], fill=_INK, width=4)
    return [(512, 700), (220, 500), (820, 560), (512, 400)]


def _draw_generic(draw: ImageDraw.ImageDraw) -> list[tuple[int, int]]:
    draw.rounded_rectangle([280, 420, 744, 1040], radius=18, outline=_INK, width=4)
    draw.rectangle([360, 520, 664, 860], outline=_STEEL, width=3)
    draw.line([200, 620, 280, 620], fill=_INK, width=4)
    draw.line([744, 820, 840, 820], fill=_INK, width=4)
    return [(512, 690), (200, 620), (840, 820)]


def _draw_callouts(
    draw: ImageDraw.ImageDraw,
    anchors: Sequence[tuple[int, int]],
    labels: Sequence[Mapping[str, str]],
) -> None:
    if not labels or not anchors:
        return
    font = _font(22)
    detail_font = _font(18)
    pairs = list(zip(anchors, labels))
    for index, (anchor, item) in enumerate(pairs[:4]):
        label = str(item.get("label") or "").strip()
        detail = str(item.get("detail") or "").strip()
        if not label:
            continue
        on_left = index % 2 == 1
        text_x = 36 if on_left else 760
        text_y = max(48, min(anchor[1] - 12, 1240))
        end = (text_x + (240 if on_left else 0), text_y + 10)
        draw.line([anchor, end], fill=_LEADER, width=2)
        draw.ellipse([anchor[0] - 4, anchor[1] - 4, anchor[0] + 4, anchor[1] + 4], fill=_INK)
        draw.text((text_x, text_y), label, fill=_INK, font=font)
        if detail:
            draw.text((text_x, text_y + 28), detail, fill=_TEAL, font=detail_font)
