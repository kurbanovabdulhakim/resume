"""
Structured JSON Lines Logger.

Appends machine-readable JSON events to logs/YYYY-MM-DD.jsonl.
Used across all CLI scripts to ensure AI-readable auditability and traceability.
"""

from __future__ import annotations
import json
import datetime
from pathlib import Path
from typing import Any, Dict

from scripts.config import Config


def get_today_log_file() -> Path:
    """Returns the path to the daily JSONL log file, ensuring the directory exists."""
    Config.ensure_directories()
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    return Config.LOGS_DIR / f"{today_str}.jsonl"


def log_event(event_type: str, payload: Dict[str, Any], level: str = "INFO") -> None:
    """Appends a structured event object to the daily JSONL log file."""
    log_file = get_today_log_file()
    record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "level": level,
        "event": event_type,
        "payload": payload,
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
