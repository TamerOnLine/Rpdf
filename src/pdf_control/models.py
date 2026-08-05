from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PdfResult:
    label: str
    filename: str
    data: bytes
    mime: str
