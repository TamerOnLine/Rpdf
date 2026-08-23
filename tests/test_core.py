from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from pdf_control import _engine, core


class _FakeImage:
    size = (200, 100)


class _FakeImageModule:
    @staticmethod
    def open(buffer):
        del buffer
        return _FakeImage()


class _FakePixmap:
    def tobytes(self, image_format):
        del image_format
        return b"fake-png"


class _FakeFitzPage:
    def get_pixmap(self, dpi, alpha):
        del dpi, alpha
        return _FakePixmap()


class _FakeFitzDocument:
    page_count = 1

    def load_page(self, page_index):
        del page_index
        return _FakeFitzPage()

    def close(self):
        return None


class _FakeFitz:
    @staticmethod
    def open(path):
        del path
        return _FakeFitzDocument()


class _FakePytesseract:
    class Output:
        DICT = "dict"

    @staticmethod
    def image_to_data(image, lang, output_type):
        del image, lang, output_type
        return {
            "text": ["Hello", "World"],
            "conf": ["96", "93"],
            "left": [20, 82],
            "top": [10, 10],
            "width": [50, 55],
            "height": [12, 12],
            "block_num": [1, 1],
            "par_num": [1, 1],
            "line_num": [1, 1],
        }


def _fake_render_pdf_as_image_background(input_pdf, output_buffer, dpi) -> None:
    del input_pdf, dpi
    pdf = canvas.Canvas(output_buffer, pagesize=(612, 792))
    pdf.showPage()
    pdf.save()


