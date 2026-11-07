"""
OLX Uzbekistan Job Scraper.

Fetches and normalizes job openings from OLX.uz (rabota section)
and inserts them into positions.db.

Usage:
    python scripts/portals/olx_scraper.py [--query "аналитик"] [--limit 20] [--json]
"""

from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import re
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


def parse_olx_listing_html(html_text: str) -> List[Dict[str, Any]]:
    """Lightweight stdlib parser for OLX listing cards."""
    results: List[Dict[str, Any]] = []

    # Match card containers or links
    pattern = re.compile(
        r'<a[^>]+href="([^"]+obyavlenie/[^"]+)"[^>]*>.*?<h6[^>]*>(.*?)</h6>',
        re.DOTALL | re.IGNORECASE,
    )

    for m in pattern.finditer(html_text):
        rel_url = m.group(1)
        raw_title = m.group(2).strip()

        # Clean tags
        clean_title = re.sub(r"<[^>]+>", "", raw_title).strip()
        full_url = rel_url if rel_url.startswith("http") else f"https://www.olx.uz{rel_url}"

        # Extract ID from URL
        id_match = re.search(r"-ID([a-zA-Z0-9]+)\.html", rel_url)
        vid = f"olx_{id_match.group(1)}" if id_match else f"olx_{hashlib.md5(full_url.encode()).hexdigest()[:8]}"

        results.append({
            "id": vid,
            "title": clean_title,
            "company": "OLX Employer",
            "url": full_url,
            "source": "olx",
            "tier": 2,
            "sector": normalize_sector(clean_title, clean_title),
            "salary_text": "",
        })

    return results


def fetch_olx_listings(query: str = "аналитик", limit: int = 20) -> List[Dict[str, Any]]:
    """Fetches job listings from OLX Uzbekistan."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.olx.uz/rabota/q-{encoded_query}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")
            listings = parse_olx_listing_html(html)
            return listings[:limit]
    except Exception as e:
        log_event("OLX_FETCH_ERROR", {"query": query, "error": str(e)}, level="WARNING")
        return []


def ingest_olx_vacancies(
    query: str = "аналитик",
    limit: int = 20,
    dry_run: bool = False,
    db_path: Path | None = None,
) -> Dict[str, Any]:
    """Ingests scraped OLX vacancies into positions.db."""
    target_db = Path(db_path) if db_path else Config.DB_PATH
    init_database(target_db)

    listings = fetch_olx_listings(query=query, limit=limit)
    now_iso = datetime.datetime.now().isoformat()

    inserted = 0
    if not dry_run and listings:
        conn = get_connection(target_db)
        cursor = conn.cursor()
        for item in listings:
            cursor.execute("SELECT id FROM vacancies WHERE id = ?", (item["id"],))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO vacancies (id, title, company, url, source, tier, sector, salary_text, scraped_at, is_active)
                    VALUES (?, ?, ?, ?, 'olx', ?, ?, ?, ?, 1)
                """,
                    (item["id"], item["title"], item["company"], item["url"], item["tier"], item["sector"], item["salary_text"], now_iso),
                )
                inserted += 1
        conn.commit()
        conn.close()

    result = {
        "success": True,
        "code": Config.EXIT_SUCCESS,
        "query": query,
        "found": len(listings),
        "inserted": inserted,
        "dry_run": dry_run,
        "listings": listings,
    }
    log_event("OLX_INGESTION", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape and ingest OLX Uzbekistan job vacancies")
    parser.add_argument("--query", type=str, default="аналитик", help="Search keyword")
    parser.add_argument("--limit", type=int, default=20, help="Max results to import")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing to DB")
    parser.add_argument("--db-path", type=str, default=None, help="Custom DB path")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()
    db_target = Path(args.db_path) if args.db_path else None

    res = ingest_olx_vacancies(
        query=args.query,
        limit=args.limit,
        dry_run=args.dry_run,
        db_path=db_target,
    )

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"[OK] OLX Scraper finished. Found: {res['found']}, Inserted: {res['inserted']}")

    return res["code"]


if __name__ == "__main__":
    sys.exit(main())
