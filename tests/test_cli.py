from __future__ import annotations

import unittest

from pdf_control.cli import build_parser


class CliTests(unittest.TestCase):
    def test_cli_parser_accepts_port_and_upload_size(self) -> None:
        args = build_parser().parse_args(["--port", "8080", "--max-upload-size", "2048"])

        self.assertEqual(args.port, 8080)
        self.assertEqual(args.max_upload_size, 2048)


if __name__ == "__main__":
    unittest.main()
