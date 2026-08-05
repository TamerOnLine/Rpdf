from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas

from pdf_control import core


def test_complex_pdf_preserves_mixed_page_geometry_and_rotation(tmp_path: Path) -> None:
    source = tmp_path / "complex.pdf"
    pdf = canvas.Canvas(str(source), pagesize=landscape(letter))
    pdf.setTitle("Complex integration document")
    pdf.drawString(72, 500, "Landscape content")
    pdf.acroForm.checkbox(name="approved", x=72, y=450, checked=True)
    pdf.showPage()
    pdf.setPageSize(letter)
    pdf.drawString(72, 720, "Portrait content")
    pdf.showPage()
    pdf.save()

    rotated = tmp_path / "rotated.pdf"
    extracted = tmp_path / "extracted.pdf"
    core.rotate_pages(source, rotated, "2", 90)
    core.extract_pages(rotated, extracted, "1-2")

    reader = PdfReader(str(extracted))
    assert len(reader.pages) == 2
    assert float(reader.pages[0].mediabox.width) > float(reader.pages[0].mediabox.height)
    assert reader.pages[1].get("/Rotate") == 90
    assert "Landscape content" in reader.pages[0].extract_text()
    assert "Portrait content" in reader.pages[1].extract_text()


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract is not installed")
def test_real_ocr_creates_fields_from_scanned_pdf(tmp_path: Path) -> None:
    pytest.importorskip("pytesseract")
    image = Image.new("RGB", (1400, 500), "white")
    draw = ImageDraw.Draw(image)
    font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    font = ImageFont.truetype(str(font_path), 72) if font_path.exists() else None
    draw.text((80, 170), "INVOICE TOTAL 1250", fill="black", font=font)
    scanned = tmp_path / "scanned.pdf"
    image.save(scanned, "PDF", resolution=150)

    output = tmp_path / "ocr-editable.pdf"
    count = core.create_editable_pdf(
        scanned,
        output,
        use_ocr=True,
        ocr_language="eng",
        ocr_dpi=200,
        ocr_min_confidence=20,
    )

    fields = PdfReader(str(output)).get_fields()
    assert count >= 1
    assert fields
    tooltips = " ".join(str(field.get("/TU", "")) for field in fields.values()).upper()
    assert "INVOICE" in tooltips
