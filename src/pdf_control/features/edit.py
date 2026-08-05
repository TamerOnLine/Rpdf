"""Streamlit UI for the edit workflow."""

from pathlib import Path

import streamlit as st

from pdf_control import core, utils
from pdf_control.ui import (
    _run_pdf_action,
    _select_library_pdf,
    _show_result,
    _write_library_pdf,
)


def render() -> None:
    selected_pdf = _select_library_pdf("اختر ملف PDF", "edit_pdf")
    find_text = st.text_input("النص الحالي")
    replace_text = st.text_input("النص البديل")
    pages = st.text_input(
        "الصفحات الاختيارية",
        value="",
        help='اتركها فارغة لكل الصفحات. مثال: "1,3,5-7" أو "3;8"',
    )
    output_name = st.text_input("اسم ملف الإخراج", value="edited.pdf", key="edit_output")

    if st.button("استبدال النص", width="stretch"):
        if selected_pdf is None:
            st.error("اختر ملف PDF أولًا.")
            return

        def action(tmp_dir: Path):
            source = _write_library_pdf(selected_pdf, tmp_dir / selected_pdf)
            filename = utils.safe_name(output_name, "edited.pdf")
            output = tmp_dir / filename
            count = core.replace_text_in_pdf(
                source,
                output,
                find_text,
                replace_text,
                utils.normalize_page_spec(pages) or None,
            )
            label = f"تم استبدال {count} موضع/مواضع بنجاح."
            return label, filename, output.read_bytes(), "application/pdf"

        _run_pdf_action("result_edit", action)
    _show_result("result_edit", "download_edit")
