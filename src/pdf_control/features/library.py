"""Streamlit UI for the library workflow."""

import streamlit as st

from pdf_control.ui import _add_library_uploads, _pdf_library, _reset_library_uploader


def render() -> None:
    with st.expander("مكتبة ملفات PDF", expanded=True):
        upload_key = st.session_state.setdefault("library_upload_key", "library_uploads_0")
        st.file_uploader(
            "إضافة ملفات PDF",
            type=["pdf"],
            key=upload_key,
            accept_multiple_files=True,
            on_change=_add_library_uploads,
        )

        library = _pdf_library()
        if not library:
            st.caption("لم تتم إضافة ملفات بعد.")
            return

        st.dataframe(
            [
                {"الملف": name, "الحجم MB": round(len(data) / (1024 * 1024), 2)}
                for name, data in sorted(library.items())
            ],
            hide_index=True,
            width="stretch",
        )

        remove_names = st.multiselect("حذف ملفات من المكتبة", sorted(library), key="library_remove")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("حذف المحدد", width="stretch"):
                for name in remove_names:
                    library.pop(name, None)
                _reset_library_uploader()
                st.rerun()
        with col2:
            if st.button("مسح المكتبة", width="stretch"):
                library.clear()
                _reset_library_uploader()
                st.rerun()
