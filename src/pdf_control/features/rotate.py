"""Page-rotation tab UI."""

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
    selected = _select_library_pdf("اختر ملف PDF", "rotate_pdf")
    pages = st.text_input("الصفحات", value="الكل", key="rotate_pages")
    angle = st.selectbox("زاوية الدوران", [90, 180, 270], index=0)
    output_name = st.text_input("اسم ملف الإخراج", value="rotated.pdf", key="rotate_output")
    if st.button("تدوير الصفحات", width="stretch"):
        if selected is None:
            st.error("اختر ملف PDF أولًا.")
            return

        def action(tmp_dir: Path):
            source = _write_library_pdf(selected, tmp_dir / selected)
            filename = utils.safe_name(output_name, "rotated.pdf")
            output = tmp_dir / filename
            core.rotate_pages(source, output, utils.normalize_page_spec(pages), int(angle))
            return "تم تدوير الصفحات بنجاح.", filename, output.read_bytes(), "application/pdf"

        _run_pdf_action("result_rotate", action)
    _show_result("result_rotate", "download_rotate")
