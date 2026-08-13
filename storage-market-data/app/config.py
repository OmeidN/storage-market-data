"""
Day-one settings. Deliberately plain — no Pydantic Settings, no provider
registry, no env-per-environment split. Add that machinery later if/when
it's actually needed (see planning.md Phase 3+), not now.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    request_delay_seconds: float = float(os.getenv("REQUEST_DELAY_SECONDS", "3"))
    raw_data_dir: Path = PROJECT_ROOT / os.getenv("RAW_DATA_DIR", "data/raw")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    user_agent: str = (
        "storage-market-data-bot/0.1 "
        "(personal research project; contact: set-your-email-here@example.com)"
    )


settings = Settings()
