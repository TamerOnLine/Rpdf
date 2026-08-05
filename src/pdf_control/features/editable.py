"""Streamlit UI for the editable workflow."""

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
    selected_pdf = _select_library_pdf("اختر ملف PDF", "editable_pdf")
    pages = st.text_input(
        "الصفحات الاختيارية",
        value="",
        key="editable_pages",
        help='اتركها فارغة لكل الصفحات. مثال: "1,3,5-7" أو "3;8"',
    )
    max_fields = st.number_input(
        "الحد الأقصى للحقول",
        min_value=1,
        max_value=2000,
        value=300,
        step=25,
    )
    show_field_values = st.checkbox(
        "إظهار النص المكتشف داخل الحقول",
        key="editable_show_field_values",
        help="اتركه غير مفعّل للحفاظ على شكل الصفحة الأصلي بدون صناديق نص ظاهرة.",
    )
    use_ocr = st.checkbox("استخدام OCR للملفات المصورة", key="editable_use_ocr")
    ocr_language = "eng"
    ocr_dpi = 200
    ocr_min_confidence = 30.0
    if use_ocr:
        col1, col2, col3 = st.columns(3)
        with col1:
            ocr_language = st.text_input(
                "لغة OCR",
                value="eng",
                key="editable_ocr_language",
                help='مثال: "eng" أو "ara" أو "ara+eng"',
            )
        with col2:
            ocr_dpi = st.number_input(
                "دقة OCR",
                min_value=72,
                max_value=400,
                value=200,
                step=25,
            )
        with col3:
            ocr_min_confidence = st.number_input(
                "أقل ثقة",
                min_value=0.0,
                max_value=100.0,
                value=30.0,
                step=5.0,
            )

    output_name = st.text_input(
        "اسم ملف الإخراج",
        value="editable.pdf",
        key="editable_output",
    )

    if st.button("توليد نسخة قابلة للتعديل", width="stretch"):
        if selected_pdf is None:
            st.error("اختر ملف PDF أولًا.")
            return

        def action(tmp_dir: Path):
            source = _write_library_pdf(selected_pdf, tmp_dir / selected_pdf)
            filename = utils.safe_name(output_name, "editable.pdf")
            output = tmp_dir / filename
            count = core.create_editable_pdf(
                input_pdf=source,
                output_pdf=output,
                pages=utils.normalize_page_spec(pages) or None,
                max_fields=int(max_fields),
                use_ocr=use_ocr,
                ocr_language=ocr_language,
                ocr_dpi=int(ocr_dpi),
                ocr_min_confidence=float(ocr_min_confidence),
                show_field_values=show_field_values,
            )
            label = f"تم إنشاء نسخة قابلة للتعديل تحتوي على {count} حقل/حقول."
            return label, filename, output.read_bytes(), "application/pdf"

        _run_pdf_action("result_editable_pdf", action)
    _show_result("result_editable_pdf", "download_editable_pdf")
