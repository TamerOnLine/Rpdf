from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    BooleanObject,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

from pdf_control import limits

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ModuleNotFoundError:
    arabic_reshaper = None
    get_display = None


DEFAULT_UNICODE_FONT_PATHS = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
)


@dataclass(frozen=True)
class _EditableFieldCandidate:
    page_index: int
    text: str
    x: float
    y: float
    width: float
    height: float
    font_size: float


@dataclass(frozen=True)
class _EditableCheckboxCandidate:
    page_index: int
    x: float
    y: float
    size: float
    checked: bool = False


@dataclass
class _OcrLine:
    page_index: int
    texts: list[str]
    left: float
    top: float
    right: float
    bottom: float


def _readable_pdf_reader(input_pdf: Path) -> PdfReader:
    limits.validate_file_size(input_pdf)
    reader = PdfReader(str(input_pdf))
    if reader.is_encrypted:
        raise ValueError(
            f"{input_pdf.name} is encrypted. Decrypt it before running this operation."
        )
    limits.validate_page_count(len(reader.pages))
    return reader


def _parse_page_spec(pages: str, max_pages: int) -> list[int]:
    """
    Convert page spec like '1,3,5-7' to zero-based sorted unique page indexes.
    """
    selected: set[int] = set()
    page_spec = pages.strip()

    if not page_spec:
        raise ValueError("Page spec is empty.")

    if page_spec.casefold() in {"*", "all", "all pages", "الكل", "كل", "كل الصفحات"}:
        if max_pages < 1:
            raise ValueError("No valid pages selected.")
        return list(range(max_pages))

    for part in page_spec.split(","):
        token = part.strip()
        if not token:
            continue

        if "-" in token:
            bounds = token.split("-", maxsplit=1)
            if (
                len(bounds) != 2
                or not bounds[0].strip().isdigit()
                or not bounds[1].strip().isdigit()
            ):
                raise ValueError(f"Invalid page range: {token}")
            start = int(bounds[0].strip())
            end = int(bounds[1].strip())
            if start < 1 or end < 1 or end < start:
                raise ValueError(f"Invalid page range: {token}")
            for page_num in range(start, end + 1):
                idx = page_num - 1
                if idx >= max_pages:
                    raise ValueError(f"Page {page_num} exceeds document page count ({max_pages}).")
                selected.add(idx)
        else:
            if not token.isdigit():
                raise ValueError(f"Invalid page number: {token}")
            page_num = int(token)
            if page_num < 1:
                raise ValueError("Page numbers start from 1.")
            idx = page_num - 1
            if idx >= max_pages:
                raise ValueError(f"Page {page_num} exceeds document page count ({max_pages}).")
            selected.add(idx)

    if not selected:
        raise ValueError("No valid pages selected.")

    return sorted(selected)


def _shape_arabic_text(text: str) -> str:
    if arabic_reshaper is None or get_display is None:
        return text
    return get_display(arabic_reshaper.reshape(text))


def _contains_non_latin_text(text: str) -> bool:
    return any(ord(char) > 255 for char in text)


def _default_unicode_font_path() -> Path | None:
    for path in DEFAULT_UNICODE_FONT_PATHS:
        if path.exists():
            return path
    return None


def _matrix_position(cm, tm) -> tuple[float, float]:
    return (
        float(tm[4]) * float(cm[0]) + float(tm[5]) * float(cm[2]) + float(cm[4]),
        float(tm[4]) * float(cm[1]) + float(tm[5]) * float(cm[3]) + float(cm[5]),
    )


def _field_rect(candidate: _EditableFieldCandidate) -> ArrayObject:
    return ArrayObject(
        [
            FloatObject(candidate.x),
            FloatObject(candidate.y),
            FloatObject(candidate.x + candidate.width),
            FloatObject(candidate.y + candidate.height),
        ]
    )


def _checkbox_rect(candidate: _EditableCheckboxCandidate) -> ArrayObject:
    return ArrayObject(
        [
            FloatObject(candidate.x),
            FloatObject(candidate.y),
            FloatObject(candidate.x + candidate.size),
            FloatObject(candidate.y + candidate.size),
        ]
    )


def _load_ocr_dependencies():
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "OCR requires optional dependencies. Install them with: "
            "pip install -e '.[ocr]'. The Tesseract system package is also required."
        ) from exc

    return fitz, Image, pytesseract


