import io
import unittest
import zipfile
from unittest.mock import patch

from fastapi import HTTPException
from pypdf import PdfReader, PdfWriter
from starlette.datastructures import UploadFile

from src import server
from src.server import addtext, edit, extract, health, info, insert, merge, rotate, split


def _pdf_bytes(pages: int) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=300, height=400)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def _text_pdf_bytes(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=400)
    from pypdf.generic import DecodedStreamObject, NameObject

    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 20 200 Td ({text}) Tj ET".encode("latin-1"))
    ref = writer._add_object(stream)
    page[NameObject("/Contents")] = ref

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


class ServerEndpointsAllTests(unittest.TestCase):
    def _upload(self, name: str, data: bytes) -> UploadFile:
        return UploadFile(filename=name, file=io.BytesIO(data))

    def test_health(self) -> None:
        self.assertEqual(health(), {"status": "ok"})

    def test_info_success(self) -> None:
        result = info(self._upload("a.pdf", _pdf_bytes(2)))
        self.assertEqual(result["pages"], 2)

    def test_info_failure_wrapped_http_exception(self) -> None:
        with patch("src.server.pdf_utils.get_pdf_info", side_effect=ValueError("bad file")):
            with self.assertRaises(HTTPException) as ctx:
                info(self._upload("a.pdf", _pdf_bytes(1)))
            self.assertEqual(ctx.exception.status_code, 400)

    def test_info_rejects_non_pdf_upload(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            info(self._upload("not_pdf.txt", b"hello"))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("not a valid PDF", str(ctx.exception.detail))

    def test_info_rejects_upload_over_size_limit(self) -> None:
        with patch.object(server, "MAX_UPLOAD_SIZE_BYTES", 8):
            with self.assertRaises(HTTPException) as ctx:
                info(self._upload("a.pdf", _pdf_bytes(1)))
        self.assertEqual(ctx.exception.status_code, 413)

    def test_merge_success(self) -> None:
        resp = merge(
            files=[self._upload("a.pdf", _pdf_bytes(1)), self._upload("b.pdf", _pdf_bytes(2))],
            output_name="merged.pdf",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(PdfReader(io.BytesIO(resp.body)).pages), 3)

    def test_merge_requires_two_files(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            merge(files=[self._upload("a.pdf", _pdf_bytes(1))])
        self.assertEqual(ctx.exception.status_code, 400)

    def test_merge_failure_wrapped_http_exception(self) -> None:
        with patch("src.server.pdf_utils.merge_pdfs", side_effect=RuntimeError("merge fail")):
            with self.assertRaises(HTTPException) as ctx:
                merge(
                    files=[
                        self._upload("a.pdf", _pdf_bytes(1)),
                        self._upload("b.pdf", _pdf_bytes(1)),
                    ],
                    output_name="merged.pdf",
                )
            self.assertEqual(ctx.exception.status_code, 400)

    def test_merge_sanitizes_download_name(self) -> None:
        resp = merge(
            files=[self._upload("a.pdf", _pdf_bytes(1)), self._upload("b.pdf", _pdf_bytes(1))],
            output_name="../merged.pdf",
        )
        self.assertIn('filename="merged.pdf"', resp.headers["content-disposition"])

    def test_extract_success(self) -> None:
        resp = extract(
            input_pdf=self._upload("a.pdf", _pdf_bytes(4)), pages="1,4", output_name="extracted.pdf"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(PdfReader(io.BytesIO(resp.body)).pages), 2)

    def test_extract_failure_wrapped_http_exception(self) -> None:
        with patch("src.server.pdf_utils.extract_pages", side_effect=RuntimeError("extract fail")):
            with self.assertRaises(HTTPException) as ctx:
                extract(
                    input_pdf=self._upload("a.pdf", _pdf_bytes(2)),
                    pages="1",
                    output_name="extracted.pdf",
                )
            self.assertEqual(ctx.exception.status_code, 400)

    def test_split_success(self) -> None:
        resp = split(input_pdf=self._upload("a.pdf", _pdf_bytes(3)), zip_name="split_pages.zip")
        self.assertEqual(resp.status_code, 200)
        zf = zipfile.ZipFile(io.BytesIO(resp.body))
        names = [n for n in zf.namelist() if n.endswith(".pdf")]
        self.assertEqual(len(names), 3)

    def test_split_failure_wrapped_http_exception(self) -> None:
        with patch("src.server.pdf_utils.split_pdf", side_effect=RuntimeError("split fail")):
            with self.assertRaises(HTTPException) as ctx:
                split(input_pdf=self._upload("a.pdf", _pdf_bytes(2)), zip_name="split_pages.zip")
            self.assertEqual(ctx.exception.status_code, 400)

    def test_rotate_success(self) -> None:
        resp = rotate(
            input_pdf=self._upload("a.pdf", _pdf_bytes(2)),
            pages="2",
            angle=90,
            output_name="rotated.pdf",
        )
        self.assertEqual(resp.status_code, 200)
        reader = PdfReader(io.BytesIO(resp.body))
        self.assertEqual(int(reader.pages[1].get("/Rotate", 0)), 90)

    def test_rotate_invalid_angle(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            rotate(
                input_pdf=self._upload("a.pdf", _pdf_bytes(2)),
                pages="1",
                angle=45,
                output_name="rotated.pdf",
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_edit_success(self) -> None:
        resp = edit(
            input_pdf=self._upload("a.pdf", _text_pdf_bytes("Hello Hello")),
            find_text="Hello",
            replace_text="Hi",
            pages=None,
            output_name="edited.pdf",
        )
        self.assertEqual(resp.status_code, 200)

    def test_edit_not_found(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            edit(
                input_pdf=self._upload("a.pdf", _text_pdf_bytes("Hello")),
                find_text="XYZ",
                replace_text="Hi",
                output_name="edited.pdf",
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_addtext_success(self) -> None:
        resp = addtext(
            input_pdf=self._upload("a.pdf", _pdf_bytes(1)),
            page=1,
            text="stamp",
            x=10,
            y=10,
            size=12,
            output_name="with_text.pdf",
            font_file=None,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(PdfReader(io.BytesIO(resp.body)).pages), 1)

    def test_addtext_invalid_page(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            addtext(
                input_pdf=self._upload("a.pdf", _pdf_bytes(1)),
                page=0,
                text="stamp",
                x=10,
                y=10,
                size=12,
                output_name="with_text.pdf",
                font_file=None,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_addtext_with_font_upload_success(self) -> None:
        fake_font = self._upload("font.ttf", b"not-a-real-font")

        def _fake_add_text_overlay(**kwargs):
            writer = PdfWriter()
            writer.add_blank_page(width=300, height=400)
            with kwargs["output_pdf"].open("wb") as f:
                writer.write(f)

        with patch(
            "src.server.pdf_utils.add_text_overlay", side_effect=_fake_add_text_overlay
        ) as mocked:
            resp = addtext(
                input_pdf=self._upload("a.pdf", _pdf_bytes(1)),
                page=1,
                text="stamp",
                x=10,
                y=10,
                size=12,
                output_name="with_text.pdf",
                font_file=fake_font,
            )
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(mocked.called)

    def test_insert_success(self) -> None:
        resp = insert(
            input_pdf=self._upload("base.pdf", _pdf_bytes(2)),
            insert_pdf=self._upload("ins.pdf", _pdf_bytes(1)),
            after_page=1,
            output_name="inserted.pdf",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(PdfReader(io.BytesIO(resp.body)).pages), 3)

    def test_insert_handles_same_upload_filenames(self) -> None:
        resp = insert(
            input_pdf=self._upload("same.pdf", _pdf_bytes(2)),
            insert_pdf=self._upload("same.pdf", _pdf_bytes(1)),
            after_page=1,
            output_name="inserted.pdf",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(PdfReader(io.BytesIO(resp.body)).pages), 3)


if __name__ == "__main__":
    unittest.main()
