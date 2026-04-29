import io
import unittest

from fastapi import HTTPException
from pypdf import PdfReader, PdfWriter
from starlette.datastructures import UploadFile

from src.server import insert


def _pdf_bytes(pages: int) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=300, height=400)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


class InsertApiTests(unittest.TestCase):
    def _upload(self, name: str, data: bytes) -> UploadFile:
        return UploadFile(filename=name, file=io.BytesIO(data))

    def test_insert_endpoint_success(self) -> None:
        resp = insert(
            input_pdf=self._upload("base.pdf", _pdf_bytes(2)),
            insert_pdf=self._upload("insert.pdf", _pdf_bytes(1)),
            after_page=1,
            output_name="result.pdf",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.media_type, "application/pdf")
        reader = PdfReader(io.BytesIO(resp.body))
        self.assertEqual(len(reader.pages), 3)

    def test_insert_endpoint_invalid_after_page(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            insert(
                input_pdf=self._upload("base.pdf", _pdf_bytes(2)),
                insert_pdf=self._upload("insert.pdf", _pdf_bytes(1)),
                after_page=9,
                output_name="result.pdf",
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("exceeds document page count", str(ctx.exception.detail))


if __name__ == "__main__":
    unittest.main()