def _load_pdf_render_dependency():
    try:
        import fitz
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "PDF rendering requires PyMuPDF. Install dependencies with: pip install -e ."
        ) from exc

    return fitz


def _ocr_confidence(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0


def _ocr_data_value(data: dict, key: str, index: int, default):
    values = data.get(key)
    if values is None or index >= len(values):
        return default
    return values[index]


def _ocr_line_key(data: dict, index: int) -> tuple[int, int, int]:
    return (
        int(_ocr_data_value(data, "block_num", index, 0) or 0),
        int(_ocr_data_value(data, "par_num", index, 0) or 0),
        int(_ocr_data_value(data, "line_num", index, index) or index),
    )


def _extract_ocr_editable_field_candidates(
    input_pdf: Path,
    reader: PdfReader,
    page_indexes: set[int],
    max_fields: int,
    language: str,
    dpi: int,
    min_confidence: float,
    dependency_loader=None,
) -> list[_EditableFieldCandidate]:
    if dpi < 72:
        raise ValueError("ocr_dpi must be 72 or greater.")
    if not language.strip():
        raise ValueError("OCR language cannot be empty.")

    loader = dependency_loader or _load_ocr_dependencies
    fitz, Image, pytesseract = loader()
    candidates: list[_EditableFieldCandidate] = []
    document = fitz.open(str(input_pdf))

    try:
        for page_index in sorted(page_indexes):
            if len(candidates) >= max_fields:
                break

            page = reader.pages[page_index]
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            pixmap = document.load_page(page_index).get_pixmap(dpi=dpi, alpha=False)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            image_width, image_height = image.size
            if image_width <= 0 or image_height <= 0:
                continue

            try:
                data = pytesseract.image_to_data(
                    image,
                    lang=language.strip(),
                    output_type=pytesseract.Output.DICT,
                )
            except Exception as exc:
                if exc.__class__.__name__ == "TesseractNotFoundError":
                    raise RuntimeError(
                        "Tesseract is not installed or is not available in PATH."
                    ) from exc
                raise

            lines: dict[tuple[int, int, int], _OcrLine] = {}
            for index, raw_text in enumerate(data.get("text", [])):
                text = " ".join(str(raw_text).split())
                if not text:
                    continue
                if _ocr_confidence(_ocr_data_value(data, "conf", index, -1)) < min_confidence:
                    continue

                left = float(_ocr_data_value(data, "left", index, 0) or 0)
                top = float(_ocr_data_value(data, "top", index, 0) or 0)
                width = float(_ocr_data_value(data, "width", index, 0) or 0)
                height = float(_ocr_data_value(data, "height", index, 0) or 0)
                if width <= 0 or height <= 0:
                    continue

                key = _ocr_line_key(data, index)
                right = left + width
                bottom = top + height
                if key in lines:
                    line = lines[key]
                    line.texts.append(text)
                    line.left = min(line.left, left)
                    line.top = min(line.top, top)
                    line.right = max(line.right, right)
                    line.bottom = max(line.bottom, bottom)
                else:
                    lines[key] = _OcrLine(
                        page_index=page_index,
                        texts=[text],
                        left=left,
                        top=top,
                        right=right,
                        bottom=bottom,
                    )

            x_scale = page_width / image_width
            y_scale = page_height / image_height
            for line in lines.values():
                if len(candidates) >= max_fields:
                    break

                x = line.left * x_scale
                y = page_height - (line.bottom * y_scale)
                if x < 0 or y < 0 or x >= page_width or y >= page_height:
                    continue

                width = max(8.0, (line.right - line.left) * x_scale)
                height = max(10.0, (line.bottom - line.top) * y_scale)
                candidates.append(
                    _EditableFieldCandidate(
                        page_index=line.page_index,
                        text=" ".join(line.texts),
                        x=x,
                        y=max(0.0, y),
                        width=min(width, page_width - x),
                        height=min(height, page_height - max(0.0, y)),
                        font_size=max(6.0, min(height * 0.8, 18.0)),
                    )
                )
    finally:
        close = getattr(document, "close", None)
        if close is not None:
            close()

    return candidates


def _checkbox_is_checked_from_pixmap(pixmap, rect, dpi: int) -> bool:
    scale = dpi / 72.0
    x0 = max(0, int((rect.x0 + rect.width * 0.25) * scale))
    y0 = max(0, int((rect.y0 + rect.height * 0.25) * scale))
    x1 = min(pixmap.width, int((rect.x1 - rect.width * 0.25) * scale))
    y1 = min(pixmap.height, int((rect.y1 - rect.height * 0.25) * scale))
    if x1 <= x0 or y1 <= y0:
        return False

    components = pixmap.n
    data = pixmap.samples
    dark_pixels = 0
    total_pixels = 0
    stride = max(1, min(x1 - x0, y1 - y0) // 8)
    for y in range(y0, y1, stride):
        row = y * pixmap.width * components
        for x in range(x0, x1, stride):
            offset = row + x * components
            red = data[offset]
            green = data[offset + 1] if components > 1 else red
            blue = data[offset + 2] if components > 2 else red
            if (int(red) + int(green) + int(blue)) / 3 < 150:
                dark_pixels += 1
            total_pixels += 1

    return total_pixels > 0 and dark_pixels / total_pixels > 0.08


def _inherited_pdf_value(annotation, key: str):
    current = annotation
    seen: set[int] = set()
    while current is not None:
        obj_id = id(current)
        if obj_id in seen:
            return None
        seen.add(obj_id)

        if key in current:
            return current[key]

        parent = current.get("/Parent")
        if parent is None:
            return None
        current = parent.get_object()

    return None


def _pdf_name_value(value) -> str:
    if value is None:
        return ""
    return str(value)


def _is_checked_state(value) -> bool:
    return _pdf_name_value(value) not in {"", "/Off", "Off", "None", "null"}


def _checkbox_candidates_overlap(
    first: _EditableCheckboxCandidate,
    second: _EditableCheckboxCandidate,
) -> bool:
    if first.page_index != second.page_index:
        return False

    first_x1 = first.x + first.size
    first_y1 = first.y + first.size
    second_x1 = second.x + second.size
    second_y1 = second.y + second.size
    overlap_width = max(0.0, min(first_x1, second_x1) - max(first.x, second.x))
    overlap_height = max(0.0, min(first_y1, second_y1) - max(first.y, second.y))
    overlap_area = overlap_width * overlap_height
    if overlap_area <= 0:
        return False

    smaller_area = min(first.size * first.size, second.size * second.size)
    return smaller_area > 0 and overlap_area / smaller_area > 0.45


def _merge_checkbox_candidates(
    primary: list[_EditableCheckboxCandidate],
    secondary: list[_EditableCheckboxCandidate],
    limit: int,
) -> list[_EditableCheckboxCandidate]:
    merged = list(primary[:limit])
    for candidate in secondary:
        if len(merged) >= limit:
            break
        if any(_checkbox_candidates_overlap(candidate, existing) for existing in merged):
            continue
        merged.append(candidate)
    return merged


def _extract_original_checkbox_candidates(
    reader: PdfReader,
    page_indexes: set[int],
    max_checkboxes: int,
) -> list[_EditableCheckboxCandidate]:
    if max_checkboxes < 1:
        return []

    candidates: list[_EditableCheckboxCandidate] = []
    for page_index, page in enumerate(reader.pages):
        if page_index not in page_indexes:
            continue
        if len(candidates) >= max_checkboxes:
            break

        annotations = page.get("/Annots") or []
        for annotation_ref in annotations:
            if len(candidates) >= max_checkboxes:
                break

            annotation = annotation_ref.get_object()
            if annotation.get("/Subtype") != "/Widget":
                continue

            field_type = _inherited_pdf_value(annotation, "/FT")
            if field_type != "/Btn":
                continue

            field_flags = int(_inherited_pdf_value(annotation, "/Ff") or 0)
            pushbutton = 1 << 16
            radio = 1 << 15
            if field_flags & (pushbutton | radio):
                continue

            rect = annotation.get("/Rect")
            if rect is None or len(rect) != 4:
                continue

            x0, y0, x1, y1 = [float(value) for value in rect]
            x = min(x0, x1)
            y = min(y0, y1)
            width = abs(x1 - x0)
            height = abs(y1 - y0)
            if width <= 0 or height <= 0:
                continue
            if not (4.0 <= min(width, height) <= 40.0 and max(width, height) <= 50.0):
                continue

            state = annotation.get("/AS") or _inherited_pdf_value(annotation, "/V")
            candidates.append(
                _EditableCheckboxCandidate(
                    page_index=page_index,
                    x=x,
                    y=y,
                    size=max(width, height),
                    checked=_is_checked_state(state),
                )
            )

    return candidates


def _extract_vector_checkbox_candidates(
    input_pdf: Path,
    reader: PdfReader,
    page_indexes: set[int],
    max_checkboxes: int,
    render_dpi: int = 150,
) -> list[_EditableCheckboxCandidate]:
    if max_checkboxes < 1:
        return []

    fitz = _load_pdf_render_dependency()
    document = fitz.open(str(input_pdf))
    candidates: list[_EditableCheckboxCandidate] = []
    seen: set[tuple[int, int, int]] = set()

    try:
        for page_index in sorted(page_indexes):
            if len(candidates) >= max_checkboxes:
                break

            page = document.load_page(page_index)
            page_height = float(reader.pages[page_index].mediabox.height)
            pixmap = page.get_pixmap(dpi=render_dpi, alpha=False)

            for drawing in page.get_drawings():
                if len(candidates) >= max_checkboxes:
                    break

                rect = drawing.get("rect")
                if rect is None:
                    continue

                width = float(rect.width)
                height = float(rect.height)
                if width <= 0 or height <= 0:
                    continue
                if not (6.0 <= width <= 24.0 and 6.0 <= height <= 24.0):
                    continue
                if min(width, height) / max(width, height) < 0.75:
                    continue

                key = (page_index, round(float(rect.x0)), round(float(rect.y0)))
                if key in seen:
                    continue
                seen.add(key)

                size = max(width, height)
                checked = _checkbox_is_checked_from_pixmap(pixmap, rect, render_dpi)
                candidates.append(
                    _EditableCheckboxCandidate(
                        page_index=page_index,
                        x=float(rect.x0),
                        y=page_height - float(rect.y1),
                        size=size,
                        checked=checked,
                    )
                )
    finally:
        close = getattr(document, "close", None)
        if close is not None:
            close()

    return candidates


def _extract_editable_field_candidates(
    reader: PdfReader,
    page_indexes: set[int],
    max_fields: int,
) -> list[_EditableFieldCandidate]:
    candidates: list[_EditableFieldCandidate] = []

    for page_index, page in enumerate(reader.pages):
        if page_index not in page_indexes:
            continue

        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        def visitor(
            text,
            cm,
            tm,
            font_dict,
            font_size,
            page_index=page_index,
            page_width=page_width,
            page_height=page_height,
        ) -> None:
            del font_dict
            if len(candidates) >= max_fields:
                return

            clean_text = " ".join(str(text).split())
            if not clean_text:
                return

            x, baseline_y = _matrix_position(cm, tm)
            size = max(6.0, float(font_size or 10.0))
            height = max(12.0, size * 1.35)
            y = baseline_y - size * 0.25
            if x < 0 or y < 0 or x >= page_width or y >= page_height:
                return

            estimated_width = max(size * 3.0, len(clean_text) * size * 0.55)
            width = min(estimated_width, page_width - x)
            if width <= 1:
                return

            candidates.append(
                _EditableFieldCandidate(
                    page_index=page_index,
                    text=clean_text,
                    x=x,
                    y=y,
                    width=width,
                    height=min(height, page_height - y),
                    font_size=size,
                )
            )

        page.extract_text(visitor_text=visitor)

    return candidates


def _acroform_dictionary(writer: PdfWriter) -> DictionaryObject:
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
        }
    )
    font_ref = writer._add_object(font)

    return DictionaryObject(
        {
            NameObject("/Fields"): ArrayObject(),
            NameObject("/NeedAppearances"): BooleanObject(True),
            NameObject("/DA"): TextStringObject("/Helv 0 Tf 0 g"),
            NameObject("/DR"): DictionaryObject(
                {
                    NameObject("/Font"): DictionaryObject({NameObject("/Helv"): font_ref}),
                }
            ),
        }
    )


