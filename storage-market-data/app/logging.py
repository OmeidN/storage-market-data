"""
Minimal logging setup. No structured/JSON logging yet — that's a Phase 10+
concern (scrape_runs, metrics) once there's an actual pipeline emitting
events worth structuring.
"""
import logging

from app.config import settings


def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    return logging.getLogger(name)
