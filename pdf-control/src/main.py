from __future__ import annotations

import argparse
import importlib
import os
from pathlib import Path
from pprint import pprint


def _load_pdf_utils():
    try:
        return importlib.import_module(".pdf_utils", __package__)
    except ModuleNotFoundError as exc:
        print(f"Unable to run PDF command: {exc}")
        print("Install dependencies first: pip install -r requirements.txt")
        return None


def _print_gui_error(exc: Exception) -> int:
    error_text = str(exc).strip() or repr(exc)
    display = os.environ.get("DISPLAY", "")
    wayland = os.environ.get("WAYLAND_DISPLAY", "")
    xdg_session = os.environ.get("XDG_SESSION_TYPE", "")

    print("Unable to launch GUI: Tk could not create a window.")
    print(f"TclError details: {error_text}")

    if display:
        print(f"DISPLAY is set to: {display}")
    else:
        print("DISPLAY is not set.")

    if wayland:
        print(f"WAYLAND_DISPLAY is set to: {wayland}")
    if xdg_session:
        print(f"XDG_SESSION_TYPE is: {xdg_session}")

    lowered = error_text.lower()
    if "couldn't connect to display" in lowered or "cannot open display" in lowered:
        print("A display variable exists, but this shell cannot access the graphical server.")
        print("If you are using WSL, open the app from a regular WSL terminal (not a remote SSH shell).")
        print("If you are using SSH, connect with X forwarding: ssh -X or ssh -Y.")
    elif "no display name" in lowered:
        print("No active display is available in this shell.")
        print("Run from a desktop graphical session, or use SSH with X forwarding: ssh -X / ssh -Y.")
    else:
        print("Run GUI from a desktop session, or use SSH with X forwarding (ssh -X / ssh -Y).")

    print("You can still use CLI/API commands (for example: `serve`, `info`, `merge`).")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf-control",
        description="CLI tool to control PDF files (merge/split/extract/rotate/info).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_info = subparsers.add_parser("info", help="Show PDF information.")
    parser_info.add_argument("input", type=Path, help="Input PDF file.")

    parser_merge = subparsers.add_parser("merge", help="Merge multiple PDFs into one output.")
    parser_merge.add_argument("output", type=Path, help="Output PDF file.")
    parser_merge.add_argument("inputs", type=Path, nargs="+", help="Input PDF files.")

    parser_extract = subparsers.add_parser("extract", help="Extract selected pages from a PDF.")
    parser_extract.add_argument("input", type=Path, help="Input PDF file.")
    parser_extract.add_argument("output", type=Path, help="Output PDF file.")
    parser_extract.add_argument(
        "--pages",
        required=True,
        help='Page spec like "1,3,5-7" (1-based index).',
    )

    parser_split = subparsers.add_parser("split", help="Split PDF into one file per page.")
    parser_split.add_argument("input", type=Path, help="Input PDF file.")
    parser_split.add_argument(
        "--output-dir",
        type=Path,
        default=Path("split_output"),
        help="Output directory for page files.",
    )

    parser_rotate = subparsers.add_parser("rotate", help="Rotate selected pages.")
    parser_rotate.add_argument("input", type=Path, help="Input PDF file.")
    parser_rotate.add_argument("output", type=Path, help="Output PDF file.")
    parser_rotate.add_argument(
        "--pages",
        required=True,
        help='Page spec like "1,3,5-7" (1-based index).',
    )
    parser_rotate.add_argument(
        "--angle",
        type=int,
        required=True,
        choices=[90, 180, 270],
        help="Rotation angle in degrees.",
    )

    parser_edit = subparsers.add_parser("edit", help="Replace text inside PDF pages.")
    parser_edit.add_argument("input", type=Path, help="Input PDF file.")
    parser_edit.add_argument("output", type=Path, help="Output PDF file.")
    parser_edit.add_argument("--find", required=True, help="Text to find.")
    parser_edit.add_argument("--replace", required=True, help="Replacement text.")
    parser_edit.add_argument(
        "--pages",
        required=False,
        help='Optional page spec like "1,3,5-7". If omitted, all pages are used.',
    )

    parser_addtext = subparsers.add_parser("addtext", help="Add visible text overlay to a PDF page.")
    parser_addtext.add_argument("input", type=Path, help="Input PDF file.")
    parser_addtext.add_argument("output", type=Path, help="Output PDF file.")
    parser_addtext.add_argument("--page", type=int, required=True, help="Page number (1-based).")
    parser_addtext.add_argument("--text", required=True, help="Text to draw.")
    parser_addtext.add_argument("--x", type=float, required=True, help="X position from left.")
    parser_addtext.add_argument("--y", type=float, required=True, help="Y position from bottom.")
    parser_addtext.add_argument("--size", type=int, default=14, help="Font size.")
    parser_addtext.add_argument("--font-path", required=False, help="Optional TTF font path.")

    parser_serve = subparsers.add_parser("serve", help="Run HTTP API server.")
    parser_serve.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser_serve.add_argument("--port", type=int, default=8000, help="Port to bind.")
    parser_serve.add_argument("--reload", action="store_true", help="Enable auto-reload for development.")

    subparsers.add_parser("gui", help="Launch graphical interface.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "info":
        pdf_utils = _load_pdf_utils()
        if pdf_utils is None:
            return 1
        info = pdf_utils.get_pdf_info(args.input)
        pprint(info, sort_dicts=False)
        return 0

    if args.command == "merge":
        pdf_utils = _load_pdf_utils()
        if pdf_utils is None:
            return 1
        pdf_utils.merge_pdfs(args.inputs, args.output)
        print(f"Merged {len(args.inputs)} files into: {args.output}")
        return 0

    if args.command == "extract":
        pdf_utils = _load_pdf_utils()
        if pdf_utils is None:
            return 1
        pdf_utils.extract_pages(args.input, args.output, args.pages)
        print(f"Extracted pages {args.pages} to: {args.output}")
        return 0

    if args.command == "split":
        pdf_utils = _load_pdf_utils()
        if pdf_utils is None:
            return 1
        pdf_utils.split_pdf(args.input, args.output_dir)
        print(f"Split file to directory: {args.output_dir}")
        return 0

    if args.command == "rotate":
        pdf_utils = _load_pdf_utils()
        if pdf_utils is None:
            return 1
        pdf_utils.rotate_pages(args.input, args.output, args.pages, args.angle)
        print(f"Rotated pages {args.pages} by {args.angle} degrees into: {args.output}")
        return 0

    if args.command == "edit":
        pdf_utils = _load_pdf_utils()
        if pdf_utils is None:
            return 1
        replaced_count = pdf_utils.replace_text_in_pdf(
            args.input,
            args.output,
            args.find,
            args.replace,
            args.pages,
        )
        print(f"Replaced {replaced_count} occurrence(s) in: {args.output}")
        return 0

    if args.command == "addtext":
        pdf_utils = _load_pdf_utils()
        if pdf_utils is None:
            return 1
        pdf_utils.add_text_overlay(
            input_pdf=args.input,
            output_pdf=args.output,
            page_number=args.page,
            text=args.text,
            x=args.x,
            y=args.y,
            font_size=args.size,
            font_path=args.font_path,
        )
        print(f"Added text on page {args.page} into: {args.output}")
        return 0

    if args.command == "gui":
        try:
            from .gui import run_gui
        except ModuleNotFoundError as exc:
            print(f"Unable to launch GUI: {exc}")
            print("Install tkinter package for your system, then run the command again.")
            return 1
        try:
            run_gui()
        except Exception as exc:
            # Tkinter raises TclError when no graphical display is available.
            if exc.__class__.__name__ == "TclError":
                return _print_gui_error(exc)
            raise
        return 0

    if args.command == "serve":
        try:
            import uvicorn
        except ModuleNotFoundError as exc:
            print(f"Unable to launch API server: {exc}")
            print("Install dependencies first: pip install -r requirements.txt")
            return 1
        uvicorn.run("src.server:app", host=args.host, port=args.port, reload=args.reload)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        raise SystemExit(130)
