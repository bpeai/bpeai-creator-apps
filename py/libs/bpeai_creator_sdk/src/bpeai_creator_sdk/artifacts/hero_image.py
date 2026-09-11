"""Title-slide hero image: OpenAI rendering with a technical-sketch fallback.

Shared by equipment_evaluator and equipment_sizing. The PPTX layout owns
placement; this module writes a portrait PNG (no embedded text).
"""

from __future__ import annotations

import base64
import os
import urllib.request
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from PIL import Image, ImageDraw, ImageFilter


def build_hero_image_prompt(result: Mapping[str, Any], *, llm_prompt: str = "") -> str:
    extra = " ".join(str(llm_prompt or "").strip().split())
    if extra:
        return extra
    system = str(result.get("system_name") or result.get("equipment_name") or "process equipment").strip()
    concept = str(
        result.get("selected_model") or result.get("recommended_basis") or ""
    ).strip()
    family = str(result.get("equipment_system") or result.get("equipment_type") or "").lower()
    blob = " ".join([system, concept, family]).lower()
    mixing = any(
        token in blob
        for token in ("agitator", "mixing", "vessel", "tank", "bioreactor", "reactor")
    )
    if mixing:
        duty = concept or "top-entry sanitary axial-flow hydrofoil agitator"
        return (
            "Professional life-science equipment catalog rendering, portrait 3:4. "
            f"Cutaway of a hygienic 316L stainless-steel {system} with a centered "
            f"top-entry agitator. Show the gearmotor and seal housing on the top head, "
            f"a polished shaft, and {duty} inside the vessel. Include light wall baffles. "
            "Pale cool-gray studio background matching hex F7FAFC. Soft even lighting, "
            "photoreal, high detail, no text, no labels, no logos, no people, no watermark."
        )
    duty = concept or "sanitary process equipment package"
    return (
        "Professional life-science equipment catalog rendering, portrait 3:4. "
        f"Photoreal studio view of a hygienic {system} ({duty}). "
        "Pale cool-gray studio background matching hex F7FAFC. Soft even lighting, "
        "high detail, no text, no labels, no logos, no people, no watermark."
    )


def render_title_hero(
    result: Mapping[str, Any],
    *,
    output_path: Path | str,
    llm_prompt: str = "",
) -> Path:
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    prompt = build_hero_image_prompt(result, llm_prompt=llm_prompt)
    generated = _openai_hero_png(prompt, dest)
    if generated is not None:
        return generated
    return draw_equipment_schematic(result, dest)


def attach_title_hero_image(
    result: Mapping[str, Any],
    slide_pack: MutableMapping[str, Any],
    *,
    output_path: Path | str,
) -> Path | None:
    """Generate a hero PNG and stamp ``hero_image_path`` onto the slide pack."""
    title0: Mapping[str, Any] = {}
    slides = slide_pack.get("slides")
    if isinstance(slides, list) and slides and isinstance(slides[0], Mapping):
        title0 = slides[0]
    llm_prompt = str(title0.get("hero_image_prompt") or "").strip()
    path = render_title_hero(result, output_path=output_path, llm_prompt=llm_prompt)
    slide_pack["hero_image_path"] = str(path)
    return path


def _openai_hero_png(prompt: str, dest: Path) -> Path | None:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except Exception:
        return None
    client = OpenAI(api_key=api_key)
    preferred = (os.getenv("OPENAI_IMAGE_MODEL") or "").strip()
    attempts = []
    if preferred:
        attempts.append((preferred, os.getenv("OPENAI_IMAGE_SIZE") or "1024x1536"))
    attempts.extend(
        [
            ("gpt-image-1", "1024x1536"),
            ("dall-e-3", "1024x1792"),
            ("dall-e-3", "1024x1024"),
        ]
    )
    seen: set[tuple[str, str]] = set()
    for model, size in attempts:
        key = (model, size)
        if key in seen:
            continue
        seen.add(key)
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "prompt": prompt,
                "n": 1,
                "size": size,
            }
            if model.startswith("dall-e"):
                kwargs["quality"] = "hd"
                kwargs["style"] = "natural"
                kwargs["response_format"] = "b64_json"
            resp = client.images.generate(**kwargs)
            item = resp.data[0]
            payload = getattr(item, "b64_json", None)
            if payload:
                dest.write_bytes(base64.b64decode(payload))
                return dest
            url = getattr(item, "url", None)
            if url:
                urllib.request.urlretrieve(url, dest)
                return dest
        except Exception:
            continue
    return None


