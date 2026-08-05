"""Streamlit UI for the xournal workflow."""

import shutil
import tempfile
from pathlib import Path

import streamlit as st

from pdf_control.ui import (
    _open_xournal,
    _select_library_pdf,
    _unique_xournal_pdf_path,
    _write_library_pdf,
)


def render() -> None:
    st.caption("افتح Xournal++ فارغًا أو افتح ملف PDF للمعاينة والتعديل اليدوي.")

    if st.button("فتح Xournal++ بدون PDF", width="stretch"):
        xournal_bin = shutil.which("xournalpp")
        if xournal_bin is None:
            st.error("برنامج Xournal++ غير مثبت. ثبّت الحزمة xournalpp أولًا.")
            return
        try:
            _open_xournal(xournal_bin)
            st.success("تم فتح Xournal++.")
        except Exception as exc:
            st.error(str(exc))

    local_path = st.text_input("مسار ملف PDF على الجهاز", key="xournal_path")
    selected_pdf = _select_library_pdf("أو اختر ملفًا من مكتبة الملفات", "xournal_selected")

    if st.button("فتح في Xournal++", width="stretch"):
        xournal_bin = shutil.which("xournalpp")
        if xournal_bin is None:
            st.error("برنامج Xournal++ غير مثبت. ثبّت الحزمة xournalpp أولًا.")
            return

        try:
            if selected_pdf is not None:
                xournal_dir = Path(tempfile.gettempdir()) / "pdf-control-xournal"
                xournal_dir.mkdir(parents=True, exist_ok=True)
                open_path = _write_library_pdf(
                    selected_pdf,
                    _unique_xournal_pdf_path(selected_pdf, xournal_dir),
                )
            else:
                if not local_path.strip():
                    st.error("أدخل مسار ملف PDF أو أضف ملفًا إلى المكتبة أولًا.")
                    return
                open_path = Path(local_path.strip()).expanduser()
                if not open_path.exists():
                    st.error("الملف غير موجود.")
                    return

            _open_xournal(xournal_bin, open_path)
            st.success("تم إرسال الملف إلى Xournal++.")
        except Exception as exc:
            st.error(str(exc))
