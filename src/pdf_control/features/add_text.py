"""Streamlit UI for the add text workflow."""

import tempfile
from pathlib import Path

import streamlit as st

from pdf_control import core, utils
from pdf_control.ui import (
    _run_pdf_action,
    _select_library_pdf,
    _show_result,
    _write_library_pdf,
    _write_upload,
)


def render() -> None:
    selected_pdf = _select_library_pdf("اختر ملف PDF", "addtext_pdf")
    font_file = st.file_uploader("خط TTF اختياري", type=["ttf"], key="addtext_font")
    st.caption("سيتم إنشاء ملف PDF جديد. بعد نجاح العملية اضغط تحميل النتيجة.")
    text = st.text_input("النص المراد إضافته", value="تمت المراجعة")
    col1, col2 = st.columns(2)
    with col1:
        page = st.number_input("رقم الصفحة", min_value=1, value=1, step=1)
        x = st.number_input("X", value=120.0, step=10.0)
    with col2:
        size = st.number_input("حجم الخط", min_value=1, value=16, step=1)
        y = st.number_input("Y", value=100.0, step=10.0)
    output_name = st.text_input("اسم ملف الإخراج", value="with_text.pdf", key="addtext_output")

    if selected_pdf is not None:
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                source = _write_library_pdf(selected_pdf, Path(tmp_dir) / selected_pdf)
                page_width, page_height = core.get_page_size(source, int(page))
            st.caption(
                f"حجم الصفحة {int(page)}: {page_width:.0f} x {page_height:.0f}. "
                "الإحداثيات تبدأ من أسفل يسار الصفحة."
            )
        except Exception as exc:
            st.caption(str(exc))

    if st.button("إضافة النص", width="stretch"):
        if selected_pdf is None:
            st.error("اختر ملف PDF أولًا.")
            return

        def action(tmp_dir: Path):
            source = _write_library_pdf(selected_pdf, tmp_dir / selected_pdf)
            font_path = None
            if font_file is not None:
                font_path = str(_write_upload(font_file, tmp_dir / "font.ttf"))
            filename = utils.safe_name(output_name, "with_text.pdf")
            output = tmp_dir / filename
            core.add_text_overlay(
                source,
                output,
                int(page),
                text,
                float(x),
                float(y),
                int(size),
                font_path,
            )
            return (
                "تم إنشاء ملف جديد يحتوي على النص. اضغط تحميل النتيجة.",
                filename,
                output.read_bytes(),
                "application/pdf",
            )

        _run_pdf_action("result_add_text", action)
    _show_result("result_add_text", "download_add_text")
