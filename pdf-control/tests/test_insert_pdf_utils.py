import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from src import pdf_utils


def _make_pdf(path: Path, pages: int) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=300, height=400)
    with path.open("wb") as f:
        writer.write(f)


class InsertPdfUtilsTests(unittest.TestCase):
    def test_insert_at_beginning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            base = tmp_dir / "base.pdf"
            ins = tmp_dir / "ins.pdf"
            out = tmp_dir / "out.pdf"

            _make_pdf(base, 2)
            _make_pdf(ins, 1)

            pdf_utils.insert_pdf_after_page(base, ins, out, after_page=0)

            reader = PdfReader(str(out))
            self.assertEqual(len(reader.pages), 3)

    def test_insert_after_middle_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            base = tmp_dir / "base.pdf"
            ins = tmp_dir / "ins.pdf"
            out = tmp_dir / "out.pdf"

            _make_pdf(base, 4)
            _make_pdf(ins, 2)

            pdf_utils.insert_pdf_after_page(base, ins, out, after_page=2)

            reader = PdfReader(str(out))
            self.assertEqual(len(reader.pages), 6)

    def test_insert_rejects_invalid_after_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            base = tmp_dir / "base.pdf"
            ins = tmp_dir / "ins.pdf"
            out = tmp_dir / "out.pdf"

            _make_pdf(base, 2)
            _make_pdf(ins, 1)

            with self.assertRaises(ValueError):
                pdf_utils.insert_pdf_after_page(base, ins, out, after_page=3)


if __name__ == "__main__":
    unittest.main()
