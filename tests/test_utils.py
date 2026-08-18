from __future__ import annotations

import unittest

from pdf_control import utils


class UtilityTests(unittest.TestCase):
    def test_normalize_page_spec_accepts_arabic_and_semicolon_separators(self) -> None:
        self.assertEqual(utils.normalize_page_spec("1؛3،5;7"), "1,3,5,7")

    def test_safe_name_strips_path_components(self) -> None:
        self.assertEqual(utils.safe_name("../unsafe.pdf", "fallback.pdf"), "unsafe.pdf")


if __name__ == "__main__":
    unittest.main()
