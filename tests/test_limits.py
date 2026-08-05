from __future__ import annotations

from unittest.mock import patch

import pytest

from pdf_control import limits


def test_upload_limit_rejects_a_single_oversized_file() -> None:
    with patch("pdf_control.config.max_file_size_mb", return_value=1):
        with pytest.raises(ValueError, match="الملف"):
            limits.validate_upload(b"x" * (limits.MIB + 1))


def test_upload_limit_rejects_session_memory_growth() -> None:
    with patch("pdf_control.config.max_session_size_mb", return_value=1):
        with pytest.raises(ValueError, match="الجلسة"):
            limits.validate_upload(b"x" * 10, current_session_bytes=limits.MIB)


def test_render_page_limit_is_separate_from_processing_limit() -> None:
    with patch("pdf_control.config.max_render_pages", return_value=2):
        with pytest.raises(ValueError, match="rendering limit"):
            limits.validate_page_count(3, rendering=True)
