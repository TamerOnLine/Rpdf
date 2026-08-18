from __future__ import annotations

import os

APP_NAME = "PDF Control"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_MAX_FILE_SIZE_MB = 256
DEFAULT_MAX_SESSION_SIZE_MB = 512
DEFAULT_MAX_PDF_PAGES = 2000
DEFAULT_MAX_RENDER_PAGES = 250


def _read_positive_int_env(name: str, default: int | None = None) -> int | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default

    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc

    if parsed < 1:
        raise ValueError(f"{name} must be greater than 0.")
    return parsed


def default_port() -> int | None:
    port = _read_positive_int_env("PORT")
    if port is not None and port > 65535:
        raise ValueError("PORT must be between 1 and 65535.")
    return port


def max_file_size_mb() -> int:
    return int(_read_positive_int_env("PDF_CONTROL_MAX_FILE_SIZE_MB", DEFAULT_MAX_FILE_SIZE_MB))


def max_session_size_mb() -> int:
    return int(
        _read_positive_int_env("PDF_CONTROL_MAX_SESSION_SIZE_MB", DEFAULT_MAX_SESSION_SIZE_MB)
    )


def max_pdf_pages() -> int:
    return int(_read_positive_int_env("PDF_CONTROL_MAX_PAGES", DEFAULT_MAX_PDF_PAGES))


def max_render_pages() -> int:
    return int(_read_positive_int_env("PDF_CONTROL_MAX_RENDER_PAGES", DEFAULT_MAX_RENDER_PAGES))
