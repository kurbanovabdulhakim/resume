"""
Update Application Status CLI.

Progresses a job application through recruitment stages:
applied -> viewed -> invited -> interview -> offer -> rejected / declined.

Usage:
    python scripts/update_status.py --vacancy-id ID --status interview [--notes "Notes"] [--json]
"""

from __future__ import annotations
import argparse
import datetime
import json
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

VALID_STATUSES = ("applied", "viewed", "invited", "interview", "offer", "rejected", "declined")


def update_application_status(
    vacancy_id: str,
    status: str,
    notes: str = "",
    cv_variant: Optional[str] = None,
    cover_letter_sent: Optional[int] = None,
    pdf_sent_in_chat: Optional[int] = None,
    db_path: Path | None = None,
) -> Dict[str, Any]:
    """Updates the status and metadata for an existing vacancy application."""
    target_db = Path(db_path) if db_path else Config.DB_PATH
    init_database(target_db)

    if status not in VALID_STATUSES:
        err_msg = f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}"
        log_event("UPDATE_STATUS_INVALID", {"error": err_msg, "vacancy_id": vacancy_id}, level="WARNING")
        return {"success": False, "error": err_msg, "code": Config.EXIT_ERROR}

    now_iso = datetime.datetime.now().isoformat()

    try:
        conn = get_connection(target_db)
        cursor = conn.cursor()

        # Check if vacancy exists
        cursor.execute("SELECT id, title, company FROM vacancies WHERE id = ?", (vacancy_id,))
        vac = cursor.fetchone()
        if not vac:
            conn.close()
            err_msg = f"Vacancy ID '{vacancy_id}' not found in vacancies table."
            log_event("UPDATE_STATUS_NOT_FOUND", {"error": err_msg, "vacancy_id": vacancy_id}, level="WARNING")
            return {"success": False, "error": err_msg, "code": Config.EXIT_NO_DATA}

        # Check if application exists
        cursor.execute("SELECT id, status, notes FROM applications WHERE vacancy_id = ?", (vacancy_id,))
        app = cursor.fetchone()

        if app:
            app_id, prev_status, existing_notes = app
            combined_notes = (existing_notes or "") + (f"\n[{now_iso}] {notes}" if notes else "")
            cursor.execute(
                """
                UPDATE applications
                SET status = ?,
                    notes = ?,
                    last_updated = ?,
                    cv_variant = coalesce(?, cv_variant),
                    cover_letter_sent = coalesce(?, cover_letter_sent),
                    pdf_sent_in_chat = coalesce(?, pdf_sent_in_chat)
                WHERE id = ?
            """,
                (status, combined_notes.strip(), now_iso, cv_variant, cover_letter_sent, pdf_sent_in_chat, app_id),
            )
        else:
            prev_status = None
            cursor.execute(
                """
                INSERT INTO applications (vacancy_id, status, applied_at, cv_variant, cover_letter_sent, pdf_sent_in_chat, notes, last_updated)
                VALUES (?, ?, ?, ?, coalesce(?, 0), coalesce(?, 0), ?, ?)
            """,
                (vacancy_id, status, now_iso, cv_variant, cover_letter_sent, pdf_sent_in_chat, notes, now_iso),
            )

        conn.commit()
        conn.close()

        result = {
            "success": True,
            "code": Config.EXIT_SUCCESS,
            "vacancy_id": vacancy_id,
            "company": vac[2],
            "title": vac[1],
            "previous_status": prev_status,
            "status": status,
            "notes": notes,
            "last_updated": now_iso,
        }
        log_event("APPLICATION_STATUS_UPDATED", result)
        return result
    except Exception as e:
        err_msg = f"Failed to update status: {str(e)}"
        log_event("UPDATE_STATUS_ERROR", {"error": err_msg, "vacancy_id": vacancy_id}, level="ERROR")
        return {"success": False, "error": err_msg, "code": Config.EXIT_ERROR}


def main() -> int:
    parser = argparse.ArgumentParser(description="Update application recruitment status in positions.db")
    parser.add_argument("--vacancy-id", type=str, required=True, help="Vacancy ID")
    parser.add_argument("--status", type=str, required=True, choices=VALID_STATUSES, help="New status")
    parser.add_argument("--notes", type=str, default="", help="Additional notes or feedback")
    parser.add_argument("--cv-variant", type=str, default=None, help="CV variant used")
    parser.add_argument("--cover-letter-sent", type=int, choices=[0, 1], default=None, help="Cover letter sent (0/1)")
    parser.add_argument("--pdf-sent", type=int, choices=[0, 1], default=None, help="Resume PDF sent in chat (0/1)")
    parser.add_argument("--db-path", type=str, default=None, help="Path to positions.db")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()
    db_target = Path(args.db_path) if args.db_path else None

    res = update_application_status(
        vacancy_id=args.vacancy_id,
        status=args.status,
        notes=args.notes,
        cv_variant=args.cv_variant,
        cover_letter_sent=args.cover_letter_sent,
        pdf_sent_in_chat=args.pdf_sent,
        db_path=db_target,
    )

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        if res["success"]:
            print(f"[OK] Application updated: [{res['vacancy_id']}] {res['company']} — {res['title']}")
            print(f"     Status: {res.get('previous_status', 'none')} -> {res['status']}")
            if res.get("notes"):
                print(f"     Notes: {res['notes']}")
        else:
            print(f"[ERROR] {res['error']}", file=sys.stderr)

    return res["code"]


if __name__ == "__main__":
    sys.exit(main())
