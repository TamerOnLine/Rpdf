"""Non-destructive visual layers for the browser PDF editor."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from pdf_control import limits
from pdf_control._engine import _default_unicode_font_path, _shape_arabic_text

MAX_EDITOR_LAYERS = 500
MAX_EDITOR_JSON_BYTES = 1024 * 1024
MAX_TEXT_LENGTH = 4000
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _load_fitz():
    try:
        import fitz
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("يتطلب محرر الطبقات تثبيت PyMuPDF.") from exc
    return fitz


def _number(value, name: str, *, minimum: float, maximum: float) -> float:
    if isinstance(value, bool):
        raise ValueError(f"قيمة {name} غير صالحة.")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"قيمة {name} غير صالحة.") from exc
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"قيمة {name} خارج النطاق المسموح.")
    return result


def _color(value, default: str) -> tuple[float, float, float]:
    value = value if isinstance(value, str) and _HEX_COLOR.fullmatch(value) else default
    return tuple(int(value[index : index + 2], 16) / 255 for index in (1, 3, 5))


def parse_visual_layers(payload: str, page_count: int) -> list[dict]:
    """Parse and strictly validate the untrusted editor payload."""
    if len(payload.encode("utf-8")) > MAX_EDITOR_JSON_BYTES:
        raise ValueError("بيانات التعديلات أكبر من الحد المسموح.")
    try:
        layers = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("بيانات التعديلات غير صالحة.") from exc
    if not isinstance(layers, list):
        raise ValueError("يجب إرسال التعديلات في قائمة.")
    if len(layers) > MAX_EDITOR_LAYERS:
        raise ValueError(f"لا يمكن حفظ أكثر من {MAX_EDITOR_LAYERS} طبقة.")

    validated = []
    for raw in layers:
        if not isinstance(raw, dict) or raw.get("type") not in {"mask", "text"}:
            raise ValueError("تحتوي التعديلات على نوع طبقة غير صالح.")
        page = int(_number(raw.get("page"), "الصفحة", minimum=1, maximum=page_count))
        layer = {
            "type": raw["type"],
            "page": page,
            "x": _number(raw.get("x"), "X", minimum=0, maximum=100000),
            "y": _number(raw.get("y"), "Y", minimum=0, maximum=100000),
            "width": _number(raw.get("width"), "العرض", minimum=1, maximum=100000),
            "height": _number(raw.get("height"), "الارتفاع", minimum=1, maximum=100000),
        }
        if layer["type"] == "mask":
            layer["color"] = raw.get("color", "#ffffff")
        else:
            text = raw.get("text", "")
            if not isinstance(text, str) or len(text) > MAX_TEXT_LENGTH:
                raise ValueError("نص إحدى الطبقات غير صالح أو طويل جدًا.")
            layer.update(
                text=text,
                font_size=_number(raw.get("fontSize", 16), "حجم الخط", minimum=4, maximum=200),
                color=raw.get("color", "#111111"),
                align=(
                    raw.get("align", "right")
                    if raw.get("align") in {"left", "center", "right"}
                    else "right"
                ),
            )
        validated.append(layer)
    return validated


def render_editor_page(
    input_pdf: Path, page_number: int, dpi: int = 120
) -> tuple[bytes, int, float, float]:
    """Render one page and return its PNG plus document geometry."""
    if not 72 <= dpi <= 180:
        raise ValueError("يجب أن تكون دقة المعاينة بين 72 و180 DPI.")
    limits.validate_file_size(input_pdf)
    fitz = _load_fitz()
    document = fitz.open(str(input_pdf))
    try:
        limits.validate_page_count(document.page_count, rendering=True)
        if not 1 <= page_number <= document.page_count:
            raise ValueError("رقم صفحة المعاينة غير صالح.")
        page = document.load_page(page_number - 1)
        pixmap = page.get_pixmap(dpi=dpi, alpha=False)
        return pixmap.tobytes("png"), document.page_count, page.rect.width, page.rect.height
    finally:
        document.close()


def apply_visual_layers(
    input_pdf: Path,
    output_pdf: Path,
    payload: str,
    font_path: str | None = None,
) -> int:
    """Append visual cover/text operations while retaining the original page content."""
    limits.validate_file_size(input_pdf)
    fitz = _load_fitz()
    document = fitz.open(str(input_pdf))
    try:
        limits.validate_page_count(document.page_count)
        layers = parse_visual_layers(payload, document.page_count)
        chosen_font = Path(font_path) if font_path else _default_unicode_font_path()
        font_name = "editorfont" if chosen_font else "helv"

        for layer in layers:
            page = document.load_page(layer["page"] - 1)
            rect = fitz.Rect(
                layer["x"],
                layer["y"],
                layer["x"] + layer["width"],
                layer["y"] + layer["height"],
            ) & page.rect
            if rect.is_empty or rect.is_infinite:
                raise ValueError("إحدى الطبقات تقع خارج حدود الصفحة.")
            if layer["type"] == "mask":
                color = _color(layer["color"], "#ffffff")
                page.draw_rect(rect, color=color, fill=color, overlay=True)
                continue

            if not layer["text"]:
                continue
            if chosen_font:
                page.insert_font(fontname=font_name, fontfile=str(chosen_font))
            align = {"left": 0, "center": 1, "right": 2}[layer["align"]]
            result = page.insert_textbox(
                rect,
                _shape_arabic_text(layer["text"]),
                fontsize=layer["font_size"],
                fontname=font_name,
                color=_color(layer["color"], "#111111"),
                align=align,
                overlay=True,
            )
            if result < 0:
                raise ValueError("أحد مربعات النص أصغر من محتواه؛ كبّر المربع أو صغّر الخط.")

        document.save(str(output_pdf), garbage=3, deflate=True)
        return len(layers)
    finally:
        document.close()


__all__ = ["apply_visual_layers", "parse_visual_layers", "render_editor_page"]
