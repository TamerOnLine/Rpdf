"""Streamlit UI for the exact editable workflow."""

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
    selected_pdf = _select_library_pdf("اختر ملف PDF", "exact_editable_pdf")
    pages = st.text_input(
        "الصفحات الاختيارية",
        value="",
        key="exact_editable_pages",
        help='اتركها فارغة لكل الصفحات. مثال: "1,3,5-7" أو "3;8"',
    )
    max_fields = st.number_input(
        "الحد الأقصى للحقول",
        min_value=1,
        max_value=3000,
        value=500,
        step=25,
        key="exact_editable_max_fields",
    )
    render_dpi = st.number_input(
        "دقة النسخة المطابقة",
        min_value=72,
        max_value=400,
        value=200,
        step=25,
        key="exact_editable_render_dpi",
    )
    show_field_values = st.checkbox(
        "إظهار النص المكتشف داخل الحقول",
        key="exact_editable_show_field_values",
        help="اتركه غير مفعّل حتى تبقى الصفحة طبق الأصل بصريًا.",
    )
    detect_checkboxes = st.checkbox(
        "تحويل مربعات الاختيار إلى عناصر قابلة للنقر",
        value=True,
        key="exact_editable_detect_checkboxes",
    )
    max_checkboxes = 300
    if detect_checkboxes:
        max_checkboxes = st.number_input(
            "الحد الأقصى لمربعات الاختيار",
            min_value=1,
            max_value=1000,
            value=300,
            step=25,
            key="exact_editable_max_checkboxes",
        )
    use_ocr = st.checkbox("استخدام OCR للملفات المصورة", key="exact_editable_use_ocr")
    ocr_language = "eng"
    ocr_dpi = 200
    ocr_min_confidence = 30.0
    if use_ocr:
        col1, col2, col3 = st.columns(3)
        with col1:
            ocr_language = st.text_input(
                "لغة OCR",
                value="eng",
                key="exact_editable_ocr_language",
                help='مثال: "eng" أو "ara" أو "ara+eng"',
            )
        with col2:
            ocr_dpi = st.number_input(
                "دقة OCR",
                min_value=72,
                max_value=400,
                value=250,
                step=25,
                key="exact_editable_ocr_dpi",
            )
        with col3:
            ocr_min_confidence = st.number_input(
                "أقل ثقة",
                min_value=0.0,
                max_value=100.0,
                value=25.0,
                step=5.0,
                key="exact_editable_ocr_confidence",
            )

    output_name = st.text_input(
        "اسم ملف الإخراج",
        value="exact_editable.pdf",
        key="exact_editable_output",
    )

    if st.button("توليد نسخة طبق الأصل قابلة للتعديل", width="stretch"):
        if selected_pdf is None:
            st.error("اختر ملف PDF أولًا.")
            return

        def action(tmp_dir: Path):
            source = _write_library_pdf(selected_pdf, tmp_dir / selected_pdf)
            filename = utils.safe_name(output_name, "exact_editable.pdf")
            output = tmp_dir / filename
            count = core.create_exact_editable_pdf(
                input_pdf=source,
                output_pdf=output,
                pages=utils.normalize_page_spec(pages) or None,
                max_fields=int(max_fields),
                use_ocr=use_ocr,
                ocr_language=ocr_language,
                ocr_dpi=int(ocr_dpi),
                ocr_min_confidence=float(ocr_min_confidence),
                render_dpi=int(render_dpi),
                show_field_values=show_field_values,
                detect_checkboxes=detect_checkboxes,
                max_checkboxes=int(max_checkboxes),
            )
            label = f"تم إنشاء نسخة طبق الأصل تحتوي على {count} حقل/حقول قابلة للتعديل."
            return label, filename, output.read_bytes(), "application/pdf"

        _run_pdf_action("result_exact_editable_pdf", action)
    _show_result("result_exact_editable_pdf", "download_exact_editable_pdf")
