"""Streamlit application shell; tab implementations live in features."""

import streamlit as st

from pdf_control import ui
from pdf_control.features import (
    add_text,
    edit,
    editable,
    exact_editable,
    extract,
    info,
    insert,
    library,
    merge,
    preview,
    rotate,
    split,
    xournal,
)

# Backwards-compatible utility exports used by integrations and tests.
_open_xournal = ui._open_xournal
_pdf_data_uri = ui._pdf_data_uri
_unique_library_name = ui._unique_library_name
_unique_xournal_pdf_path = ui._unique_xournal_pdf_path
subprocess = ui.subprocess
uuid = ui.uuid


def main() -> None:
    st.set_page_config(page_title="PDF Control", page_icon="📄", layout="wide")
    st.title("PDF Control")
    st.caption("واجهة Streamlit للتحكم بملفات PDF")
    library.render()

    renderers = [
        ("معاينة", preview.render),
        ("Xournal++", xournal.render),
        ("معلومات", info.render),
        ("دمج", merge.render),
        ("استخراج", extract.render),
        ("تقسيم", split.render),
        ("تدوير", rotate.render),
        ("استبدال نص", edit.render),
        ("إضافة نص", add_text.render),
        ("نسخة قابلة للتعديل", editable.render),
        ("طبق الأصل", exact_editable.render),
        ("إدراج", insert.render),
    ]
    tabs = st.tabs([label for label, _ in renderers])
    for tab, (_, renderer) in zip(tabs, renderers, strict=True):
        with tab:
            renderer()


if __name__ == "__main__":
    main()
