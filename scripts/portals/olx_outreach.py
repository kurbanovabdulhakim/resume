"""
OLX Job Outreach & Contact Extractor.

Inspects ingested OLX vacancies, extracts direct recruiter contacts (Telegram, Phone),
generates humanized outreach drafts, and logs them into positions.db.

Usage:
    python scripts/portals/olx_outreach.py [--limit 10] [--json]
"""

from __future__ import annotations
import argparse
import datetime
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import get_connection, init_database
from scripts.logger import log_event


def generate_humanized_letter(title: str, company: str, category: str = "", snippet: str = "") -> str:
    """Produces a clean, non-robotic default Russian outreach message grounded in candidate profile."""
    return (
        f"Здравствуйте! Меня заинтересовала вакансия «{title}» в «{company}».\n\n"
        f"У меня экономическое образование (ТФИ) и практический опыт операционного управления и финансового контроля: "
        f"в Explorer Logistics (CEO/COO) настроил управленческий P&L и снизил накладные расходы на 18%, "
        f"а в АКБ «Равнак-банк» систематизировал регламенты сервиса и сократил операционные ошибки на 22%.\n\n"
        f"Буду рад обсудить задачи и при необходимости отправить полное резюме. "
        f"С уважением, {Config.CANDIDATE_NAME} ({Config.CANDIDATE_PHONE}, {Config.CANDIDATE_TELEGRAM})."
    )


def fetch_page_html(url: str, timeout: int = 10) -> str:
    """Fetches HTML text for an OLX posting."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def extract_contacts_from_html(html_text: str) -> Dict[str, Any]:
    """Extracts Telegram handles, phone numbers, and emails from OLX vacancy HTML."""
    # Strip HTML tags for clean text analysis
    clean_text = re.sub(r"<[^>]+>", " ", html_text)

    # 1. Telegram usernames (avoiding standard web keywords)
    tg_pattern = re.compile(r'(?:t\.me/|@)([a-zA-Z0-9_]{5,32})', re.IGNORECASE)
    excluded_handles = {'olx', 'telegram', 'channel', 'support', 'help', 'bot', 'admin'}
    found_tg = []
    for match in tg_pattern.finditer(clean_text):
        handle = match.group(1)
        if handle.lower() not in excluded_handles:
            found_tg.append(f"@{handle}")

    # 2. Uzbekistan phone numbers
    phone_pattern = re.compile(r'(?:\+?998[\s-]?)?(?:\(?\d{2}\)?[\s-]?)?\d{3}[\s-]?\d{2}[\s-]?\d{2}')
    raw_phones = phone_pattern.findall(clean_text)
    cleaned_phones = []
    for p in raw_phones:
        digits = re.sub(r'\D', '', p)
        if len(digits) == 9:
            cleaned_phones.append(f"+998{digits}")
        elif len(digits) == 12 and digits.startswith('998'):
            cleaned_phones.append(f"+{digits}")

    return {
        "telegrams": list(dict.fromkeys(found_tg)),
        "phones": list(dict.fromkeys(cleaned_phones))
    }


def process_pending_olx_vacancies(limit: int = 10, db_path: Path | None = None) -> Dict[str, Any]:
    """Inspects pending OLX vacancies, fetches description, and prepares outreach."""
    target_db = Path(db_path) if db_path else Config.DB_PATH
    init_database(target_db)

    conn = get_connection(target_db)
    cursor = conn.cursor()

    # Find OLX vacancies that do not have a finalized application record yet
    query = """
        SELECT v.id, v.title, v.company, v.url, v.sector
        FROM vacancies v
        LEFT JOIN applications a ON v.id = a.vacancy_id
        WHERE v.source = 'olx' AND v.is_active = 1 AND a.id IS NULL
        LIMIT ?
    """
    cursor.execute(query, (limit,))
    rows = cursor.fetchall()
    conn.close()

    results = []

    for row in rows:
        vid, title, company, url, sector = row
        contacts: Dict[str, Any] = {"telegrams": [], "phones": []}
        try:
            html = fetch_page_html(url)
            contacts = extract_contacts_from_html(html)
        except Exception as e:
            contacts = {"error": str(e), "telegrams": [], "phones": []}

        # Generate humanized outreach draft
        letter = generate_humanized_letter(title, company, sector or "")

        note_parts = []
        if contacts.get("telegrams"):
            note_parts.append(f"TG: {', '.join(contacts['telegrams'])}")
        if contacts.get("phones"):
            note_parts.append(f"Phone: {', '.join(contacts['phones'])}")

        status = "ready_for_outreach" if note_parts else "needs_in_site_message"
        notes = " | ".join(note_parts) or "Direct contact in OLX chat"

        results.append({
            "id": vid,
            "title": title,
            "company": company,
            "url": url,
            "status": status,
            "notes": notes,
            "contacts": contacts,
            "draft_letter": letter,
            "sample_message": letter[:120] + "...",
        })

    summary = {
        "success": True,
        "processed": len(results),
        "results": results
    }
    log_event("OLX_OUTREACH_PROCESSED", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Process and extract contacts for OLX vacancies")
    parser.add_argument("--limit", type=int, default=10, help="Number of OLX vacancies to process")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    summary = process_pending_olx_vacancies(limit=args.limit)
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"[OK] OLX Outreach processed {summary['processed']} vacancies.")
        for r in summary['results']:
            print(f"  • {r['title']} -> {r['status']} ({r['contacts'].get('telegrams') or r['contacts'].get('phones') or 'OLX Chat'})")

    return 0


if __name__ == "__main__":
    sys.exit(main())

