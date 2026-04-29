from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from . import pdf_utils

app = FastAPI(
    title="PDF Control API",
    description="HTTP API for PDF operations (info/merge/extract/split/rotate/edit/addtext/insert).",
    version="1.0.0",
)


def _read_upload(upload: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as f:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)


def _pdf_response(output_pdf: Path, download_name: str) -> Response:
    return Response(
        content=output_pdf.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )


def _zip_response(output_zip: Path, download_name: str) -> Response:
    return Response(
        content=output_zip.read_bytes(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/info")
def info(input_pdf: UploadFile = File(...)) -> dict:
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_dir = Path(tmp_dir)
        source = temp_dir / (input_pdf.filename or "input.pdf")
        _read_upload(input_pdf, source)
        try:
            return pdf_utils.get_pdf_info(source)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/merge")
def merge(
    files: list[UploadFile] = File(...),
    output_name: str = Form("merged.pdf"),
) -> Response:
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="At least two input files are required.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_dir = Path(tmp_dir)
        input_paths: list[Path] = []
        for i, upload in enumerate(files, start=1):
            name = upload.filename or f"input_{i}.pdf"
            path = temp_dir / name
            _read_upload(upload, path)
            input_paths.append(path)

        output_pdf = temp_dir / output_name
        try:
            pdf_utils.merge_pdfs(input_paths, output_pdf)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _pdf_response(output_pdf, output_name)


@app.post("/extract")
def extract(
    input_pdf: UploadFile = File(...),
    pages: str = Form(...),
    output_name: str = Form("extracted.pdf"),
) -> Response:
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_dir = Path(tmp_dir)
        source = temp_dir / (input_pdf.filename or "input.pdf")
        output_pdf = temp_dir / output_name
        _read_upload(input_pdf, source)
        try:
            pdf_utils.extract_pages(source, output_pdf, pages)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _pdf_response(output_pdf, output_name)


@app.post("/split")
def split(
    input_pdf: UploadFile = File(...),
    zip_name: str = Form("split_pages.zip"),
) -> Response:
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_dir = Path(tmp_dir)
        source = temp_dir / (input_pdf.filename or "input.pdf")
        output_dir = temp_dir / "split_output"
        output_zip = temp_dir / zip_name
        _read_upload(input_pdf, source)
        try:
            pdf_utils.split_pdf(source, output_dir)
            with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for file_path in sorted(output_dir.glob("*.pdf")):
                    zf.write(file_path, arcname=file_path.name)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _zip_response(output_zip, zip_name)


@app.post("/rotate")
def rotate(
    input_pdf: UploadFile = File(...),
    pages: str = Form(...),
    angle: int = Form(...),
    output_name: str = Form("rotated.pdf"),
) -> Response:
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_dir = Path(tmp_dir)
        source = temp_dir / (input_pdf.filename or "input.pdf")
        output_pdf = temp_dir / output_name
        _read_upload(input_pdf, source)
        try:
            pdf_utils.rotate_pages(source, output_pdf, pages, angle)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _pdf_response(output_pdf, output_name)


@app.post("/edit")
def edit(
    input_pdf: UploadFile = File(...),
    find_text: str = Form(...),
    replace_text: str = Form(...),
    pages: str | None = Form(None),
    output_name: str = Form("edited.pdf"),
) -> Response:
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_dir = Path(tmp_dir)
        source = temp_dir / (input_pdf.filename or "input.pdf")
        output_pdf = temp_dir / output_name
        _read_upload(input_pdf, source)
        try:
            pdf_utils.replace_text_in_pdf(source, output_pdf, find_text, replace_text, pages)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _pdf_response(output_pdf, output_name)


@app.post("/addtext")
def addtext(
    input_pdf: UploadFile = File(...),
    page: int = Form(...),
    text: str = Form(...),
    x: float = Form(...),
    y: float = Form(...),
    size: int = Form(14),
    output_name: str = Form("with_text.pdf"),
    font_file: UploadFile | None = File(None),
) -> Response:
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_dir = Path(tmp_dir)
        source = temp_dir / (input_pdf.filename or "input.pdf")
        output_pdf = temp_dir / output_name
        _read_upload(input_pdf, source)

        font_path: str | None = None
        if font_file is not None:
            font_dest = temp_dir / (font_file.filename or "font.ttf")
            _read_upload(font_file, font_dest)
            font_path = str(font_dest)

        try:
            pdf_utils.add_text_overlay(
                input_pdf=source,
                output_pdf=output_pdf,
                page_number=page,
                text=text,
                x=x,
                y=y,
                font_size=size,
                font_path=font_path,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _pdf_response(output_pdf, output_name)


@app.post("/insert")
def insert(
    input_pdf: UploadFile = File(...),
    insert_pdf: UploadFile = File(...),
    after_page: int = Form(...),
    output_name: str = Form("inserted.pdf"),
) -> Response:
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_dir = Path(tmp_dir)
        source = temp_dir / (input_pdf.filename or "input.pdf")
        insert_source = temp_dir / (insert_pdf.filename or "insert.pdf")
        output_pdf = temp_dir / output_name

        _read_upload(input_pdf, source)
        _read_upload(insert_pdf, insert_source)

        try:
            pdf_utils.insert_pdf_after_page(
                input_pdf=source,
                insert_pdf=insert_source,
                output_pdf=output_pdf,
                after_page=after_page,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _pdf_response(output_pdf, output_name)
