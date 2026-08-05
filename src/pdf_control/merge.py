"""Document information, composition, selection, splitting, and rotation."""

from collections.abc import Iterable
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from pdf_control._pdf import parse_page_spec, readable_pdf_reader


def get_pdf_info(input_pdf: Path) -> dict:
    reader = PdfReader(str(input_pdf))
    encrypted = reader.is_encrypted
    metadata = {} if encrypted else reader.metadata or {}
    return {
        "path": str(input_pdf),
        "pages": None if encrypted else len(reader.pages),
        "encrypted": bool(encrypted),
        "title": metadata.get("/Title"),
        "author": metadata.get("/Author"),
        "producer": metadata.get("/Producer"),
        "creator": metadata.get("/Creator"),
    }


def get_page_size(input_pdf: Path, page_number: int = 1) -> tuple[float, float]:
    if page_number < 1:
        raise ValueError("Page number must start from 1.")
    reader = readable_pdf_reader(input_pdf)
    if page_number > len(reader.pages):
        raise ValueError(f"Page {page_number} exceeds document page count ({len(reader.pages)}).")
    page = reader.pages[page_number - 1]
    return float(page.mediabox.width), float(page.mediabox.height)


def _write(writer: PdfWriter, output_pdf: Path) -> None:
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as stream:
        writer.write(stream)


def merge_pdfs(inputs: Iterable[Path], output_pdf: Path) -> None:
    writer = PdfWriter()
    for input_pdf in inputs:
        for page in readable_pdf_reader(input_pdf).pages:
            writer.add_page(page)
    _write(writer, output_pdf)


def insert_pdf_after_page(
    input_pdf: Path, insert_pdf: Path, output_pdf: Path, after_page: int
) -> None:
    if after_page < 0:
        raise ValueError("after_page must be 0 or greater.")
    base = readable_pdf_reader(input_pdf)
    addition = readable_pdf_reader(insert_pdf)
    if after_page > len(base.pages):
        raise ValueError(f"Page {after_page} exceeds document page count ({len(base.pages)}).")
    writer = PdfWriter()
    for page in base.pages[:after_page]:
        writer.add_page(page)
    for page in addition.pages:
        writer.add_page(page)
    for page in base.pages[after_page:]:
        writer.add_page(page)
    _write(writer, output_pdf)


def extract_pages(input_pdf: Path, output_pdf: Path, pages: str) -> None:
    reader = readable_pdf_reader(input_pdf)
    writer = PdfWriter()
    for index in parse_page_spec(pages, len(reader.pages)):
        writer.add_page(reader.pages[index])
    _write(writer, output_pdf)


def split_pdf(input_pdf: Path, output_dir: Path) -> None:
    reader = readable_pdf_reader(input_pdf)
    output_dir.mkdir(parents=True, exist_ok=True)
    padding = max(3, len(str(len(reader.pages))))
    for number, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)
        _write(writer, output_dir / f"{input_pdf.stem}_page_{number:0{padding}d}.pdf")


def rotate_pages(input_pdf: Path, output_pdf: Path, pages: str, angle: int) -> None:
    if angle not in {90, 180, 270}:
        raise ValueError("Angle must be one of 90, 180, 270.")
    reader = readable_pdf_reader(input_pdf)
    selected = set(parse_page_spec(pages, len(reader.pages)))
    writer = PdfWriter()
    for index, page in enumerate(reader.pages):
        if index in selected:
            page.rotate(angle)
        writer.add_page(page)
    _write(writer, output_pdf)


__all__ = [
    "extract_pages",
    "get_page_size",
    "get_pdf_info",
    "insert_pdf_after_page",
    "merge_pdfs",
    "rotate_pages",
    "split_pdf",
]