def _ensure_acroform(writer: PdfWriter) -> DictionaryObject:
    if NameObject("/AcroForm") not in writer._root_object:
        writer._root_object[NameObject("/AcroForm")] = _acroform_dictionary(writer)
    return writer._root_object[NameObject("/AcroForm")]


def _render_pdf_as_image_background(input_pdf: Path, output_buffer: io.BytesIO, dpi: int) -> None:
    if dpi < 72:
        raise ValueError("render_dpi must be 72 or greater.")

    try:
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            f"{exc}. Install dependencies first: pip install -r requirements.txt"
        ) from exc

    limits.validate_file_size(input_pdf)
    fitz = _load_pdf_render_dependency()
    document = fitz.open(str(input_pdf))

    try:
        limits.validate_page_count(document.page_count, rendering=True)
        background = canvas.Canvas(output_buffer)
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            rect = page.rect
            page_width = float(rect.width)
            page_height = float(rect.height)
            pixmap = page.get_pixmap(dpi=dpi, alpha=False)

            background.setPageSize((page_width, page_height))
            background.drawImage(
                ImageReader(io.BytesIO(pixmap.tobytes("png"))),
                0,
                0,
                width=page_width,
                height=page_height,
            )
            background.showPage()
        background.save()
    finally:
        close = getattr(document, "close", None)
        if close is not None:
            close()


