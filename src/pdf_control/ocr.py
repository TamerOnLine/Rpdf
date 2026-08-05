"""PDF rendering and OCR-facing operations."""

from pathlib import Path

from pdf_control import limits


def load_pdf_render_dependency():
    try:
        import fitz
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "PDF rendering requires PyMuPDF. Install dependencies with: pip install -e ."
        ) from exc
    return fitz


def render_pdf_pages_as_png(
    input_pdf: Path,
    dpi: int = 120,
    *,
    dependency_loader=None,
) -> list[bytes]:
    """Render every page as PNG bytes while enforcing rendering limits."""
    if dpi < 72:
        raise ValueError("dpi must be 72 or greater.")
    limits.validate_file_size(input_pdf)
    fitz = (dependency_loader or load_pdf_render_dependency)()
    document = fitz.open(str(input_pdf))
    try:
        limits.validate_page_count(document.page_count, rendering=True)
        return [
            document.load_page(index).get_pixmap(dpi=dpi, alpha=False).tobytes("png")
            for index in range(document.page_count)
        ]
    finally:
        document.close()


__all__ = ["render_pdf_pages_as_png"]
