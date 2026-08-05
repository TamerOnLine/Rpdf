from __future__ import annotations

import argparse
import logging
import os
import socket
import subprocess
import sys
from pathlib import Path

from pdf_control import config
from pdf_control.logging import configure_logging

logger = logging.getLogger(__name__)


def _pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((config.DEFAULT_HOST, 0))
        return int(sock.getsockname()[1])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the PDF Control Streamlit app.")
    parser.add_argument("--port", type=int, default=config.default_port(), help="Port to bind.")
    parser.add_argument(
        "--max-upload-size",
        type=int,
        default=config.max_upload_size_mb(),
        help="Maximum upload size in MB per file.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser automatically.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    port = args.port or _pick_port()
    web_path = Path(__file__).with_name("web.py")

    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = env.get(
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false"
    )
    env["STREAMLIT_SERVER_MAX_UPLOAD_SIZE"] = str(args.max_upload_size)

    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(web_path),
        "--server.address",
        config.DEFAULT_HOST,
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]

    url = f"http://localhost:{port}"
    print(f"Starting {config.APP_NAME} on {url}")
    print(f"Max upload size: {args.max_upload_size} MB per file")
    logger.info("Starting Streamlit app on %s", url)

    process = subprocess.Popen(command, env=env)
    if not args.no_browser:
        subprocess.Popen(
            [sys.executable, "-m", "webbrowser", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