def _add_editable_fields(
    writer: PdfWriter,
    candidates: list[_EditableFieldCandidate],
    show_field_values: bool = False,
) -> int:
    acroform = _ensure_acroform(writer)
    fields = acroform[NameObject("/Fields")]

    for index, candidate in enumerate(candidates, start=1):
        field_name = f"editable_text_{index:04d}"
        font_size = max(6.0, min(candidate.font_size, 24.0))
        field_value = candidate.text if show_field_values else ""
        annotation = {
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/FT"): NameObject("/Tx"),
            NameObject("/T"): TextStringObject(field_name),
            NameObject("/TU"): TextStringObject(candidate.text),
            NameObject("/V"): TextStringObject(field_value),
            NameObject("/DV"): TextStringObject(field_value),
            NameObject("/Rect"): _field_rect(candidate),
            NameObject("/DA"): TextStringObject(f"/Helv {font_size:.2f} Tf 0 g"),
            NameObject("/F"): NumberObject(4),
            NameObject("/Ff"): NumberObject(0),
            NameObject("/Border"): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0)]),
        }
        added = writer.add_annotation(candidate.page_index, annotation)
        fields.append(added.indirect_reference)

    writer.set_need_appearances_writer(True)
    return len(candidates)


def _checkbox_appearance(size: float, checked: bool) -> DecodedStreamObject:
    stream = DecodedStreamObject()
    line_width = max(0.8, size * 0.08)
    commands = [
        "q",
        "1 1 1 rg",
        "0 0 0 RG",
        f"{line_width:.2f} w",
        f"0.5 0.5 {max(1.0, size - 1):.2f} {max(1.0, size - 1):.2f} re B",
    ]
    if checked:
        commands.extend(
            [
                "0 0 0 RG",
                f"{max(1.2, size * 0.12):.2f} w",
                f"{size * 0.22:.2f} {size * 0.52:.2f} m",
                f"{size * 0.42:.2f} {size * 0.28:.2f} l",
                f"{size * 0.78:.2f} {size * 0.78:.2f} l S",
            ]
        )
    commands.append("Q")
    stream.set_data(("\n".join(commands) + "\n").encode("ascii"))
    stream.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Form"),
            NameObject("/BBox"): ArrayObject(
                [FloatObject(0), FloatObject(0), FloatObject(size), FloatObject(size)]
            ),
            NameObject("/Resources"): DictionaryObject(),
        }
    )
    return stream


