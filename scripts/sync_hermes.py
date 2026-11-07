"""
Hermes Batch Queue Sync Script.

Synchronizes vacancies and applied application statuses from HERMES_BATCH_QUEUE.json
and related Hermes execution reports into SQLite database (positions.db).

This script is idempotent: running it repeatedly updates existing records without duplication.

Usage:
    python scripts/sync_hermes.py [--queue-file PATH] [--db-path PATH] [--dry-run] [--json]
"""

from __future__ import annotations
import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import get_connection, init_database
from scripts.logger import log_event


def normalize_sector(category_str: str, title: str = "") -> str:
    """Normalizes raw category or job title into one of standard sectors."""
    combined = f"{category_str} {title}".lower()
    if any(k in combined for k in ["банк", "финанс", "аудит", "бухгалтер", "казначей", "finance", "audit"]):
        return "Finance"
    if any(k in combined for k in ["логистик", "вэд", "склад", "авиа", "доставк", "logistics", "supply"]):
        return "Logistics"
    if any(k in combined for k in ["аналитик", "data", " bi ", "bi-", "sql", "analytics"]):
        return "Analytics"
    if any(k in combined for k in ["менедж", "управлен", "директор", "руководит", "operation", "manager"]):
        return "Management"
    return "Finance"


def parse_salary_range(salary_str: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """Extracts approximate numeric min and max salary from salary text."""
    if not salary_str:
        return (None, None)
    clean = salary_str.replace("\u202f", "").replace(" ", "").replace(",", "")
    nums = [int(n) for n in re.findall(r"\d+", clean)]
    if not nums:
        return (None, None)
    if len(nums) == 1:
        return (nums[0], nums[0])
    return (nums[0], nums[1])


def collect_applied_reports_ids(queue_dir: Path) -> Set[str]:
    """Scans directory containing the queue for hermes report files with confirmed applications."""
    applied_ids: Set[str] = set()
    if not queue_dir.exists():
        return applied_ids

    for report_file in queue_dir.glob("*hermes*report*.json"):
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                rep_data = json.load(f)
                items = rep_data.get("results", []) if isinstance(rep_data, dict) else rep_data
                for it in items:
                    if isinstance(it, dict) and (it.get("applied") or it.get("resume_sent")):
                        vid = str(it.get("id"))
                        if vid:
                            applied_ids.add(vid)
        except Exception:
            continue
    return applied_ids


def sync_hermes_queue(
    queue_path: Path | None = None,
    db_path: Path | None = None,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Syncs Hermes queue and confirmed applications into SQLite positions.db."""
    target_queue = Path(queue_path) if queue_path else Config.get_hermes_queue_path()
    if not target_queue or not target_queue.is_file():
        err_msg = f"Hermes queue file not found. Checked: {target_queue or 'Default paths'}"
        log_event("HERMES_SYNC_ERROR", {"error": err_msg}, level="ERROR")
        return {"success": False, "error": err_msg, "code": Config.EXIT_ERROR}

    target_db = Path(db_path) if db_path else Config.DB_PATH
    init_database(target_db)

    try:
        with open(target_queue, "r", encoding="utf-8") as f:
            queue_data = json.load(f)
    except Exception as e:
        err_msg = f"Failed to read Hermes queue file: {e}"
        log_event("HERMES_SYNC_ERROR", {"error": err_msg}, level="ERROR")
        return {"success": False, "error": err_msg, "code": Config.EXIT_ERROR}

    applied_report_ids = collect_applied_reports_ids(target_queue.parent)

    batches = queue_data.get("batches", [])
    now_iso = datetime.datetime.now().isoformat()

    conn = get_connection(target_db)
    cursor = conn.cursor()

    total_vacancies_seen = 0
    new_vacancies = 0
    updated_vacancies = 0
    applications_synced = 0

    for batch in batches:
        b_num = batch.get("batch_number", 0)
        b_applied_count = batch.get("applied_count", 0)
        b_vacancies = batch.get("vacancies", [])

        for idx, vac in enumerate(b_vacancies):
            if limit and total_vacancies_seen >= limit:
                break

            total_vacancies_seen += 1
            vid = str(vac.get("id", ""))
            if not vid:
                continue

            title = str(vac.get("title", "Untitled"))
            company = str(vac.get("company", "Unknown"))
            url = str(vac.get("url", ""))
            salary_raw = str(vac.get("salary", ""))
            category = str(vac.get("category", ""))
            tier = int(vac.get("tier", 2))
            sector = normalize_sector(category, title)
            s_min, s_max = parse_salary_range(salary_raw)

            # Check if this vacancy was applied
            is_applied = (
                vac.get("applied", False)
                or (vid in applied_report_ids)
                or (idx < b_applied_count)
            )

            if dry_run:
                continue

            # Upsert into vacancies
            cursor.execute("SELECT id FROM vacancies WHERE id = ?", (vid,))
            exists = cursor.fetchone()

            if exists:
                cursor.execute(
                    """
                    UPDATE vacancies 
                    SET title=?, company=?, url=?, tier=?, sector=?, salary_min=?, salary_max=?, salary_text=?, is_active=1
                    WHERE id=?
                """,
                    (title, company, url, tier, sector, s_min, s_max, salary_raw, vid),
                )
                updated_vacancies += 1
            else:
                cursor.execute(
                    """
                    INSERT INTO vacancies (id, title, company, url, source, tier, sector, salary_min, salary_max, salary_text, scraped_at, is_active)
                    VALUES (?, ?, ?, ?, 'hh.uz', ?, ?, ?, ?, ?, ?, 1)
                """,
                    (vid, title, company, url, tier, sector, s_min, s_max, salary_raw, now_iso),
                )
                new_vacancies += 1

            # Sync application record if applied
            if is_applied:
                cursor.execute("SELECT id, status FROM applications WHERE vacancy_id = ?", (vid,))
                app_row = cursor.fetchone()
                if app_row:
                    cursor.execute(
                        """
                        UPDATE applications
                        SET last_updated = ?, notes = coalesce(notes, '') || ' [Hermes sync]'
                        WHERE vacancy_id = ?
                    """,
                        (now_iso, vid),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO applications (vacancy_id, status, applied_at, cover_letter_sent, pdf_sent_in_chat, last_updated, notes)
                        VALUES (?, 'applied', ?, 1, 1, ?, 'Imported via Hermes Batch Queue')
                    """,
                        (vid, now_iso, now_iso),
                    )
                applications_synced += 1

    if not dry_run:
        conn.commit()
    conn.close()

    result = {
        "success": True,
        "code": Config.EXIT_SUCCESS,
        "queue_file": str(target_queue),
        "db_path": str(target_db),
        "vacancies_synced": total_vacancies_seen,
        "new_vacancies": new_vacancies,
        "updated_vacancies": updated_vacancies,
        "applications_synced": applications_synced,
        "dry_run": dry_run,
        "timestamp": now_iso,
    }
    log_event("HERMES_SYNC_SUCCESS", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync vacancies and applied statuses from Hermes Batch Queue to positions.db"
    )
    parser.add_argument(
        "--queue-file",
        type=str,
        default=None,
        help="Path to HERMES_BATCH_QUEUE.json (autodetected if omitted)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to target positions.db",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of vacancies processed (useful for testing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate run without writing to database",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )

    args = parser.parse_args()
    q_file = Path(args.queue_file) if args.queue_file else None
    d_path = Path(args.db_path) if args.db_path else None

    result = sync_hermes_queue(
        queue_path=q_file,
        db_path=d_path,
        dry_run=args.dry_run,
        limit=args.limit,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print(f"[OK] Hermes queue synchronized successfully:")
            print(f"     Source: {result['queue_file']}")
            print(f"     Target DB: {result['db_path']}")
            print(f"     Vacancies processed: {result['vacancies_synced']} ({result['new_vacancies']} new, {result['updated_vacancies']} updated)")
            print(f"     Applications tracked: {result['applications_synced']}")
        else:
            print(f"[ERROR] {result['error']}", file=sys.stderr)

    return result["code"]


if __name__ == "__main__":
    sys.exit(main())
