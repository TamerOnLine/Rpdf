import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from reportlab.pdfbase.ttfonts import TTFError

from src import pdf_utils


def _make_pdf(path: Path, pages: int) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=300, height=400)
    with path.open("wb") as f:
        writer.write(f)


def _make_text_pdf(path: Path, text: str) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=400)

    content = f"BT /F1 12 Tf 20 200 Td ({text}) Tj ET".encode("latin-1")
    from pypdf.generic import DecodedStreamObject

    stream = DecodedStreamObject()
    stream.set_data(content)
    stream_ref = writer._add_object(stream)
    page[NameObject("/Contents")] = stream_ref

    with path.open("wb") as f:
        writer.write(f)


class PdfUtilsAllTests(unittest.TestCase):
    def test_parse_page_spec_empty_and_invalid_tokens(self) -> None:
        with self.assertRaises(ValueError):
            pdf_utils._parse_page_spec("   ", 3)
        with self.assertRaises(ValueError):
            pdf_utils._parse_page_spec("a", 3)
        with self.assertRaises(ValueError):
            pdf_utils._parse_page_spec("0", 3)
        with self.assertRaises(ValueError):
            pdf_utils._parse_page_spec("4", 3)
        with self.assertRaises(ValueError):
            pdf_utils._parse_page_spec("1-", 3)

    def test_parse_page_spec_skips_empty_tokens(self) -> None:
        result = pdf_utils._parse_page_spec("1,,2", 3)
        self.assertEqual(result, [0, 1])

    def test_shape_arabic_text_fallback_without_optional_deps(self) -> None:
        with patch("src.pdf_utils.arabic_reshaper", None), patch("src.pdf_utils.get_display", None):
            self.assertEqual(pdf_utils._shape_arabic_text("abc"), "abc")

    def test_get_pdf_info(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.pdf"
            _make_pdf(path, 3)
            info = pdf_utils.get_pdf_info(path)
            self.assertEqual(info["pages"], 3)
            self.assertIn("encrypted", info)

    def test_merge_pdfs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            a = d / "a.pdf"
            b = d / "b.pdf"
            out = d / "out.pdf"
            _make_pdf(a, 2)
            _make_pdf(b, 1)
            pdf_utils.merge_pdfs([a, b], out)
            self.assertEqual(len(PdfReader(str(out)).pages), 3)

    def test_extract_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "src.pdf"
            out = d / "out.pdf"
            _make_pdf(src, 5)
            pdf_utils.extract_pages(src, out, "1,3,5")
            self.assertEqual(len(PdfReader(str(out)).pages), 3)

    def test_extract_pages_rejects_invalid_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "src.pdf"
            out = d / "out.pdf"
            _make_pdf(src, 2)
            with self.assertRaises(ValueError):
                pdf_utils.extract_pages(src, out, "2-1")

    def test_split_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "src.pdf"
            out_dir = d / "parts"
            _make_pdf(src, 4)
            pdf_utils.split_pdf(src, out_dir)
            parts = sorted(out_dir.glob("*.pdf"))
            self.assertEqual(len(parts), 4)

    def test_rotate_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "src.pdf"
            out = d / "rot.pdf"
            _make_pdf(src, 3)
            pdf_utils.rotate_pages(src, out, "2", 90)
            reader = PdfReader(str(out))
            self.assertEqual(int(reader.pages[1].get("/Rotate", 0)), 90)

    def test_rotate_pages_rejects_invalid_angle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "src.pdf"
            out = d / "rot.pdf"
            _make_pdf(src, 2)
            with self.assertRaises(ValueError):
                pdf_utils.rotate_pages(src, out, "1", 45)

    def test_insert_pdf_after_page_negative_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            base = d / "base.pdf"
            ins = d / "ins.pdf"
            out = d / "out.pdf"
            _make_pdf(base, 2)
            _make_pdf(ins, 1)
            with self.assertRaises(ValueError):
                pdf_utils.insert_pdf_after_page(base, ins, out, after_page=-1)

    def test_replace_text_in_pdf_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "src.pdf"
            out = d / "out.pdf"
            _make_text_pdf(src, "Hello Hello")
            replaced = pdf_utils.replace_text_in_pdf(src, out, "Hello", "Hi")
            self.assertEqual(replaced, 2)

    def test_replace_text_in_pdf_requires_find_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "src.pdf"
            out = d / "out.pdf"
            _make_text_pdf(src, "Hello")
            with self.assertRaises(ValueError):
                pdf_utils.replace_text_in_pdf(src, out, "", "Hi")

    def test_replace_text_in_pdf_raises_when_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "src.pdf"
            out = d / "out.pdf"
            _make_text_pdf(src, "Hello")
            with self.assertRaises(ValueError):
                pdf_utils.replace_text_in_pdf(src, out, "XYZ", "Hi")

    def test_add_text_overlay_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "src.pdf"
            out = d / "out.pdf"
            _make_pdf(src, 2)
            pdf_utils.add_text_overlay(
                src, out, page_number=1, text="stamp", x=10, y=10, font_size=12
            )
            self.assertEqual(len(PdfReader(str(out)).pages), 2)

    def test_add_text_overlay_rejects_invalid_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "src.pdf"
            out = d / "out.pdf"
            _make_pdf(src, 1)
            with self.assertRaises(ValueError):
                pdf_utils.add_text_overlay(src, out, page_number=0, text="stamp", x=10, y=10)

    def test_add_text_overlay_rejects_empty_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "src.pdf"
            out = d / "out.pdf"
            _make_pdf(src, 1)
            with self.assertRaises(ValueError):
                pdf_utils.add_text_overlay(src, out, page_number=1, text="", x=10, y=10)

    def test_add_text_overlay_rejects_page_out_of_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "src.pdf"
            out = d / "out.pdf"
            _make_pdf(src, 1)
            with self.assertRaises(ValueError):
                pdf_utils.add_text_overlay(src, out, page_number=2, text="stamp", x=10, y=10)

    def test_add_text_overlay_custom_font_invalid_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            src = d / "src.pdf"
            out = d / "out.pdf"
            _make_pdf(src, 1)
            with self.assertRaises((OSError, TTFError, ValueError)):
                pdf_utils.add_text_overlay(
                    src,
                    out,
                    page_number=1,
                    text="stamp",
                    x=10,
                    y=10,
                    font_path=str(d / "missing.ttf"),
                )


if __name__ == "__main__":
    unittest.main()
