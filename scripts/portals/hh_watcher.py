"""
HeadHunter Uzbekistan Vacancy Watcher.

Monitors new postings on hh.uz for Tashkent finance and analytics roles,
classifies priority tiers (Tier 1 banks/corporations), and ingests into positions.db.

Usage:
    python scripts/portals/hh_watcher.py [--query "бизнес-аналитик"] [--limit 20] [--json]
"""

from __future__ import annotations
import argparse
import datetime
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import get_connection, init_database
from scripts.logger import log_event
from scripts.sync_hermes import normalize_sector, parse_salary_range

TIER_1_EMPLOYERS = [
    "банк", "bank", "kapital", "ipoteka", "tbc", "ravnaq", "hamkor", "sqb", 
    "uzum", "payme", "click", "beeline", "ucell", "murad buildings", "orient", 
    "korzinka", "makro", "deloitte", "kpmg", "pwc", "ey", "artel", "akfa"
]


def classify_tier(company_name: str) -> int:
    """Classifies tier: 1=Bank/Major Corp, 2=Mid company, 3=Small."""
    c_lower = company_name.lower()
    if any(k in c_lower for k in TIER_1_EMPLOYERS):
        return 1
    return 2


def parse_hh_search_snippet(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes raw HeadHunter API item into canonical vacancy dictionary."""
    vid = str(item.get("id", ""))
    title = str(item.get("name", "Untitled"))
    company = str(item.get("employer", {}).get("name", "Unknown"))
    url = str(item.get("alternate_url", f"https://hh.uz/vacancy/{vid}"))
    salary_dict = item.get("salary") or {}

    salary_text = ""
    s_min = salary_dict.get("from")
    s_max = salary_dict.get("to")
    curr = salary_dict.get("currency", "")
    if s_min or s_max:
        salary_text = f"{s_min or ''} - {s_max or ''} {curr}".strip()

    tier = classify_tier(company)
    sector = normalize_sector(title, title)

    return {
        "id": vid,
        "title": title,
        "company": company,
        "url": url,
        "source": "hh.uz",
        "tier": tier,
        "sector": sector,
        "salary_min": s_min,
        "salary_max": s_max,
        "salary_text": salary_text,
    }


def fetch_hh_vacancies(query: str = "бизнес-аналитик", limit: int = 20) -> List[Dict[str, Any]]:
    """Queries hh.uz public search API for Tashkent (area 2759)."""
    encoded_query = urllib.parse.quote(query)
    # Tashkent area = 2759 on HeadHunter
    url = f"https://api.hh.ru/vacancies?text={encoded_query}&area=2759&per_page={min(limit, 100)}"
    headers = {
        "User-Agent": "Resume-Job-Tracker/1.0 (aa998908550790@gmail.com)"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            items = data.get("items", [])
            return [parse_hh_search_snippet(it) for it in items[:limit]]
    except Exception as e:
        log_event("HH_FETCH_ERROR", {"query": query, "error": str(e)}, level="WARNING")
        return []


def ingest_hh_vacancies(
    query: str = "бизнес-аналитик",
    limit: int = 20,
    dry_run: bool = False,
    db_path: Path | None = None,
) -> Dict[str, Any]:
    """Ingests fresh HH vacancies into positions.db."""
    target_db = Path(db_path) if db_path else Config.DB_PATH
    init_database(target_db)

    vacancies = fetch_hh_vacancies(query=query, limit=limit)
    now_iso = datetime.datetime.now().isoformat()

    inserted = 0
    if not dry_run and vacancies:
        conn = get_connection(target_db)
        cursor = conn.cursor()
        for v in vacancies:
            cursor.execute("SELECT id FROM vacancies WHERE id = ?", (v["id"],))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO vacancies (id, title, company, url, source, tier, sector, salary_min, salary_max, salary_text, scraped_at, is_active)
                    VALUES (?, ?, ?, ?, 'hh.uz', ?, ?, ?, ?, ?, ?, 1)
                """,
                    (v["id"], v["title"], v["company"], v["url"], v["tier"], v["sector"], v["salary_min"], v["salary_max"], v["salary_text"], now_iso),
                )
                inserted += 1
        conn.commit()
        conn.close()

    result = {
        "success": True,
        "code": Config.EXIT_SUCCESS,
        "query": query,
        "found": len(vacancies),
        "inserted": inserted,
        "dry_run": dry_run,
        "vacancies": vacancies,
    }
    log_event("HH_INGESTION", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch and ingest fresh HeadHunter Uzbekistan vacancies")
    parser.add_argument("--query", type=str, default="бизнес-аналитик", help="Search keyword")
    parser.add_argument("--limit", type=int, default=20, help="Max results to fetch")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing to DB")
    parser.add_argument("--db-path", type=str, default=None, help="Custom DB path")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()
    db_target = Path(args.db_path) if args.db_path else None

    res = ingest_hh_vacancies(
        query=args.query,
        limit=args.limit,
        dry_run=args.dry_run,
        db_path=db_target,
    )

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"[OK] HH Watcher finished. Found: {res['found']}, Inserted: {res['inserted']}")

    return res["code"]


if __name__ == "__main__":
    sys.exit(main())
