"""PDF-splitting tab UI."""

import zipfile
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
    selected = _select_library_pdf("اختر ملف PDF", "split_pdf")
    zip_name = st.text_input("اسم ملف ZIP", value="split_pages.zip")
    if st.button("تقسيم الملف", width="stretch"):
        if selected is None:
            st.error("اختر ملف PDF أولًا.")
            return

        def action(tmp_dir: Path):
            source = _write_library_pdf(selected, tmp_dir / selected)
            output_dir = tmp_dir / "pages"
            filename = utils.safe_name(zip_name, "split_pages.zip")
            output_zip = tmp_dir / filename
            core.split_pdf(source, output_dir)
            with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for file_path in sorted(output_dir.glob("*.pdf")):
                    archive.write(file_path, arcname=file_path.name)
            return "تم تقسيم الملف بنجاح.", filename, output_zip.read_bytes(), "application/zip"

        _run_pdf_action("result_split", action)
    _show_result("result_split", "download_split")