def _add_checkbox_fields(
    writer: PdfWriter,
    candidates: list[_EditableCheckboxCandidate],
) -> int:
    acroform = _ensure_acroform(writer)
    fields = acroform[NameObject("/Fields")]

    for index, candidate in enumerate(candidates, start=1):
        field_name = f"editable_checkbox_{index:04d}"
        off_ref = writer._add_object(_checkbox_appearance(candidate.size, False))
        yes_ref = writer._add_object(_checkbox_appearance(candidate.size, True))
        state = NameObject("/Yes" if candidate.checked else "/Off")
        annotation = {
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/FT"): NameObject("/Btn"),
            NameObject("/T"): TextStringObject(field_name),
            NameObject("/V"): state,
            NameObject("/AS"): state,
            NameObject("/Rect"): _checkbox_rect(candidate),
            NameObject("/F"): NumberObject(4),
            NameObject("/Ff"): NumberObject(0),
            NameObject("/Border"): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(1)]),
            NameObject("/AP"): DictionaryObject(
                {
                    NameObject("/N"): DictionaryObject(
                        {
                            NameObject("/Off"): off_ref,
                            NameObject("/Yes"): yes_ref,
                        }
                    )
                }
            ),
        }
        added = writer.add_annotation(candidate.page_index, annotation)
        fields.append(added.indirect_reference)

    writer.set_need_appearances_writer(True)
    return len(candidates)


