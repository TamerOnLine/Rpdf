import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _make_pdf(path: Path, pages: int) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=300, height=400)
    with path.open("wb") as f:
        writer.write(f)


class CliTests(unittest.TestCase):
    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "src.main", *args],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_info_command_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "input.pdf"
            _make_pdf(pdf_path, 2)

            result = self._run_cli("info", str(pdf_path))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("'pages': 2", result.stdout)

    def test_help_lists_english_gui_command(self) -> None:
        result = self._run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("gui-en", result.stdout)

    def test_gui_command_accepts_language_flag(self) -> None:
        result = self._run_cli("gui", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--lang", result.stdout)

    def test_merge_command_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            first = tmp_dir / "first.pdf"
            second = tmp_dir / "second.pdf"
            output = tmp_dir / "merged.pdf"
            _make_pdf(first, 1)
            _make_pdf(second, 2)

            result = self._run_cli("merge", str(output), str(first), str(second))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(PdfReader(str(output)).pages), 3)
            self.assertIn("Merged 2 files", result.stdout)

    def test_insert_command_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            base = tmp_dir / "base.pdf"
            insert_pdf = tmp_dir / "insert.pdf"
            output = tmp_dir / "inserted.pdf"
            _make_pdf(base, 2)
            _make_pdf(insert_pdf, 1)

            result = self._run_cli(
                "insert",
                str(base),
                str(insert_pdf),
                str(output),
                "--after-page",
                "1",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(PdfReader(str(output)).pages), 3)
            self.assertIn("Inserted", result.stdout)

    def test_insert_command_invalid_after_page_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            base = tmp_dir / "base.pdf"
            insert_pdf = tmp_dir / "insert.pdf"
            output = tmp_dir / "inserted.pdf"
            _make_pdf(base, 2)
            _make_pdf(insert_pdf, 1)

            result = self._run_cli(
                "insert",
                str(base),
                str(insert_pdf),
                str(output),
                "--after-page",
                "9",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exceeds document page count", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
