"""Shared PDF validation and page-selection primitives."""

from pathlib import Path

from pypdf import PdfReader

from pdf_control import limits


def readable_pdf_reader(input_pdf: Path) -> PdfReader:
    limits.validate_file_size(input_pdf)
    reader = PdfReader(str(input_pdf))
    if reader.is_encrypted:
        raise ValueError(
            f"{input_pdf.name} is encrypted. Decrypt it before running this operation."
        )
    limits.validate_page_count(len(reader.pages))
    return reader


def parse_page_spec(pages: str, max_pages: int) -> list[int]:
    """Convert a 1-based page specification to sorted, unique zero-based indexes."""
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
            if len(bounds) != 2 or not all(bound.strip().isdigit() for bound in bounds):
                raise ValueError(f"Invalid page range: {token}")
            start, end = (int(bound.strip()) for bound in bounds)
            if start < 1 or end < 1 or end < start:
                raise ValueError(f"Invalid page range: {token}")
            page_numbers = range(start, end + 1)
        else:
            if not token.isdigit():
                raise ValueError(f"Invalid page number: {token}")
            page_numbers = (int(token),)

        for page_number in page_numbers:
            if page_number < 1:
                raise ValueError("Page numbers start from 1.")
            if page_number > max_pages:
                raise ValueError(f"Page {page_number} exceeds document page count ({max_pages}).")
            selected.add(page_number - 1)

    if not selected:
        raise ValueError("No valid pages selected.")
    return sorted(selected)
