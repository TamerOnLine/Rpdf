"""PDF-information tab UI."""

import tempfile
from pathlib import Path

import streamlit as st

from pdf_control import core
from pdf_control.ui import _select_library_pdf, _write_library_pdf


def render() -> None:
    selected = _select_library_pdf("اختر ملف PDF", "info_pdf")
    if st.button("عرض المعلومات", width="stretch"):
        if selected is None:
            st.error("اختر ملف PDF أولًا.")
            return
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = _write_library_pdf(selected, Path(tmp_dir) / selected)
            try:
                st.session_state["pdf_info"] = core.get_pdf_info(source)
            except Exception as exc:
                st.error(str(exc))
                return
    info = st.session_state.get("pdf_info")
    if info:
        st.dataframe(
            [
                {"الحقل": key, "القيمة": "" if value is None else str(value)}
                for key, value in info.items()
            ],
            hide_index=True,
            width="stretch",
        )