def replace_text_in_pdf(
    input_pdf: Path,
    output_pdf: Path,
    find_text: str,
    replace_text: str,
    pages: str | None = None,
) -> int:
    if not find_text:
        raise ValueError("find_text cannot be empty.")

    reader = _readable_pdf_reader(input_pdf)
    writer = PdfWriter()
    replaced_count = 0

    if pages:
        target_indexes = set(_parse_page_spec(pages, len(reader.pages)))
    else:
        target_indexes = set(range(len(reader.pages)))

    for idx, page in enumerate(reader.pages):
        if idx in target_indexes:
            content = page.get_contents()
            if content is not None:
                content_stream = content if hasattr(content, "operations") else None
                if content_stream is None:
                    from pypdf.generic import ContentStream

                    content_stream = ContentStream(content, reader)

                for operands, operator in content_stream.operations:
                    if operator == b"Tj" and operands:
                        text_obj = operands[0]
                        if isinstance(text_obj, TextStringObject):
                            text_value = str(text_obj)
                            occurrences = text_value.count(find_text)
                            if occurrences:
                                operands[0] = TextStringObject(
                                    text_value.replace(find_text, replace_text)
                                )
                                replaced_count += occurrences
                    elif operator == b"TJ" and operands:
                        array_obj = operands[0]
                        for i, item in enumerate(array_obj):
                            if isinstance(item, TextStringObject):
                                text_value = str(item)
                                occurrences = text_value.count(find_text)
                                if occurrences:
                                    array_obj[i] = TextStringObject(
                                        text_value.replace(find_text, replace_text)
                                    )
                                    replaced_count += occurrences

                if hasattr(page, "replace_contents"):
                    page.replace_contents(content_stream)
                else:
                    page[NameObject("/Contents")] = content_stream

        writer.add_page(page)

    if replaced_count == 0:
        raise ValueError("No matching text found in selected pages.")

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as f:
        writer.write(f)

    return replaced_count


def create_editable_pdf(
    input_pdf: Path,
    output_pdf: Path,
    pages: str | None = None,
    max_fields: int = 300,
    use_ocr: bool = False,
    ocr_language: str = "eng",
    ocr_dpi: int = 200,
    ocr_min_confidence: float = 30.0,
    show_field_values: bool = False,
    *,
    ocr_dependency_loader=None,
) -> int:
    if max_fields < 1:
        raise ValueError("max_fields must be greater than 0.")

    reader = _readable_pdf_reader(input_pdf)
    if pages:
        page_indexes = set(_parse_page_spec(pages, len(reader.pages)))
    else:
        page_indexes = set(range(len(reader.pages)))

    if use_ocr:
        candidates = _extract_ocr_editable_field_candidates(
            input_pdf,
            reader,
            page_indexes,
            max_fields,
            ocr_language,
            ocr_dpi,
            ocr_min_confidence,
            ocr_dependency_loader,
        )
    else:
        candidates = _extract_editable_field_candidates(reader, page_indexes, max_fields)

    if not candidates:
        if use_ocr:
            raise ValueError("OCR did not find text in the selected pages.")
        raise ValueError("No selectable text was found. Enable OCR for scanned/image-only PDFs.")

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    field_count = _add_editable_fields(writer, candidates, show_field_values)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as f:
        writer.write(f)

    return field_count


