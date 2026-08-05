"""Shared Streamlit session, result, and local-application helpers."""

from __future__ import annotations

import base64
import subprocess
import tempfile
import uuid
from collections.abc import Callable
from pathlib import Path

import streamlit as st

from pdf_control import limits, utils
from pdf_control.models import PdfResult


def _write_upload(uploaded_file, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(uploaded_file.getvalue())
    return destination


def _pdf_data_uri(data: bytes) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:application/pdf;base64,{encoded}"


def _unique_xournal_pdf_path(name: str, root: Path) -> Path:
    safe_name = utils.safe_name(name, "uploaded.pdf")
    path = Path(safe_name)
    suffix = path.suffix or ".pdf"
    stem = path.stem or "uploaded"
    return root / f"{stem}-{uuid.uuid4().hex[:12]}{suffix}"


def _open_xournal(xournal_bin: str, open_path: Path | None = None) -> None:
    command = [xournal_bin]
    if open_path is not None:
        command.append(str(open_path))
    subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _store_result(result_key: str, label: str, filename: str, data: bytes, mime: str) -> None:
    library_bytes = sum(len(value) for value in _pdf_library().values())
    limits.validate_upload(data, library_bytes)
    st.session_state[result_key] = PdfResult(label=label, filename=filename, data=data, mime=mime)


def _clear_result(result_key: str) -> None:
    st.session_state.pop(result_key, None)


def _show_result(result_key: str, download_key: str) -> None:
    result = st.session_state.get(result_key)
    if not result:
        return

    st.success(result.label)
    st.download_button(
        "تحميل النتيجة",
        data=result.data,
        file_name=result.filename,
        mime=result.mime,
        key=download_key,
        type="primary",
        width="stretch",
    )


def _run_pdf_action(
    result_key: str,
    action: Callable[[Path], tuple[str, str, bytes, str]],
) -> None:
    _clear_result(result_key)
    status = st.status("تهيئة الملفات…", expanded=False)
    try:
        status.update(label="جارٍ معالجة ملف PDF…", state="running")
        with tempfile.TemporaryDirectory() as tmp_dir:
            label, filename, data, mime = action(Path(tmp_dir))
        status.update(label="اكتملت المعالجة، جارٍ تجهيز التنزيل…", state="running")
        _store_result(result_key, label, filename, data, mime)
        status.update(label="اكتملت العملية", state="complete")
    except Exception as exc:
        status.update(label="تعذّر إكمال العملية", state="error")
        st.error(str(exc))


def _pdf_library() -> dict[str, bytes]:
    if "pdf_library" not in st.session_state:
        st.session_state["pdf_library"] = {}
    return st.session_state["pdf_library"]


def _unique_library_name(name: str, data: bytes, library: dict[str, bytes]) -> str:
    if name not in library or library[name] == data:
        return name

    path = Path(name)
    suffix = path.suffix
    stem = path.name[: -len(suffix)] if suffix else path.name
    stem = stem or "uploaded"

    counter = 2
    while True:
        candidate = f"{stem} ({counter}){suffix}"
        if candidate not in library or library[candidate] == data:
            return candidate
        counter += 1


def _add_library_uploads() -> None:
    library = _pdf_library()
    upload_key = st.session_state.get("library_upload_key", "library_uploads_0")
    for uploaded_file in st.session_state.get(upload_key, []):
        data = uploaded_file.getvalue()
        name = utils.safe_name(uploaded_file.name, "uploaded.pdf")
        target_name = _unique_library_name(name, data, library)
        if target_name in library and library[target_name] == data:
            continue
        try:
            limits.validate_upload(data, sum(len(value) for value in library.values()))
        except ValueError as exc:
            st.error(f"{name}: {exc}")
            continue
        library[target_name] = data


def _reset_library_uploader() -> None:
    st.session_state["library_upload_version"] = (
        st.session_state.get("library_upload_version", 0) + 1
    )
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
