# PDF Control

PDF Control is a local Streamlit web app for working with PDF files from your browser. It is designed for everyday PDF tasks such as merging files, extracting pages, splitting documents, rotating pages, adding text, inserting one PDF into another, and opening PDFs in Xournal++ for manual annotation.

## Features

- Session-based PDF library for uploading and managing multiple files in one place.
- PDF information view, including page count, encryption status, and available metadata.
- Merge two or more PDF files into a single document.
- Extract selected pages using formats such as `1,3,5-7` or `3;8`.
- Split a PDF into individual page files packaged as a ZIP archive.
- Rotate selected pages by `90`, `180`, or `270` degrees.
- Replace text in selected pages or across the full document when the text is available in the PDF text layer.
- Add text to a selected page with optional TTF font support for Arabic and other non-Latin text.
- Insert a full PDF document into another PDF after a selected page.
- Open a PDF in Xournal++ when it is installed on the system.

## Requirements

- Python 3.10 or newer.
- A system capable of running Streamlit locally.
- Xournal++ is optional and only required for the manual editing workflow.

## Installation

From the project root:

```bash
cd pdf-control
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running The App

From the project root:

```bash
cd pdf-control
./run.sh
```

The script automatically selects an available port and starts the app on a local URL such as:

```text
http://localhost:8501
```

You can set a specific port with the `PORT` environment variable:

```bash
cd pdf-control
PORT=8501 ./run.sh
```

You can also change the maximum upload size in megabytes:

```bash
cd pdf-control
STREAMLIT_MAX_UPLOAD_SIZE_MB=2048 ./run.sh
```

## Usage

1. Open the local URL shown in the terminal.
2. Upload PDF files from the `PDF file library` section in the app.
3. Choose the tab for the operation you want to run.
4. Select the required files, pages, and options.
5. Run the operation and download the generated result.

## Page Selection Format

Page numbers are 1-based, so the first page is `1`.

- Single page: `1`
- Multiple pages: `1,3,8`
- Page range: `5-7`
- Mixed format: `1,3,5-7`
- Arabic separators and semicolons are accepted by the app, such as `1؛3` or `1،3`.

## Important Notes

- Uploaded files are stored in the current Streamlit session, not in a permanent database.
- PDF operations generate new files and do not modify the original uploads directly.
- Text replacement depends on the internal structure of the PDF. It may not work with scanned pages, image-only text, or PDFs with complex text encoding.
- Added text uses standard PDF coordinates, where the origin starts at the bottom-left corner of the page.
- For better Arabic text rendering when adding text, upload a suitable TTF font or rely on fonts available on the system.

## Project Structure

```text
.
└── pdf-control/
    ├── requirements.txt
    ├── run.sh
    └── src/
        ├── __init__.py
        ├── pdf_utils.py
        └── streamlit_app.py
```

- `pdf-control/src/streamlit_app.py`: Streamlit UI and user interaction flow.
- `pdf-control/src/pdf_utils.py`: PDF processing utilities.
- `pdf-control/requirements.txt`: Python dependencies required to run the app.
- `pdf-control/run.sh`: Local startup script that configures Streamlit and opens the app in the browser.

## Main Dependencies

- `streamlit`: Local web interface.
- `pypdf`: Reading, writing, and modifying PDF files.
- `reportlab`: Creating text overlays for PDF pages.
- `arabic-reshaper` and `python-bidi`: Improving Arabic text rendering when adding text to PDFs.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
