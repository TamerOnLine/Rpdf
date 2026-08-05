# PDF Control

Current stable release: **1.0.0**.

PDF Control is a local Streamlit web app for everyday PDF work: merging files, extracting pages, splitting documents, rotating pages, adding text, inserting one PDF into another, and opening PDFs in Xournal++ for manual annotation.

## Features

- Session-based PDF library for uploading and managing multiple files.
- Full PDF preview in the browser, with image rendering for embedded environments.
- PDF information view with page count, encryption status, and metadata.
- Merge two or more PDF files into one document.
- Extract selected pages using formats such as `1,3,5-7` or `3;8`.
- Split a PDF into individual page files packaged as a ZIP archive.
- Rotate selected pages by `90`, `180`, or `270` degrees.
- Replace text when it is available in the PDF text layer.
- Add text to a selected page with optional TTF font support for Arabic and other non-Latin text.
- Generate a same-layout editable PDF by adding form fields over selectable text, with optional OCR for scanned PDFs.
- Generate an exact-look editable PDF by rendering the original pages as image backgrounds and placing transparent editable fields and clickable checkboxes above them.
- Insert a full PDF document into another PDF after a selected page.
- Open a PDF in Xournal++ when it is installed on the system.

## Requirements

- Python 3.10 or newer.
- A system capable of running Streamlit locally.
- Xournal++ is optional and only required for the manual editing workflow.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For development and tests:

```bash
pip install -e .[dev]
```

For OCR support with scanned/image-only PDFs:

```bash
.venv/bin/python -m pip install -e '.[ocr]'
sudo apt install tesseract-ocr tesseract-ocr-ara
```

If the virtual environment is already activated, this is equivalent to:

```bash
pip install -e '.[ocr]'
```

## Running The App

Use the packaged CLI:

```bash
pdf-control
```

Or run the development script:

```bash
scripts/dev.sh
```

You can set a specific port:

```bash
pdf-control --port 8501
```

You can also change the maximum upload size in megabytes:

```bash
pdf-control --max-upload-size 2048
```

## Usage

1. Open the local URL shown in the terminal.
2. Upload PDF files from the PDF file library section.
3. Choose the tab for the operation you want to run.
4. Select the required files, pages, and options.
5. Run the operation and download the generated result.

## Page Selection Format

Page numbers are 1-based, so the first page is `1`.

- Single page: `1`
- All pages: `all` or `الكل`
- Multiple pages: `1,3,8`
- Page range: `5-7`
- Mixed format: `1,3,5-7`
- Arabic separators and semicolons are accepted, such as `1؛3` or `1،3`.

## Important Notes

- Uploaded files are stored in the current Streamlit session, not in a permanent database.
- If two uploaded files use the same name but have different content, PDF Control keeps both by adding a numeric suffix to the newer file.
- PDF operations generate new files and do not modify the original uploads directly.
- Xournal++ opens a fresh temporary copy of library files to avoid reusing an older `.xopp` journal with missing or out-of-sync PDF pages.
- Encrypted PDFs can be inspected for encryption status, but processing operations require a decrypted copy.
- Text replacement depends on the internal structure of the PDF. It may not work with scanned pages, image-only text, or PDFs with complex text encoding.
- Editable PDF generation can use the selectable text layer or OCR. OCR requires the optional Python dependencies and the Tesseract system package.
- Editable PDF fields are transparent by default so the generated file keeps the original page appearance. Enable "إظهار النص المكتشف داخل الحقول" only when you want the detected text to be visibly placed in the generated fields.
- Use the "طبق الأصل" tab when preserving the visual appearance matters most. It rasterizes each page as a background, so the output looks closer to the original but may be larger and less sharp at low render DPI values.
- In the "طبق الأصل" tab, keep "تحويل مربعات الاختيار إلى عناصر قابلة للنقر" enabled when the source has checkbox-style options.
- OCR quality depends on scan clarity. Typed text is usually much better than handwriting, and handwritten Arabic may produce inaccurate text.
- Added text uses standard PDF coordinates, where the origin starts at the bottom-left corner of the page.
- For better Arabic text rendering when adding text, upload a suitable TTF font or rely on fonts available on the system.

## Resource Limits

PDF Control applies conservative limits before expensive work. Override them through environment variables:

```bash
PDF_CONTROL_MAX_FILE_SIZE_MB=256
PDF_CONTROL_MAX_SESSION_SIZE_MB=512
PDF_CONTROL_MAX_PAGES=2000
PDF_CONTROL_MAX_RENDER_PAGES=250
```

The session limit includes uploaded library files and generated download results. Rendering has a
lower page limit because page images and OCR consume substantially more memory than PDF composition.

## Project Structure

```text
.
├── pyproject.toml
├── Makefile
├── .env.example
├── requirements.txt
├── src/
│   └── pdf_control/
│       ├── cli.py
│       ├── config.py
│       ├── core.py
│       ├── logging.py
│       ├── models.py
│       ├── utils.py
│       ├── web.py
│       └── features/
├── tests/
├── scripts/
├── .github/workflows/
├── docs/
├── examples/
└── assets/
```

- `src/pdf_control/web.py`: lightweight Streamlit application shell.
- `src/pdf_control/ui.py`: shared Streamlit session, result, and local-application helpers.
- `src/pdf_control/features/`: one Streamlit module per operation tab.
- `src/pdf_control/core.py`: stable compatibility facade for processing APIs.
- `src/pdf_control/merge.py`: composition, extraction, splitting, and rotation APIs.
- `src/pdf_control/editing.py`: text replacement and overlay APIs.
- `src/pdf_control/ocr.py`: rendering and OCR-facing APIs.
- `src/pdf_control/forms.py`: editable form generation APIs.
- `src/pdf_control/limits.py`: configurable resource guards.
- `src/pdf_control/cli.py`: command-line entrypoint.
- `src/pdf_control/config.py`: environment-based configuration.
- `src/pdf_control/utils.py`: shared helper functions.
- `src/pdf_control/logging.py`: logging setup.
- `scripts/dev.sh`: local development runner.
- `scripts/test.sh`: test runner.

## Developer Commands

```bash
make install
make run
make test
make lint
make format
make check
```

The same commands are mirrored by scripts in `scripts/`.

## Testing

```bash
scripts/test.sh
```

Or:

```bash
pytest
```

## License

This project is licensed under the MIT License. See `LICENSE` for details.
