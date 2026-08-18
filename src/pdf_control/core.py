"""Stable public facade for PDF Control's processing modules."""

from pdf_control import _engine
from pdf_control._engine import (  # noqa: F401
    _extract_vector_checkbox_candidates,
    _load_ocr_dependencies,
    _load_pdf_render_dependency,
    _render_pdf_as_image_background,
)
from pdf_control._pdf import parse_page_spec as _parse_page_spec  # noqa: F401
from pdf_control.editing import add_text_overlay, replace_text_in_pdf
from pdf_control.layers import apply_visual_layers, render_editor_page
from pdf_control.merge import (
    extract_pages,
    get_page_size,
    get_pdf_info,
    insert_pdf_after_page,
    merge_pdfs,
    rotate_pages,
    split_pdf,
)
from pdf_control.ocr import render_pdf_pages_as_png as _render_pdf_pages_as_png


def render_pdf_pages_as_png(input_pdf, dpi=120):
    """Render PDF pages without mutating process-wide engine state."""
    return _render_pdf_pages_as_png(
        input_pdf,
        dpi=dpi,
        dependency_loader=_load_pdf_render_dependency,
    )


def create_editable_pdf(*args, **kwargs):
    """Create fields with call-scoped OCR dependencies."""
    kwargs.setdefault("ocr_dependency_loader", _load_ocr_dependencies)
    return _engine.create_editable_pdf(*args, **kwargs)


def create_exact_editable_pdf(*args, **kwargs):
    """Create an exact editable PDF with call-scoped collaborators."""
    kwargs.setdefault("ocr_dependency_loader", _load_ocr_dependencies)
    kwargs.setdefault("background_renderer", _render_pdf_as_image_background)
    kwargs.setdefault("vector_checkbox_extractor", _extract_vector_checkbox_candidates)
    return _engine.create_exact_editable_pdf(*args, **kwargs)


__all__ = [
    "add_text_overlay",
    "apply_visual_layers",
    "create_editable_pdf",
    "create_exact_editable_pdf",
    "extract_pages",
    "get_page_size",
    "get_pdf_info",
    "insert_pdf_after_page",
    "merge_pdfs",
    "render_pdf_pages_as_png",
    "render_editor_page",
    "replace_text_in_pdf",
    "rotate_pages",
    "split_pdf",
]