def create_exact_editable_pdf(
    input_pdf: Path,
    output_pdf: Path,
    pages: str | None = None,
    max_fields: int = 300,
    use_ocr: bool = False,
    ocr_language: str = "eng",
    ocr_dpi: int = 200,
    ocr_min_confidence: float = 30.0,
    render_dpi: int = 200,
    show_field_values: bool = False,
    detect_checkboxes: bool = True,
    max_checkboxes: int = 300,
    *,
    ocr_dependency_loader=None,
    background_renderer=None,
    vector_checkbox_extractor=None,
) -> int:
    if max_fields < 1:
        raise ValueError("max_fields must be greater than 0.")

    reader = _readable_pdf_reader(input_pdf)
    if pages:
        page_indexes = set(_parse_page_spec(pages, len(reader.pages)))
    else:
        page_indexes = set(range(len(reader.pages)))

    if use_ocr:
        candidates = _extract_ocr_editable_field_candidates(
            input_pdf,
            reader,
            page_indexes,
            max_fields,
            ocr_language,
            ocr_dpi,
            ocr_min_confidence,
            ocr_dependency_loader,
        )
    else:
        candidates = _extract_editable_field_candidates(reader, page_indexes, max_fields)

    checkboxes: list[_EditableCheckboxCandidate] = []
    if detect_checkboxes:
        original_checkboxes = _extract_original_checkbox_candidates(
            reader,
            page_indexes,
            max_checkboxes,
        )
        remaining_checkboxes = max(0, max_checkboxes - len(original_checkboxes))
        extract_vector_checkboxes = vector_checkbox_extractor or _extract_vector_checkbox_candidates
        vector_checkboxes = extract_vector_checkboxes(
            input_pdf,
            reader,
            page_indexes,
            remaining_checkboxes,
            render_dpi=min(max(render_dpi, 100), 250),
        )
        checkboxes = _merge_checkbox_candidates(
            original_checkboxes,
            vector_checkboxes,
            max_checkboxes,
        )

    if not candidates and not checkboxes:
        if use_ocr:
            raise ValueError("OCR did not find text or checkboxes in the selected pages.")
        raise ValueError(
            "No selectable text or checkboxes were found. Enable OCR for scanned/image-only PDFs."
        )

    background_buffer = io.BytesIO()
    render_background = background_renderer or _render_pdf_as_image_background
    render_background(input_pdf, background_buffer, render_dpi)
    background_buffer.seek(0)
    background_reader = PdfReader(background_buffer)

    writer = PdfWriter()
    for page in background_reader.pages:
        writer.add_page(page)

    field_count = 0
    if candidates:
        field_count += _add_editable_fields(writer, candidates, show_field_values)
    if checkboxes:
        field_count += _add_checkbox_fields(writer, checkboxes)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as f:
        writer.write(f)

    return field_count


def add_text_overlay(
    input_pdf: Path,
    output_pdf: Path,
    page_number: int,
    text: str,
    x: float,
    y: float,
    font_size: int = 14,
    font_path: str | None = None,
) -> None:
    if page_number < 1:
        raise ValueError("Page number must start from 1.")
    if not text:
        raise ValueError("text cannot be empty.")

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            f"{exc}. Install dependencies first: pip install -r requirements.txt"
        ) from exc

    reader = _readable_pdf_reader(input_pdf)
    if page_number > len(reader.pages):
        raise ValueError(f"Page {page_number} exceeds document page count ({len(reader.pages)}).")

    target_index = page_number - 1
    target_page = reader.pages[target_index]
    page_width = float(target_page.mediabox.width)
    page_height = float(target_page.mediabox.height)
    if x < 0 or y < 0 or x > page_width or y > page_height:
        raise ValueError(
            "Text position is outside page bounds. "
            f"Page size is {page_width:.0f} x {page_height:.0f}."
        )

    overlay_buffer = io.BytesIO()
    overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))

    font_name = "Helvetica"
    selected_font_path = Path(font_path) if font_path else None
    if selected_font_path is None and _contains_non_latin_text(text):
        selected_font_path = _default_unicode_font_path()

    if selected_font_path:
        font_name = "CustomFont"
        pdfmetrics.registerFont(TTFont(font_name, str(selected_font_path)))

    draw_text = _shape_arabic_text(text)
    overlay_canvas.setFont(font_name, font_size)
    overlay_canvas.drawString(x, y, draw_text)
    overlay_canvas.save()

    overlay_buffer.seek(0)
    overlay_reader = PdfReader(overlay_buffer)
    overlay_page = overlay_reader.pages[0]

    writer = PdfWriter()
    for idx, page in enumerate(reader.pages):
        if idx == target_index:
            page.merge_page(overlay_page)
        writer.add_page(page)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as f:
        writer.write(f)