class PageSpecTests(unittest.TestCase):
    def test_parse_page_spec_accepts_single_pages_and_ranges(self) -> None:
        self.assertEqual(core._parse_page_spec("1,3,5-7", 10), [0, 2, 4, 5, 6])

    def test_parse_page_spec_accepts_all_pages_aliases(self) -> None:
        self.assertEqual(core._parse_page_spec("الكل", 3), [0, 1, 2])
        self.assertEqual(core._parse_page_spec("all", 2), [0, 1])
        self.assertEqual(core._parse_page_spec("*", 1), [0])

    def test_parse_page_spec_deduplicates_and_sorts(self) -> None:
        self.assertEqual(core._parse_page_spec("3,1,3", 5), [0, 2])

    def test_parse_page_spec_rejects_out_of_range_page(self) -> None:
        with self.assertRaisesRegex(ValueError, "exceeds document page count"):
            core._parse_page_spec("4", 3)

    def test_rotate_pages_rejects_invalid_angle(self) -> None:
        with self.assertRaisesRegex(ValueError, "Angle must be one of"):
            core.rotate_pages(self._input_pdf(), self._output_pdf(), "1", 45)

    def _input_pdf(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        tmp_dir = TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        path = Path(tmp_dir.name) / "input.pdf"
        path.write_bytes(b"%PDF-1.4\n")
        return path

    def _output_pdf(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        tmp_dir = TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        return Path(tmp_dir.name) / "output.pdf"


class CorePdfOperationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.root = Path(self.tmp_dir.name)

    def _make_pdf(self, name: str, lines: list[str]) -> Path:
        path = self.root / name
        pdf = canvas.Canvas(str(path))
        for line in lines:
            pdf.drawString(72, 720, line)
            pdf.showPage()
        pdf.save()
        return path

    def _encrypt_pdf(self, source: Path) -> Path:
        reader = PdfReader(str(source))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt("secret")

        encrypted = self.root / "encrypted.pdf"
        with encrypted.open("wb") as file:
            writer.write(file)
        return encrypted

    def test_merge_pdfs_combines_all_pages(self) -> None:
        first = self._make_pdf("first.pdf", ["first page", "second page"])
        second = self._make_pdf("second.pdf", ["third page"])
        output = self.root / "merged.pdf"

        core.merge_pdfs([first, second], output)

        self.assertEqual(len(PdfReader(str(output)).pages), 3)

    def test_extract_pages_writes_selected_pages(self) -> None:
        source = self._make_pdf("source.pdf", ["one", "two", "three"])
        output = self.root / "extracted.pdf"

        core.extract_pages(source, output, "2-3")

        reader = PdfReader(str(output))
        self.assertEqual(len(reader.pages), 2)
        self.assertIn("two", reader.pages[0].extract_text())

    def test_extract_pages_accepts_all_alias(self) -> None:
        source = self._make_pdf("source.pdf", ["one", "two", "three"])
        output = self.root / "all_pages.pdf"

        core.extract_pages(source, output, "all")

        self.assertEqual(len(PdfReader(str(output)).pages), 3)

    def test_split_pdf_writes_one_file_per_page(self) -> None:
        source = self._make_pdf("source.pdf", ["one", "two"])
        output_dir = self.root / "pages"

        core.split_pdf(source, output_dir)

        outputs = sorted(output_dir.glob("*.pdf"))
        self.assertEqual(
            [path.name for path in outputs], ["source_page_001.pdf", "source_page_002.pdf"]
        )
        self.assertEqual(len(PdfReader(str(outputs[0])).pages), 1)

    def test_rotate_pages_updates_selected_page_rotation(self) -> None:
        source = self._make_pdf("source.pdf", ["one", "two"])
        output = self.root / "rotated.pdf"

        core.rotate_pages(source, output, "1", 90)

        reader = PdfReader(str(output))
        self.assertEqual(reader.pages[0].get("/Rotate"), 90)
        self.assertIn(reader.pages[1].get("/Rotate"), (None, 0))

    def test_insert_pdf_after_page_places_inserted_document(self) -> None:
        base = self._make_pdf("base.pdf", ["base one", "base two"])
        insert = self._make_pdf("insert.pdf", ["inserted"])
        output = self.root / "inserted.pdf"

        core.insert_pdf_after_page(base, insert, output, after_page=1)

        reader = PdfReader(str(output))
        self.assertEqual(len(reader.pages), 3)
        self.assertIn("inserted", reader.pages[1].extract_text())

    def test_replace_text_in_pdf_updates_text_layer(self) -> None:
        source = self._make_pdf("source.pdf", ["hello world"])
        output = self.root / "replaced.pdf"

        count = core.replace_text_in_pdf(source, output, "hello", "bye")

        self.assertEqual(count, 1)
        self.assertIn("bye world", PdfReader(str(output)).pages[0].extract_text())

    def test_add_text_overlay_keeps_document_readable(self) -> None:
        source = self._make_pdf("source.pdf", ["base"])
        output = self.root / "overlay.pdf"

        core.add_text_overlay(source, output, 1, "Reviewed", 120, 120, 14)

        reader = PdfReader(str(output))
        self.assertEqual(len(reader.pages), 1)
        self.assertIn("Reviewed", reader.pages[0].extract_text())

    def test_visual_layers_preserve_original_text_and_add_new_text(self) -> None:
        source = self._make_pdf("source.pdf", ["original content"])
        output = self.root / "layered.pdf"
        edits = json.dumps(
            [
                {"type": "mask", "page": 1, "x": 65, "y": 60, "width": 150, "height": 24},
                {
                    "type": "text",
                    "page": 1,
                    "x": 65,
                    "y": 60,
                    "width": 180,
                    "height": 35,
                    "text": "New content",
                    "fontSize": 12,
                    "color": "#111111",
                    "align": "left",
                },
            ]
        )

        count = core.apply_visual_layers(source, output, edits)

        extracted = PdfReader(str(output)).pages[0].extract_text()
        self.assertEqual(count, 2)
        self.assertIn("original content", extracted)
        self.assertIn("New content", extracted)

    def test_visual_layers_reject_out_of_range_page(self) -> None:
        source = self._make_pdf("source.pdf", ["original content"])
        edits = json.dumps([{"type": "mask", "page": 2, "x": 1, "y": 1, "width": 10, "height": 10}])

        with self.assertRaisesRegex(ValueError, "الصفحة"):
            core.apply_visual_layers(source, self.root / "layered.pdf", edits)

    def test_visual_layers_can_delete_original_pages(self) -> None:
        source = self._make_pdf("source.pdf", ["first", "second", "third"])
        output = self.root / "pages_deleted.pdf"

        count = core.apply_visual_layers(source, output, "[]", None, "[2]")

        reader = PdfReader(str(output))
        self.assertEqual(count, 0)
        self.assertEqual(len(reader.pages), 2)
        self.assertIn("first", reader.pages[0].extract_text())
        self.assertIn("third", reader.pages[1].extract_text())

    def test_visual_layer_accepts_compact_default_text_box(self) -> None:
        source = self._make_pdf("source.pdf", ["original content"])
        output = self.root / "compact_text.pdf"
        edits = json.dumps(
            [
                {
                    "type": "text",
                    "page": 1,
                    "x": 65,
                    "y": 60,
                    "width": 70,
                    "height": 16,
                    "text": "نص جديد",
                    "fontSize": 14,
                    "color": "#4b2fd3",
                    "align": "center",
                    "verticalAlign": "middle",
                }
            ]
        )

        count = core.apply_visual_layers(source, output, edits)

        self.assertEqual(count, 1)
        self.assertTrue(output.exists())

    def test_visual_layer_shrinks_long_text_to_fit_compact_box(self) -> None:
        source = self._make_pdf("source.pdf", ["original content"])
        output = self.root / "fitted_text.pdf"
        edits = json.dumps(
            [
                {
                    "type": "text",
                    "page": 1,
                    "x": 65,
                    "y": 60,
                    "width": 70,
                    "height": 16,
                    "text": "SAL-0459-LONG",
                    "fontSize": 14,
                    "color": "#4b2fd3",
                    "align": "center",
                    "verticalAlign": "middle",
                }
            ]
        )

        count = core.apply_visual_layers(source, output, edits)

        self.assertEqual(count, 1)
        self.assertTrue(output.exists())
        self.assertEqual(PdfReader(str(output)).pages[0].extract_text().count("SAL-0459-LONG"), 1)

    def test_visual_layers_refuse_to_delete_every_page(self) -> None:
        source = self._make_pdf("source.pdf", ["first", "second"])

        with self.assertRaisesRegex(ValueError, "جميع صفحات"):
            core.apply_visual_layers(source, self.root / "pages_deleted.pdf", "[]", None, "[1, 2]")

    def test_create_editable_pdf_adds_form_fields_for_text_layer(self) -> None:
        source = self._make_pdf("source.pdf", ["first line", "second line"])
        output = self.root / "editable.pdf"

        count = core.create_editable_pdf(source, output)

        reader = PdfReader(str(output))
        fields = reader.get_fields()
        self.assertEqual(count, 2)
        self.assertIsNotNone(fields)
        assert fields is not None
        self.assertEqual(len(fields), 2)
        self.assertEqual(fields["editable_text_0001"]["/V"], "")
        self.assertEqual(fields["editable_text_0001"]["/TU"], "first line")
        first_annotation = reader.pages[0]["/Annots"][0].get_object()
        self.assertNotIn("/MK", first_annotation)

    def test_create_editable_pdf_can_show_detected_text_in_fields(self) -> None:
        source = self._make_pdf("source.pdf", ["first line"])
        output = self.root / "editable.pdf"

        core.create_editable_pdf(source, output, show_field_values=True)

        fields = PdfReader(str(output)).get_fields()
        self.assertIsNotNone(fields)
        assert fields is not None
        self.assertEqual(fields["editable_text_0001"]["/V"], "first line")

    def test_create_editable_pdf_respects_page_selection(self) -> None:
        source = self._make_pdf("source.pdf", ["first page", "second page"])
        output = self.root / "editable.pdf"

        count = core.create_editable_pdf(source, output, pages="2")

        fields = PdfReader(str(output)).get_fields()
        self.assertEqual(count, 1)
        self.assertIsNotNone(fields)
        assert fields is not None
        self.assertEqual(fields["editable_text_0001"]["/TU"], "second page")

    def test_create_editable_pdf_rejects_files_without_selectable_text(self) -> None:
        blank = self.root / "blank.pdf"
        pdf = canvas.Canvas(str(blank))
        pdf.showPage()
        pdf.save()

        with self.assertRaisesRegex(ValueError, "No selectable text"):
            core.create_editable_pdf(blank, self.root / "editable.pdf")

    def test_create_editable_pdf_can_use_ocr_candidates(self) -> None:
        blank = self.root / "blank.pdf"
        pdf = canvas.Canvas(str(blank))
        pdf.showPage()
        pdf.save()

        with patch(
            "pdf_control.core._load_ocr_dependencies",
            return_value=(_FakeFitz, _FakeImageModule, _FakePytesseract),
        ):
            count = core.create_editable_pdf(
                blank,
                self.root / "editable.pdf",
                use_ocr=True,
                ocr_language="eng",
                ocr_dpi=200,
            )

        fields = PdfReader(str(self.root / "editable.pdf")).get_fields()
        self.assertEqual(count, 1)
        self.assertIsNotNone(fields)
        assert fields is not None
        self.assertEqual(fields["editable_text_0001"]["/V"], "")
        self.assertEqual(fields["editable_text_0001"]["/TU"], "Hello World")

    def test_create_exact_editable_pdf_renders_background_and_adds_fields(self) -> None:
        source = self._make_pdf("source.pdf", ["first line"])
        output = self.root / "exact_editable.pdf"

        with patch(
            "pdf_control.core._render_pdf_as_image_background",
            side_effect=_fake_render_pdf_as_image_background,
        ):
            count = core.create_exact_editable_pdf(source, output)

        reader = PdfReader(str(output))
        fields = reader.get_fields()
        self.assertEqual(count, 1)
        self.assertEqual(len(reader.pages), 1)
        self.assertIsNotNone(fields)
        assert fields is not None
        self.assertEqual(fields["editable_text_0001"]["/V"], "")
        self.assertEqual(fields["editable_text_0001"]["/TU"], "first line")

    def test_create_exact_editable_pdf_adds_clickable_checkbox_fields(self) -> None:
        source = self.root / "checkbox.pdf"
        pdf = canvas.Canvas(str(source))
        pdf.drawString(120, 500, "Option")
        pdf.rect(100, 500, 12, 12)
        pdf.line(102, 506, 105, 502)
        pdf.line(105, 502, 111, 511)
        pdf.showPage()
        pdf.save()
        output = self.root / "exact_editable.pdf"

        with patch(
            "pdf_control.core._render_pdf_as_image_background",
            side_effect=_fake_render_pdf_as_image_background,
        ):
            count = core.create_exact_editable_pdf(source, output)

        fields = PdfReader(str(output)).get_fields()
        self.assertIsNotNone(fields)
        assert fields is not None
        self.assertGreaterEqual(count, 2)
        self.assertEqual(fields["editable_checkbox_0001"]["/FT"], "/Btn")
        self.assertIn(fields["editable_checkbox_0001"]["/V"], ("/Off", "/Yes"))

    def test_create_exact_editable_pdf_preserves_original_checkbox_widgets(self) -> None:
        source = self.root / "widget_checkbox.pdf"
        pdf = canvas.Canvas(str(source))
        pdf.acroForm.checkbox(name="original_choice", x=100, y=500, size=12, checked=True)
        pdf.showPage()
        pdf.save()
        output = self.root / "exact_editable.pdf"

        with (
            patch(
                "pdf_control.core._render_pdf_as_image_background",
                side_effect=_fake_render_pdf_as_image_background,
            ),
            patch("pdf_control.core._extract_vector_checkbox_candidates", return_value=[]),
        ):
            count = core.create_exact_editable_pdf(source, output)

        fields = PdfReader(str(output)).get_fields()
        self.assertIsNotNone(fields)
        assert fields is not None
        self.assertEqual(count, 1)
        self.assertEqual(fields["editable_checkbox_0001"]["/FT"], "/Btn")
        self.assertEqual(fields["editable_checkbox_0001"]["/V"], "/Yes")

    def test_get_page_size_returns_pdf_dimensions(self) -> None:
        source = self._make_pdf("source.pdf", ["base"])

        width, height = core.get_page_size(source)

        self.assertGreater(width, 0)
        self.assertGreater(height, 0)

    def test_render_pdf_pages_as_png_renders_each_page(self) -> None:
        source = self._make_pdf("source.pdf", ["base"])

        with patch("pdf_control.core._load_pdf_render_dependency", return_value=_FakeFitz):
            images = core.render_pdf_pages_as_png(source)

        self.assertEqual(images, [b"fake-png"])

    def test_dependency_injection_does_not_mutate_engine_globals(self) -> None:
        source = self._make_pdf("source.pdf", ["base"])
        original_loader = _engine._load_pdf_render_dependency

        with patch("pdf_control.core._load_pdf_render_dependency", return_value=_FakeFitz):
            core.render_pdf_pages_as_png(source)

        self.assertIs(_engine._load_pdf_render_dependency, original_loader)

    def test_get_pdf_info_reports_encrypted_files_without_decrypting(self) -> None:
        source = self._make_pdf("source.pdf", ["base"])
        encrypted = self._encrypt_pdf(source)

        info = core.get_pdf_info(encrypted)

        self.assertTrue(info["encrypted"])
        self.assertIsNone(info["pages"])

    def test_pdf_operations_reject_encrypted_files_with_clear_message(self) -> None:
        source = self._make_pdf("source.pdf", ["base"])
        encrypted = self._encrypt_pdf(source)

        with self.assertRaisesRegex(ValueError, "encrypted"):
            core.extract_pages(encrypted, self.root / "out.pdf", "1")


if __name__ == "__main__":
    unittest.main()
