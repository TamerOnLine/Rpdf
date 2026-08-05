"""PDF-insertion tab UI."""

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
    base = _select_library_pdf("ملف PDF الأساسي", "insert_base")
    inserted = _select_library_pdf("ملف PDF المراد إدراجه", "insert_file")
    after_page = st.number_input("الإدراج بعد الصفحة", min_value=0, value=1, step=1)
    output_name = st.text_input("اسم ملف الإخراج", value="inserted.pdf", key="insert_output")
    if st.button("إدراج الملف", width="stretch"):
        if not base or not inserted:
            st.error("اختر الملف الأساسي وملف الإدراج.")
            return

        def action(tmp_dir: Path):
            source = _write_library_pdf(base, tmp_dir / f"base_{utils.safe_name(base, 'base.pdf')}")
            addition = _write_library_pdf(
                inserted, tmp_dir / f"insert_{utils.safe_name(inserted, 'insert.pdf')}"
            )
            filename = utils.safe_name(output_name, "inserted.pdf")
            output = tmp_dir / filename
            core.insert_pdf_after_page(source, addition, output, int(after_page))
            return "تم إدراج الملف بنجاح.", filename, output.read_bytes(), "application/pdf"

        _run_pdf_action("result_insert", action)
    _show_result("result_insert", "download_insert")