def draw_equipment_schematic(result: Mapping[str, Any], dest: Path) -> Path:
    """Deterministic cutaway sketch used when the image API is unavailable."""
    w, h = 1024, 1365
    bg = (247, 250, 252)
    navy = (23, 50, 77)
    teal = (0, 163, 152)
    steel = (196, 208, 218)
    steel_dk = (120, 140, 158)
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    cx = w // 2
    tank_w = 420
    tank_top = 310
    tank_bot = 1120
    left = cx - tank_w // 2
    right = cx + tank_w // 2

    draw.ellipse([left, tank_top - 70, right, tank_top + 90], outline=navy, width=6, fill=steel)
    draw.ellipse([left, tank_bot - 90, right, tank_bot + 70], outline=navy, width=6, fill=steel)
    draw.rectangle([left, tank_top + 10, right, tank_bot - 10], fill=(232, 239, 244), outline=navy, width=6)
    draw.rectangle([left + 18, tank_top + 28, right - 18, tank_bot - 28], fill=(238, 246, 248))

    for x in (left + 36, right - 44):
        draw.rectangle([x, tank_top + 80, x + 10, tank_bot - 80], fill=steel_dk)

    liquid_top = tank_top + 160
    draw.rectangle([left + 18, liquid_top, right - 18, tank_bot - 28], fill=(214, 236, 234))
    draw.line([left + 18, liquid_top, right - 18, liquid_top], fill=teal, width=4)

    draw.rectangle([cx - 10, 210, cx + 10, tank_bot - 140], fill=navy)
    impeller_ys = (liquid_top + 160, tank_bot - 220, tank_bot - 360)
    n_imp = 2
    concept = str(result.get("selected_model") or result.get("recommended_basis") or "").lower()
    if "three" in concept or "3 " in concept:
        n_imp = 3
    for y in impeller_ys[:n_imp]:
        _hydrofoil(draw, cx, y, span=300, color=teal)

    draw.rounded_rectangle([cx - 70, 70, cx + 70, 170], radius=16, fill=navy)
    draw.rounded_rectangle([cx - 48, 170, cx + 48, 230], radius=10, fill=steel_dk)
    draw.ellipse([cx - 22, 188, cx + 22, 232], fill=teal)
    draw.rectangle([cx - 90, 228, cx + 90, 258], fill=steel, outline=navy, width=3)

    for x in (left + 40, right - 56):
        draw.rectangle([x, tank_bot + 20, x + 16, tank_bot + 90], fill=navy)
        draw.rectangle([x - 18, tank_bot + 90, x + 34, tank_bot + 102], fill=navy)

    img = img.filter(ImageFilter.SMOOTH)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, format="PNG")
    return dest


def _hydrofoil(draw: ImageDraw.ImageDraw, cx: int, y: int, *, span: int, color: tuple[int, int, int]) -> None:
    half = span // 2
    draw.polygon([(cx - half, y), (cx - 40, y - 22), (cx - 18, y), (cx - 40, y + 22)], fill=color)
    draw.polygon([(cx + half, y), (cx + 40, y - 22), (cx + 18, y), (cx + 40, y + 22)], fill=color)
    draw.ellipse([cx - 16, y - 16, cx + 16, y + 16], fill=(23, 50, 77))
