"""Resource guards used before expensive PDF work."""

from pathlib import Path

from pdf_control import config

MIB = 1024 * 1024


def validate_file_size(path: Path) -> None:
    size = path.stat().st_size
    maximum = config.max_file_size_mb() * MIB
    if size > maximum:
        raise ValueError(
            f"{path.name} is {size / MIB:.1f} MB; the processing limit is "
            f"{config.max_file_size_mb()} MB."
        )


def validate_page_count(page_count: int, *, rendering: bool = False) -> None:
    maximum = config.max_render_pages() if rendering else config.max_pdf_pages()
    if page_count > maximum:
        operation = "rendering" if rendering else "processing"
        raise ValueError(
            f"The PDF has {page_count} pages; the {operation} limit is {maximum} pages."
        )


def validate_upload(data: bytes, current_session_bytes: int = 0) -> None:
    validate_upload_size(len(data), current_session_bytes)


def validate_upload_size(size: int, current_session_bytes: int = 0) -> None:
    """Validate a running upload size without retaining the upload in memory."""
    if size > config.max_file_size_mb() * MIB:
        raise ValueError(f"يتجاوز الملف الحد المسموح ({config.max_file_size_mb()} MB).")
    if current_session_bytes + size > config.max_session_size_mb() * MIB:
        raise ValueError(f"تتجاوز مكتبة الجلسة الحد المسموح ({config.max_session_size_mb()} MB).")
