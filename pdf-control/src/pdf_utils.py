from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable, List, Set

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ModuleNotFoundError:
    arabic_reshaper = None
    get_display = None


def _parse_page_spec(pages: str, max_pages: int) -> List[int]:
    """
    Convert page spec like '1,3,5-7' to zero-based sorted unique page indexes.
    """
    selected: Set[int] = set()

    if not pages.strip():
        raise ValueError("Page spec is empty.")

    for part in pages.split(","):
        token = part.strip()
        if not token:
            continue

        if "-" in token:
            bounds = token.split("-", maxsplit=1)
            if len(bounds) != 2 or not bounds[0].strip().isdigit() or not bounds[1].strip().isdigit():
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


def get_pdf_info(input_pdf: Path) -> dict:
    reader = PdfReader(str(input_pdf))
    encrypted = reader.is_encrypted
    meta = reader.metadata or {}

    return {
        "path": str(input_pdf),
        "pages": len(reader.pages),
        "encrypted": bool(encrypted),
        "title": meta.get("/Title"),
        "author": meta.get("/Author"),
        "producer": meta.get("/Producer"),
        "creator": meta.get("/Creator"),
    }


def merge_pdfs(inputs: Iterable[Path], output_pdf: Path) -> None:
    writer = PdfWriter()
    for file_path in inputs:
        reader = PdfReader(str(file_path))
        for page in reader.pages:
            writer.add_page(page)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as f:
        writer.write(f)


def extract_pages(input_pdf: Path, output_pdf: Path, pages: str) -> None:
    reader = PdfReader(str(input_pdf))
    indexes = _parse_page_spec(pages, len(reader.pages))

    writer = PdfWriter()
    for idx in indexes:
        writer.add_page(reader.pages[idx])

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as f:
        writer.write(f)


def split_pdf(input_pdf: Path, output_dir: Path) -> None:
    reader = PdfReader(str(input_pdf))
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = input_pdf.stem
    total = len(reader.pages)
    pad = max(3, len(str(total)))

    for i, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)
        out_name = f"{stem}_page_{str(i).zfill(pad)}.pdf"
        out_file = output_dir / out_name
        with out_file.open("wb") as f:
            writer.write(f)


def rotate_pages(input_pdf: Path, output_pdf: Path, pages: str, angle: int) -> None:
    if angle not in {90, 180, 270}:
        raise ValueError("Angle must be one of 90, 180, 270.")

    reader = PdfReader(str(input_pdf))
    indexes = set(_parse_page_spec(pages, len(reader.pages)))

    writer = PdfWriter()
    for idx, page in enumerate(reader.pages):
        if idx in indexes:
            page.rotate(angle)
        writer.add_page(page)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as f:
        writer.write(f)


def replace_text_in_pdf(
    input_pdf: Path,
    output_pdf: Path,
    find_text: str,
    replace_text: str,
    pages: str | None = None,
) -> int:
    if not find_text:
        raise ValueError("find_text cannot be empty.")

    reader = PdfReader(str(input_pdf))
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
                                operands[0] = TextStringObject(text_value.replace(find_text, replace_text))
                                replaced_count += occurrences
                    elif operator == b"TJ" and operands:
                        array_obj = operands[0]
                        for i, item in enumerate(array_obj):
                            if isinstance(item, TextStringObject):
                                text_value = str(item)
                                occurrences = text_value.count(find_text)
                                if occurrences:
                                    array_obj[i] = TextStringObject(text_value.replace(find_text, replace_text))
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

    reader = PdfReader(str(input_pdf))
    if page_number > len(reader.pages):
        raise ValueError(f"Page {page_number} exceeds document page count ({len(reader.pages)}).")

    target_index = page_number - 1
    target_page = reader.pages[target_index]
    page_width = float(target_page.mediabox.width)
    page_height = float(target_page.mediabox.height)

    overlay_buffer = io.BytesIO()
    overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))

    font_name = "Helvetica"
    if font_path:
        font_name = "CustomFont"
        pdfmetrics.registerFont(TTFont(font_name, font_path))

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
