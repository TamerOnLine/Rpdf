from __future__ import annotations

import argparse
import logging
import os
import shutil
import socket
import subprocess
import threading
import webbrowser
from pathlib import Path

from pdf_control import config
from pdf_control.logging import configure_logging

logger = logging.getLogger(__name__)


def _pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((config.DEFAULT_HOST, 0))
        return int(sock.getsockname()[1])


def _port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((config.DEFAULT_HOST, port))
        except OSError:
            return False
    return True


def _is_wsl() -> bool:
    try:
        release = Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8")
    except OSError:
        return False
    return "microsoft" in release.casefold()


def _open_browser(url: str) -> None:
    """Open the host browser, including the Windows browser when running in WSL."""
    try:
        if _is_wsl():
            powershell = shutil.which("powershell.exe")
            if powershell:
                subprocess.Popen(
                    [powershell, "-NoProfile", "-Command", "Start-Process", url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
        if not webbrowser.open(url):
            print(f"Open this address in your browser: {url}")
    except OSError:
        logger.warning("Could not open the browser automatically")
        print(f"Open this address in your browser: {url}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the PDF Control browser app.")
    parser.add_argument(
        "--port",
        type=int,
        default=config.default_port() or config.DEFAULT_PORT,
        help="Port to bind.",
    )
    parser.add_argument(
        "--max-upload-size",
        type=int,
        default=config.max_file_size_mb(),
        help="Maximum upload size in MB per file.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser automatically.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    import uvicorn

    configure_logging()
    args = build_parser().parse_args(argv)
    port = args.port or _pick_port()
    if not 1 <= port <= 65535:
        raise SystemExit("--port must be between 1 and 65535")
    if args.max_upload_size < 1:
        raise SystemExit("--max-upload-size must be greater than 0")
    if not _port_is_available(port):
        requested_port = port
        port = _pick_port()
        print(f"Port {requested_port} is already in use; using port {port} instead.")
    os.environ["PDF_CONTROL_MAX_FILE_SIZE_MB"] = str(args.max_upload_size)
    url = f"http://localhost:{port}"
    print(f"Starting {config.APP_NAME} on {url}")
    print(f"Max upload size: {args.max_upload_size} MB per file")
    logger.info("Starting browser app on %s", url)

    if not args.no_browser:
        threading.Timer(0.8, _open_browser, args=(url,)).start()

    uvicorn.run(
        "pdf_control.api:app",
        host=config.DEFAULT_HOST,
        port=port,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
