from __future__ import annotations

import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Callable

import streamlit as st

from src import pdf_utils


def _safe_name(name: str | None, fallback: str) -> str:
    clean_name = Path(name or fallback).name
    return clean_name or fallback


def _normalize_page_spec(pages: str) -> str:
    return pages.replace("؛", ",").replace(";", ",").replace("،", ",").strip()


def _write_upload(uploaded_file, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(uploaded_file.getvalue())
    return destination


def _store_result(label: str, filename: str, data: bytes, mime: str) -> None:
    st.session_state["result"] = {
        "label": label,
        "filename": filename,
        "data": data,
        "mime": mime,
    }


def _clear_result() -> None:
    st.session_state.pop("result", None)


def _show_result(key: str) -> None:
    result = st.session_state.get("result")
    if not result:
        return

    st.success(result["label"])
    st.download_button(
        "تحميل النتيجة",
        data=result["data"],
        file_name=result["filename"],
        mime=result["mime"],
        key=key,
        type="primary",
        width="stretch",
    )


def _run_pdf_action(action: Callable[[Path], tuple[str, str, bytes, str]]) -> None:
    _clear_result()
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            label, filename, data, mime = action(Path(tmp_dir))
        _store_result(label, filename, data, mime)
    except Exception as exc:
        st.error(str(exc))


def _pdf_library() -> dict[str, bytes]:
    if "pdf_library" not in st.session_state:
        st.session_state["pdf_library"] = {}
    return st.session_state["pdf_library"]


def _add_library_uploads() -> None:
    library = _pdf_library()
    upload_key = st.session_state.get("library_upload_key", "library_uploads_0")
    for uploaded_file in st.session_state.get(upload_key, []):
        library[_safe_name(uploaded_file.name, "uploaded.pdf")] = uploaded_file.getvalue()


def _reset_library_uploader() -> None:
    st.session_state["library_upload_version"] = st.session_state.get("library_upload_version", 0) + 1
    st.session_state["library_upload_key"] = (
        f"library_uploads_{st.session_state['library_upload_version']}"
    )


def _write_library_pdf(name: str, destination: Path) -> Path:
    library = _pdf_library()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(library[name])
    return destination


def _library_names() -> list[str]:
    return sorted(_pdf_library())


def _select_library_pdf(label: str, key: str) -> str | None:
    names = _library_names()
    if not names:
        st.info("أضف ملفات PDF إلى مكتبة الملفات أولًا.")
        return None
    return st.selectbox(label, names, key=key)


def _library_panel() -> None:
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


def _xournal_tab() -> None:
    st.caption("افتح ملف PDF في Xournal++ للمعاينة أو التعديل اليدوي.")
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
                open_path = _write_library_pdf(selected_pdf, xournal_dir / selected_pdf)
            else:
                if not local_path.strip():
                    st.error("أدخل مسار ملف PDF أو أضف ملفًا إلى المكتبة أولًا.")
                    return
                open_path = Path(local_path.strip()).expanduser()
                if not open_path.exists():
                    st.error("الملف غير موجود.")
                    return

            subprocess.Popen(
                [xournal_bin, str(open_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            st.success("تم إرسال الملف إلى Xournal++.")
        except Exception as exc:
            st.error(str(exc))


def _info_tab() -> None:
    selected_pdf = _select_library_pdf("اختر ملف PDF", "info_pdf")

    if st.button("عرض المعلومات", width="stretch"):
        if selected_pdf is None:
            st.error("اختر ملف PDF أولًا.")
            return
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = _write_library_pdf(selected_pdf, Path(tmp_dir) / selected_pdf)
            try:
                info = pdf_utils.get_pdf_info(source)
            except Exception as exc:
                st.error(str(exc))
                return
        st.session_state["pdf_info"] = info

    info = st.session_state.get("pdf_info")
    if info:
        st.dataframe(
            [{"الحقل": key, "القيمة": "" if value is None else str(value)} for key, value in info.items()],
            hide_index=True,
            width="stretch",
        )


def _merge_tab() -> None:
    names = _library_names()
    selected_pdfs = st.multiselect("اختر ملفين أو أكثر من المكتبة", names, key="merge_pdfs")
    output_name = st.text_input("اسم ملف الإخراج", value="merged.pdf", key="merge_output")

    if st.button("دمج الملفات", width="stretch"):
        if len(selected_pdfs) < 2:
            st.error("اختر ملفين على الأقل.")
            return

        def action(tmp_dir: Path):
            input_paths = [
                _write_library_pdf(name, tmp_dir / f"{index}_{_safe_name(name, 'input.pdf')}")
                for index, name in enumerate(selected_pdfs, start=1)
            ]
            filename = _safe_name(output_name, "merged.pdf")
            output = tmp_dir / filename
            pdf_utils.merge_pdfs(input_paths, output)
            return "تم دمج الملفات بنجاح.", filename, output.read_bytes(), "application/pdf"

        _run_pdf_action(action)
    _show_result("download_merge")


def _extract_tab() -> None:
    selected_pdf = _select_library_pdf("اختر ملف PDF", "extract_pdf")
    pages = st.text_input("الصفحات", value="1", help='مثال: "1,3,5-7" أو "3;8"')
    output_name = st.text_input("اسم ملف الإخراج", value="extracted.pdf", key="extract_output")

    if st.button("استخراج الصفحات", width="stretch"):
        if selected_pdf is None:
            st.error("اختر ملف PDF أولًا.")
            return

        def action(tmp_dir: Path):
            source = _write_library_pdf(selected_pdf, tmp_dir / selected_pdf)
            filename = _safe_name(output_name, "extracted.pdf")
            output = tmp_dir / filename
            pdf_utils.extract_pages(source, output, _normalize_page_spec(pages))
            return "تم استخراج الصفحات بنجاح.", filename, output.read_bytes(), "application/pdf"

        _run_pdf_action(action)
    _show_result("download_extract")


def _split_tab() -> None:
    selected_pdf = _select_library_pdf("اختر ملف PDF", "split_pdf")
    zip_name = st.text_input("اسم ملف ZIP", value="split_pages.zip")

    if st.button("تقسيم الملف", width="stretch"):
        if selected_pdf is None:
            st.error("اختر ملف PDF أولًا.")
            return

        def action(tmp_dir: Path):
            source = _write_library_pdf(selected_pdf, tmp_dir / selected_pdf)
            output_dir = tmp_dir / "pages"
            filename = _safe_name(zip_name, "split_pages.zip")
            output_zip = tmp_dir / filename
            pdf_utils.split_pdf(source, output_dir)
            with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for file_path in sorted(output_dir.glob("*.pdf")):
                    zf.write(file_path, arcname=file_path.name)
            return "تم تقسيم الملف بنجاح.", filename, output_zip.read_bytes(), "application/zip"

        _run_pdf_action(action)
    _show_result("download_split")


def _rotate_tab() -> None:
    selected_pdf = _select_library_pdf("اختر ملف PDF", "rotate_pdf")
    pages = st.text_input(
        "الصفحات",
        value="1",
        key="rotate_pages",
        help='مثال: "1,3,5-7" أو "3;8"',
    )
    angle = st.selectbox("زاوية الدوران", [90, 180, 270], index=0)
    output_name = st.text_input("اسم ملف الإخراج", value="rotated.pdf", key="rotate_output")

    if st.button("تدوير الصفحات", width="stretch"):
        if selected_pdf is None:
            st.error("اختر ملف PDF أولًا.")
            return

        def action(tmp_dir: Path):
            source = _write_library_pdf(selected_pdf, tmp_dir / selected_pdf)
            filename = _safe_name(output_name, "rotated.pdf")
            output = tmp_dir / filename
            pdf_utils.rotate_pages(source, output, _normalize_page_spec(pages), int(angle))
            return "تم تدوير الصفحات بنجاح.", filename, output.read_bytes(), "application/pdf"

        _run_pdf_action(action)
    _show_result("download_rotate")


def _edit_tab() -> None:
    selected_pdf = _select_library_pdf("اختر ملف PDF", "edit_pdf")
    find_text = st.text_input("النص الحالي")
    replace_text = st.text_input("النص البديل")
    pages = st.text_input(
        "الصفحات الاختيارية",
        value="",
        help='اتركها فارغة لكل الصفحات. مثال: "1,3,5-7" أو "3;8"',
    )
    output_name = st.text_input("اسم ملف الإخراج", value="edited.pdf", key="edit_output")

    if st.button("استبدال النص", width="stretch"):
        if selected_pdf is None:
            st.error("اختر ملف PDF أولًا.")
            return

        def action(tmp_dir: Path):
            source = _write_library_pdf(selected_pdf, tmp_dir / selected_pdf)
            filename = _safe_name(output_name, "edited.pdf")
            output = tmp_dir / filename
            count = pdf_utils.replace_text_in_pdf(
                source,
                output,
                find_text,
                replace_text,
                _normalize_page_spec(pages) or None,
            )
            label = f"تم استبدال {count} موضع/مواضع بنجاح."
            return label, filename, output.read_bytes(), "application/pdf"

        _run_pdf_action(action)
    _show_result("download_edit")


def _add_text_tab() -> None:
    selected_pdf = _select_library_pdf("اختر ملف PDF", "addtext_pdf")
    font_file = st.file_uploader("خط TTF اختياري", type=["ttf"], key="addtext_font")
    st.caption("سيتم إنشاء ملف PDF جديد. بعد نجاح العملية اضغط تحميل النتيجة.")
    text = st.text_input("النص المراد إضافته", value="تمت المراجعة")
    col1, col2 = st.columns(2)
    with col1:
        page = st.number_input("رقم الصفحة", min_value=1, value=1, step=1)
        x = st.number_input("X", value=120.0, step=10.0)
    with col2:
        size = st.number_input("حجم الخط", min_value=1, value=16, step=1)
        y = st.number_input("Y", value=100.0, step=10.0)
    output_name = st.text_input("اسم ملف الإخراج", value="with_text.pdf", key="addtext_output")

    if selected_pdf is not None:
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                source = _write_library_pdf(selected_pdf, Path(tmp_dir) / selected_pdf)
                page_width, page_height = pdf_utils.get_page_size(source, int(page))
            st.caption(
                f"حجم الصفحة {int(page)}: {page_width:.0f} x {page_height:.0f}. "
                "الإحداثيات تبدأ من أسفل يسار الصفحة."
            )
        except Exception as exc:
            st.caption(str(exc))

    if st.button("إضافة النص", width="stretch"):
        if selected_pdf is None:
            st.error("اختر ملف PDF أولًا.")
            return

        def action(tmp_dir: Path):
            source = _write_library_pdf(selected_pdf, tmp_dir / selected_pdf)
            font_path = None
            if font_file is not None:
                font_path = str(_write_upload(font_file, tmp_dir / "font.ttf"))
            filename = _safe_name(output_name, "with_text.pdf")
            output = tmp_dir / filename
            pdf_utils.add_text_overlay(
                source,
                output,
                int(page),
                text,
                float(x),
                float(y),
                int(size),
                font_path,
            )
            return "تم إنشاء ملف جديد يحتوي على النص. اضغط تحميل النتيجة.", filename, output.read_bytes(), "application/pdf"

        _run_pdf_action(action)
    _show_result("download_add_text")


def _insert_tab() -> None:
    base_pdf = _select_library_pdf("ملف PDF الأساسي", "insert_base")
    inserted_pdf = _select_library_pdf("ملف PDF المراد إدراجه", "insert_file")
    after_page = st.number_input("الإدراج بعد الصفحة", min_value=0, value=1, step=1)
    output_name = st.text_input("اسم ملف الإخراج", value="inserted.pdf", key="insert_output")

    if st.button("إدراج الملف", width="stretch"):
        if not base_pdf or not inserted_pdf:
            st.error("اختر الملف الأساسي وملف الإدراج.")
            return

        def action(tmp_dir: Path):
            source = _write_library_pdf(base_pdf, tmp_dir / f"base_{_safe_name(base_pdf, 'base.pdf')}")
            insert_source = _write_library_pdf(
                inserted_pdf,
                tmp_dir / f"insert_{_safe_name(inserted_pdf, 'insert.pdf')}",
            )
            filename = _safe_name(output_name, "inserted.pdf")
            output = tmp_dir / filename
            pdf_utils.insert_pdf_after_page(source, insert_source, output, int(after_page))
            return "تم إدراج الملف بنجاح.", filename, output.read_bytes(), "application/pdf"

        _run_pdf_action(action)
    _show_result("download_insert")


def main() -> None:
    st.set_page_config(page_title="PDF Control", page_icon="📄", layout="wide")
    st.title("PDF Control")
    st.caption("واجهة Streamlit للتحكم بملفات PDF")
    _library_panel()

    tabs = st.tabs(
        [
            "Xournal++",
            "معلومات",
            "دمج",
            "استخراج",
            "تقسيم",
            "تدوير",
            "استبدال نص",
            "إضافة نص",
            "إدراج",
        ]
    )

    with tabs[0]:
        _xournal_tab()
    with tabs[1]:
        _info_tab()
    with tabs[2]:
        _merge_tab()
    with tabs[3]:
        _extract_tab()
    with tabs[4]:
        _split_tab()
    with tabs[5]:
        _rotate_tab()
    with tabs[6]:
        _edit_tab()
    with tabs[7]:
        _add_text_tab()
    with tabs[8]:
        _insert_tab()


if __name__ == "__main__":
    main()
