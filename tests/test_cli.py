from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from pdf_control.cli import _is_wsl, _open_browser, build_parser


class CliTests(unittest.TestCase):
    def test_cli_parser_accepts_port_and_upload_size(self) -> None:
        args = build_parser().parse_args(["--port", "8080", "--max-upload-size", "2048"])

        self.assertEqual(args.port, 8080)
        self.assertEqual(args.max_upload_size, 2048)

    def test_wsl_detection_uses_kernel_release(self) -> None:
        with patch.object(Path, "read_text", return_value="5.15.0-microsoft-standard-WSL2"):
            self.assertTrue(_is_wsl())

    @patch("pdf_control.cli._is_wsl", return_value=True)
    @patch("pdf_control.cli.shutil.which", return_value="/usr/bin/powershell.exe")
    @patch("pdf_control.cli.subprocess.Popen")
    def test_browser_uses_windows_powershell_in_wsl(self, popen, _which, _wsl) -> None:
        _open_browser("http://localhost:8000")

        command = popen.call_args.args[0]
        self.assertEqual(command[-2:], ["Start-Process", "http://localhost:8000"])


if __name__ == "__main__":
    unittest.main()
