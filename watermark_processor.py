from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal

from PIL import Image, ImageEnhance, ImageOps


Anchor = Literal[
    "top_left",
    "top_center",
    "top_right",
    "center_left",
    "center",
    "center_right",
    "bottom_left",
    "bottom_center",
    "bottom_right",
]


@dataclass(frozen=True)
class WatermarkSettings:
    watermark_path: Path
    anchor: Anchor = "bottom_right"
    width_percent: float = 18.0
    margin_percent: float = 4.0
    top_margin_percent: float | None = None
    opacity: float = 0.85


@dataclass(frozen=True)
class TransformState:
    offset_x: int = 0
    mirrored: bool = False


def render_watermarked_image(
    image_bytes: bytes,
    settings: WatermarkSettings,
    state: TransformState | None = None,
) -> bytes:
    state = state or TransformState()

    with Image.open(BytesIO(image_bytes)) as source_image:
        base = ImageOps.exif_transpose(source_image).convert("RGBA")

    if state.mirrored:
        base = ImageOps.mirror(base)

    watermark = _load_watermark(settings, base.width)
    x, y = _calculate_position(base.size, watermark.size, settings, state.offset_x)

    canvas = Image.new("RGBA", base.size, (255, 255, 255, 0))
    canvas.alpha_composite(base)
    canvas.alpha_composite(watermark, (x, y))

    output = BytesIO()
    canvas.convert("RGB").save(output, format="JPEG", quality=94, optimize=True)
    return output.getvalue()


def _load_watermark(settings: WatermarkSettings, image_width: int) -> Image.Image:
    if not settings.watermark_path.exists():
        raise FileNotFoundError(
            f"Watermark file not found: {settings.watermark_path}. "
            "Put your channel logo there or change WATERMARK_PATH."
        )

    watermark = Image.open(settings.watermark_path).convert("RGBA")
    target_width = max(1, round(image_width * settings.width_percent / 100))
    ratio = target_width / watermark.width
    target_height = max(1, round(watermark.height * ratio))
    watermark = watermark.resize((target_width, target_height), Image.Resampling.LANCZOS)

    opacity = min(1.0, max(0.0, settings.opacity))
    if opacity < 1:
        alpha = watermark.getchannel("A")
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        watermark.putalpha(alpha)

    return watermark


def _calculate_position(
    image_size: tuple[int, int],
    watermark_size: tuple[int, int],
    settings: WatermarkSettings,
    offset_x: int,
) -> tuple[int, int]:
    image_width, image_height = image_size
    watermark_width, watermark_height = watermark_size
    margin = round(min(image_width, image_height) * settings.margin_percent / 100)
    top_margin_percent = (
        settings.margin_percent
        if settings.top_margin_percent is None
        else settings.top_margin_percent
    )
    top_margin = round(min(image_width, image_height) * top_margin_percent / 100)

    horizontal, vertical = _split_anchor(settings.anchor)

    if horizontal == "left":
        x = margin
    elif horizontal == "center":
        x = (image_width - watermark_width) // 2
    else:
        x = image_width - watermark_width - margin

    if vertical == "top":
        y = top_margin
    elif vertical == "center":
        y = (image_height - watermark_height) // 2
    else:
        y = image_height - watermark_height - margin

    x = min(max(x + offset_x, 0), image_width - watermark_width)
    y = min(max(y, 0), image_height - watermark_height)
    return x, y


def _split_anchor(anchor: str) -> tuple[str, str]:
    match anchor:
        case "top_left":
            return "left", "top"
        case "top_center":
            return "center", "top"
        case "top_right":
            return "right", "top"
        case "center_left":
            return "left", "center"
        case "center":
            return "center", "center"
        case "center_right":
            return "right", "center"
        case "bottom_left":
            return "left", "bottom"
        case "bottom_center":
            return "center", "bottom"
        case "bottom_right":
            return "right", "bottom"
        case _:
            return "right", "bottom"
