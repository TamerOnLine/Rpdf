# Changelog

## Unreleased

- Replaced the Streamlit runtime with a standard Arabic HTML/CSS/JavaScript browser interface.
- Added a FastAPI layer for all supported PDF processing operations.
- Added isolated per-request temporary files with cleanup after downloads.
- Streamed uploads and generated downloads to avoid retaining whole files in memory.
- Enforced server-side bounds for OCR, rendering, fields, checkboxes, fonts, and output names.
- Consolidated PDF loading and page-selection primitives in `_pdf.py`.
- Changed the default local browser port to 8000.
- Removed the obsolete Streamlit interface, unused compatibility modules, and generated artifacts.
- Moved page selection and validated PDF loading into shared internal primitives.
- Established the composition module as the canonical implementation for document information,
  merge, insert, extract, split, and rotate operations.
- Replaced process-wide dependency monkey-patching with call-scoped dependency injection.
- Converted the merge, extract, split, rotate, info, and insert tabs into real feature modules.
- Moved every remaining tab implementation into its feature module and replaced the legacy web
  module with a small shared `ui` helper module.
- Added regression coverage ensuring rendering dependency injection cannot mutate engine globals.

## 1.0.0 - 2026-07-30

- Introduced stable processing modules for composition, editing, OCR, and forms.
- Split the Streamlit application shell into per-tab feature modules.
- Added configurable file, session-memory, processing-page, and rendering-page limits.
- Added visible multi-stage status reporting for long-running PDF operations.
- Added real Tesseract OCR integration coverage and complex-PDF regression coverage.
- Added a dedicated OCR integration job to CI.
