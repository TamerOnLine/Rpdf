"""Streamlit UI for the preview workflow."""

import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from pdf_control import core
from pdf_control.ui import (
    _pdf_data_uri,
    _pdf_library,
    _select_library_pdf,
    _write_library_pdf,
)


def render() -> None:
    selected_pdf = _select_library_pdf("اختر ملف PDF", "preview_pdf")
    if selected_pdf is None:
        return

    library = _pdf_library()
    data = library[selected_pdf]

    with tempfile.TemporaryDirectory() as tmp_dir:
        source = _write_library_pdf(selected_pdf, Path(tmp_dir) / selected_pdf)
        try:
            info = core.get_pdf_info(source)
        except Exception as exc:
            st.warning(str(exc))
            info = None

    if info and info.get("pages") is not None:
        st.caption(f"عدد الصفحات: {info['pages']}")

    st.download_button(
        "تحميل الملف",
        data=data,
        file_name=selected_pdf,
        mime="application/pdf",
        key="download_preview_source",
        width="stretch",
    )

    preview_mode = st.radio(
        "طريقة المعاينة",
        ["صور الصفحات", "عارض PDF"],
        horizontal=True,
        key="preview_mode",
    )

    if preview_mode == "صور الصفحات":
        dpi = st.slider(
            "وضوح الصور",
            min_value=72,
            max_value=180,
            value=120,
            step=12,
            key="preview_dpi",
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = _write_library_pdf(selected_pdf, Path(tmp_dir) / selected_pdf)
            try:
                page_images = core.render_pdf_pages_as_png(source, dpi=int(dpi))
            except ModuleNotFoundError as exc:
                st.warning(str(exc))
                page_images = []
            except Exception as exc:
                st.error(str(exc))
                page_images = []

        for index, page_image in enumerate(page_images, start=1):
            st.image(page_image, caption=f"صفحة {index}", width="stretch")
        return

    height = st.slider(
        "ارتفاع عارض PDF",
        min_value=500,
        max_value=1400,
        value=900,
        step=100,
        key="preview_height",
    )
    components.html(
        (
            '<iframe title="PDF preview" '
            f'src="{_pdf_data_uri(data)}#toolbar=1&navpanes=1&view=FitH" '
            'width="100%" '
            f'height="{height}" '
            'style="border:1px solid #d0d7de;border-radius:6px;background:white;"></iframe>'
        ),
        height=height + 20,
    )
