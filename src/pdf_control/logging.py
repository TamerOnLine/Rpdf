from __future__ import annotations

import logging

from pdf_control import config


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format=f"%(asctime)s %(levelname)s [{config.APP_NAME}] %(name)s: %(message)s",
    )
