from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from pdf_control import config


class ConfigTests(unittest.TestCase):
    def test_default_port_reads_environment_value(self) -> None:
        with patch.dict(os.environ, {"PORT": "8080"}):
            self.assertEqual(config.default_port(), 8080)

    def test_default_port_rejects_non_integer_value(self) -> None:
        with patch.dict(os.environ, {"PORT": "abc"}):
            with self.assertRaisesRegex(ValueError, "PORT must be an integer"):
                config.default_port()

    def test_default_port_rejects_out_of_range_value(self) -> None:
        with patch.dict(os.environ, {"PORT": "70000"}):
            with self.assertRaisesRegex(ValueError, "PORT must be between"):
                config.default_port()

if __name__ == "__main__":
    unittest.main()
