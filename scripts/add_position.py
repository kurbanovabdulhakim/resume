"""
Add Position CLI.

Manually registers a new job vacancy and initial application record in positions.db.

Usage:
    python scripts/add_position.py --title "Job Title" --company "Employer" [--url URL] [--sector SECTOR] [--tier TIER] [--json]
"""

from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import get_connection, init_database
from scripts.logger import log_event


def extract_vacancy_id(url: str, title: str, company: str) -> str:
    """Extracts vacancy ID from hh.uz URL or generates unique deterministic hash."""
    if url:
        m = re.search(r"vacancy/(\d+)", url)
        if m:
            return m.group(1)
    raw = f"{company}_{title}_{datetime.datetime.now().isoformat()}".encode("utf-8")
    return f"man_{hashlib.md5(raw).hexdigest()[:10]}"


def add_vacancy(
    title: str,
    company: str,
    url: str = "",
    source: str = "manual",
    tier: int = 2,
    sector: str = "Finance",
    salary_text: str = "",
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    notes: str = "",
    status: str = "applied",
    db_path: Path | None = None,
) -> Dict[str, Any]:
    """Inserts a vacancy and creates an initial application entry."""
    target_db = Path(db_path) if db_path else Config.DB_PATH
    init_database(target_db)

    vid = extract_vacancy_id(url, title, company)
    now_iso = datetime.datetime.now().isoformat()

    valid_statuses = ("applied", "viewed", "invited", "interview", "offer", "rejected", "declined")
    if status not in valid_statuses:
        err_msg = f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}"
        return {"success": False, "error": err_msg, "code": Config.EXIT_ERROR}

    try:
        conn = get_connection(target_db)
        cursor = conn.cursor()

        # Insert or replace vacancy
        cursor.execute(
            """
            INSERT INTO vacancies (id, title, company, url, source, tier, sector, salary_min, salary_max, salary_text, published_at, scraped_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title, company=excluded.company, url=excluded.url,
                tier=excluded.tier, sector=excluded.sector, is_active=1
        """,
            (vid, title, company, url, source, tier, sector, salary_min, salary_max, salary_text, now_iso, now_iso),
        )

        # Insert application entry
        cursor.execute("SELECT id FROM applications WHERE vacancy_id = ?", (vid,))
        existing_app = cursor.fetchone()

        if existing_app:
            cursor.execute(
                """
                UPDATE applications
                SET status = ?, notes = coalesce(notes, '') || '\n' || ?, last_updated = ?
                WHERE vacancy_id = ?
            """,
                (status, notes, now_iso, vid),
            )
        else:
            cursor.execute(
                """
                INSERT INTO applications (vacancy_id, status, applied_at, cover_letter_sent, pdf_sent_in_chat, notes, last_updated)
                VALUES (?, ?, ?, 0, 0, ?, ?)
            """,
                (vid, status, now_iso, notes, now_iso),
            )

        conn.commit()
        conn.close()

        result = {
            "success": True,
            "code": Config.EXIT_SUCCESS,
            "vacancy_id": vid,
            "title": title,
            "company": company,
            "status": status,
            "tier": tier,
            "sector": sector,
            "db_path": str(target_db),
            "timestamp": now_iso,
        }
        log_event("VACANCY_ADDED", result)
        return result
    except Exception as e:
        err_msg = f"Failed to add vacancy: {str(e)}"
        log_event("VACANCY_ADD_ERROR", {"error": err_msg}, level="ERROR")
        return {"success": False, "error": err_msg, "code": Config.EXIT_ERROR}


def main() -> int:
    parser = argparse.ArgumentParser(description="Add a vacancy manually to positions.db")
    parser.add_argument("--title", type=str, required=True, help="Job title")
    parser.add_argument("--company", type=str, required=True, help="Company name")
    parser.add_argument("--url", type=str, default="", help="Link to posting")
    parser.add_argument("--source", type=str, default="manual", help="Source (hh.uz, olx, manual, etc.)")
    parser.add_argument("--tier", type=int, default=2, help="Tier (1=Corp/Bank, 2=Mid, 3=Small)")
    parser.add_argument("--sector", type=str, default="Finance", help="Sector (Finance, Logistics, Analytics, Management)")
    parser.add_argument("--salary", type=str, default="", help="Salary text")
    parser.add_argument("--notes", type=str, default="", help="Notes / comments")
    parser.add_argument("--status", type=str, default="applied", help="Initial status")
    parser.add_argument("--db-path", type=str, default=None, help="Custom DB path")
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()
    db_target = Path(args.db_path) if args.db_path else None

    res = add_vacancy(
        title=args.title,
        company=args.company,
        url=args.url,
        source=args.source,
        tier=args.tier,
        sector=args.sector,
        salary_text=args.salary,
        notes=args.notes,
        status=args.status,
        db_path=db_target,
    )

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        if res["success"]:
            print(f"[OK] Position added: [{res['vacancy_id']}] {res['company']} — {res['title']}")
            print(f"     Tier: {res['tier']}, Sector: {res['sector']}, Status: {res['status']}")
        else:
            print(f"[ERROR] {res['error']}", file=sys.stderr)

    return res["code"]


if __name__ == "__main__":
    sys.exit(main())
