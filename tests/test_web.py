from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from pdf_control import utils, web


class WebUtilityTests(unittest.TestCase):
    def test_normalize_page_spec_accepts_arabic_and_semicolon_separators(self) -> None:
        self.assertEqual(utils.normalize_page_spec("1؛3،5;7"), "1,3,5,7")

    def test_pdf_data_uri_encodes_pdf_bytes(self) -> None:
        self.assertEqual(web._pdf_data_uri(b"%PDF"), "data:application/pdf;base64,JVBERg==")

    def test_unique_xournal_pdf_path_avoids_stale_matching_xopp_names(self) -> None:
        with patch("pdf_control.web.uuid.uuid4") as uuid4:
            uuid4.return_value.hex = "abc123def4567890"

            path = web._unique_xournal_pdf_path("merged.pdf", Path("/tmp/xournal"))

        self.assertEqual(path, Path("/tmp/xournal/merged-abc123def456.pdf"))

    def test_open_xournal_can_start_without_pdf_path(self) -> None:
        with patch("pdf_control.web.subprocess.Popen") as popen:
            web._open_xournal("/usr/bin/xournalpp")

        popen.assert_called_once_with(
            ["/usr/bin/xournalpp"],
            stdout=web.subprocess.DEVNULL,
            stderr=web.subprocess.DEVNULL,
            start_new_session=True,
        )

    def test_safe_name_strips_path_components(self) -> None:
        self.assertEqual(utils.safe_name("../unsafe.pdf", "fallback.pdf"), "unsafe.pdf")

    def test_unique_library_name_keeps_different_files_with_same_name(self) -> None:
        library = {"report.pdf": b"first"}

        self.assertEqual(
            web._unique_library_name("report.pdf", b"second", library),
            "report (2).pdf",
        )

    def test_unique_library_name_reuses_identical_upload(self) -> None:
        library = {"report.pdf": b"same"}

        self.assertEqual(web._unique_library_name("report.pdf", b"same", library), "report.pdf")


if __name__ == "__main__":
    unittest.main()
