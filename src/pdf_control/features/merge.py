"""Merge-tab UI."""

from pathlib import Path

import streamlit as st

from pdf_control import core, utils
from pdf_control.ui import (
    _library_names,
    _run_pdf_action,
    _show_result,
    _write_library_pdf,
)


def render() -> None:
    selected = st.multiselect("اختر ملفين أو أكثر من المكتبة", _library_names(), key="merge_pdfs")
    output_name = st.text_input("اسم ملف الإخراج", value="merged.pdf", key="merge_output")
    if st.button("دمج الملفات", width="stretch"):
        if len(selected) < 2:
            st.error("اختر ملفين على الأقل.")
            return

        def action(tmp_dir: Path):
            inputs = [
                _write_library_pdf(name, tmp_dir / f"{i}_{utils.safe_name(name, 'input.pdf')}")
                for i, name in enumerate(selected, start=1)
            ]
            filename = utils.safe_name(output_name, "merged.pdf")
            output = tmp_dir / filename
            core.merge_pdfs(inputs, output)
            return "تم دمج الملفات بنجاح.", filename, output.read_bytes(), "application/pdf"

        _run_pdf_action("result_merge", action)
    _show_result("result_merge", "download_merge")
