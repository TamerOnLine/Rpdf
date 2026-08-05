from __future__ import annotations

from pathlib import Path


def safe_name(name: str | None, fallback: str) -> str:
    clean_name = Path(name or fallback).name
    return clean_name or fallback


def normalize_page_spec(pages: str) -> str:
    return pages.replace("؛", ",").replace(";", ",").replace("،", ",").strip()
