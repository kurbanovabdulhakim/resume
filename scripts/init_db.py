"""
Database Initialization Script.

Initializes or verifies the SQLite database schema for positions.db.
This script is idempotent and safe to run multiple times.

Usage:
    python scripts/init_db.py [--db-path PATH] [--json]
"""

from __future__ import annotations
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.logger import log_event


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Returns an active SQLite connection with foreign keys enabled."""
    target_path = Path(db_path) if db_path else Config.DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_database(db_path: Path | None = None) -> Dict[str, Any]:
    """Executes schema.sql to ensure all tables and indexes exist."""
    target_path = Path(db_path) if db_path else Config.DB_PATH
    schema_file = Config.SCHEMA_SQL_PATH

    if not schema_file.is_file():
        err_msg = f"Schema file not found at {schema_file}"
        log_event("DB_INIT_ERROR", {"error": err_msg}, level="ERROR")
        return {"success": False, "error": err_msg, "code": Config.EXIT_ERROR}

    try:
        conn = get_connection(target_path)
        with open(schema_file, "r", encoding="utf-8") as f:
            sql_script = f.read()
        conn.executescript(sql_script)

        # Retrieve table list for verification
        cursor = conn.cursor()
        tables = [
            r[0]
            for r in cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        conn.close()

        result = {
            "success": True,
            "code": Config.EXIT_SUCCESS,
            "db_path": str(target_path),
            "tables": tables,
        }
        log_event("DB_INIT_SUCCESS", {"db_path": str(target_path), "tables": tables})
        return result
    except Exception as e:
        err_msg = f"Failed to initialize database: {str(e)}"
        log_event("DB_INIT_EXCEPTION", {"error": err_msg}, level="ERROR")
        return {"success": False, "error": err_msg, "code": Config.EXIT_ERROR}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize or verify the SQLite database for positions.db"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Custom path to positions.db (defaults to db/positions.db)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output result in machine-readable JSON"
    )

    args = parser.parse_args()
    db_target = Path(args.db_path) if args.db_path else None
    result = init_database(db_target)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"[OK] Database initialized successfully at: {result['db_path']}")
            print(f"     Tables verified: {', '.join(result['tables'])}")
        else:
            print(f"[ERROR] {result['error']}", file=sys.stderr)

    return result["code"]


if __name__ == "__main__":
    sys.exit(main())
