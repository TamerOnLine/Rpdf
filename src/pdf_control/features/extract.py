"""Page-extraction tab UI."""

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
    selected = _select_library_pdf("اختر ملف PDF", "extract_pdf")
    pages = st.text_input("الصفحات", value="الكل", help='مثال: "الكل" أو "1,3,5-7" أو "3;8"')
    output_name = st.text_input("اسم ملف الإخراج", value="extracted.pdf", key="extract_output")
    if st.button("استخراج الصفحات", width="stretch"):
        if selected is None:
            st.error("اختر ملف PDF أولًا.")
            return

        def action(tmp_dir: Path):
            source = _write_library_pdf(selected, tmp_dir / selected)
            filename = utils.safe_name(output_name, "extracted.pdf")
            output = tmp_dir / filename
            core.extract_pages(source, output, utils.normalize_page_spec(pages))
            return "تم استخراج الصفحات بنجاح.", filename, output.read_bytes(), "application/pdf"

        _run_pdf_action("result_extract", action)
    _show_result("result_extract", "download_extract")
