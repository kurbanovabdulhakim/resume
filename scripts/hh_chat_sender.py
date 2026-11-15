"""
HeadHunter (hh.uz) Direct Chat Cover Letter Sender.

Enters applicant-employer negotiation topics (`/applicant/negotiations/topic?topicId=...`)
for previously submitted applications and delivers the tailored cover letter directly
into the employer chat thread.

Negotiation chat messages do not trigger the vacancy application rate limit or picture CAPTCHAs.

Usage:
    python scripts/hh_chat_sender.py --list-pending --json
    python scripts/hh_chat_sender.py --vacancy-id 139144391 --dry-run
    python scripts/hh_chat_sender.py --vacancy-id 139144391
    python scripts/hh_chat_sender.py --all-applied --limit 10
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.dashboard import build_dashboard_artifacts
from scripts.init_db import get_connection, init_database
from scripts.logger import log_event


def get_pending_chat_vacancies(
    queue_path: Optional[Path] = None,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Returns applied vacancies from queue that have cover letters not yet sent via chat."""
    q_path = Path(queue_path) if queue_path else Config.DATA_DIR / "hh_autonomy_queue.json"
    t_db = Path(db_path) if db_path else Config.DB_PATH

    if not q_path.exists():
        return []

    try:
        with open(q_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    items = data.get("items", {})
    if isinstance(items, list):
        items_dict = {item.get("vacancy_id"): item for item in items if isinstance(item, dict)}
    elif isinstance(items, dict):
        items_dict = items
    else:
        items_dict = {}

    # Check DB notes to filter out already-sent
    sent_in_db = set()
    if t_db.exists():
        try:
            conn = sqlite3.connect(t_db)
            c = conn.cursor()
            c.execute(
                "SELECT vacancy_id FROM applications WHERE notes LIKE '%Cover letter sent via chat%' OR notes LIKE '%chat%'"
            )
            for row in c.fetchall():
                sent_in_db.add(str(row[0]))
            conn.close()
        except Exception:
            pass

    pending = []
    for vid, item in items_dict.items():
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        if status != "applied":
            continue
        if str(vid) in sent_in_db or item.get("cover_letter_sent_to_chat"):
            continue

        letter = item.get("cover_letter", "")
        # Only include if letter is actual text (not "1" or boolean)
        if isinstance(letter, str) and len(letter.strip()) > 10 and letter.strip() not in ("1", "0"):
            pending.append(
                {
                    "vacancy_id": str(vid),
                    "title": item.get("title", ""),
                    "company": item.get("company", ""),
                    "url": item.get("url") or f"https://tashkent.hh.uz/vacancy/{vid}",
                    "cover_letter": letter,
                }
            )

    return pending


def send_chat_cover_letter(
    driver: Any,
    vacancy_id: str,
    cover_letter: str,
    db_path: Optional[Path] = None,
    fast_typing: bool = False,
    dry_run: bool = False,
    topic_url: Optional[str] = None,
    word_delay_range: Tuple[float, float] = (1.5, 2.5),
) -> Dict[str, Any]:
    """Navigates to vacancy or topic, types cover letter into employer chat, and sends."""
    from selenium.webdriver.common.by import By

    target_db = Path(db_path) if db_path else Config.DB_PATH
    resolved_topic = topic_url

    # 1. If not already on topic page, navigate to vacancy page to find the topic link
    current_url = getattr(driver, "current_url", "")
    if not resolved_topic and "/applicant/negotiations/topic" not in current_url:
        vac_url = f"https://tashkent.hh.uz/vacancy/{vacancy_id}"
        driver.get(vac_url)
        if not fast_typing:
            time.sleep(random.uniform(1.0, 2.0))

        # Look for topic link
        topic_elements = driver.find_elements(
            By.CSS_SELECTOR,
            "[data-qa='vacancy-response-link-view-topic'], a[href*='/applicant/negotiations/topic'], a[href*='topicId']",
        )
        if not topic_elements:
            # Check if this vacancy was not applied or button not rendered
            return {
                "status": "error",
                "vacancy_id": vacancy_id,
                "detail": "Negotiation topic link not found on vacancy page. Ensure application was submitted.",
            }

        topic_el = topic_elements[0]
        resolved_topic = topic_el.get_attribute("href")
        if resolved_topic:
            driver.get(resolved_topic)
        else:
            topic_el.click()

    if not fast_typing:
        time.sleep(random.uniform(1.2, 2.2))

    # 2. Check for deduplication / existing messages in chat history
    msg_elements = driver.find_elements(
        By.CSS_SELECTOR,
        "[data-qa='chat-message'], [data-qa*='negotiations-message'], .chat-message",
    )
    letter_sample = cover_letter.strip()[:40].lower() if cover_letter else ""
    for el in msg_elements:
        try:
            txt = getattr(el, "text", "") or ""
            if letter_sample and letter_sample in txt.lower():
                return {
                    "status": "already_sent",
                    "vacancy_id": vacancy_id,
                    "detail": "Cover letter already present in chat messages",
                    "topic_url": resolved_topic or getattr(driver, "current_url", ""),
                }
        except Exception:
            pass

    # 3. Locate chat textarea
    textareas = driver.find_elements(
        By.CSS_SELECTOR,
        "textarea[data-qa='negotiations-chat-input'], textarea[data-qa='chat-input-textarea'], textarea[data-qa*='chat-input'], textarea",
    )
    if not textareas:
        return {
            "status": "error",
            "vacancy_id": vacancy_id,
            "detail": "Chat textarea not found on topic page",
            "topic_url": resolved_topic or getattr(driver, "current_url", ""),
        }

    chat_input = textareas[0]

    # 4. Type the cover letter
    if fast_typing:
        chat_input.send_keys(cover_letter)
    else:
        # Natural human typing
        from scripts.hh_apply import type_human_paced_text

        type_human_paced_text(
            chat_input,
            cover_letter,
            word_delay_range=word_delay_range,
        )

    # 5. Locate send button
    send_buttons = driver.find_elements(
        By.CSS_SELECTOR,
        "button[data-qa='negotiations-chat-send'], button[data-qa*='chat-send'], button[data-qa*='send'], button[type='submit']",
    )
    if not send_buttons:
        return {
            "status": "error",
            "vacancy_id": vacancy_id,
            "detail": "Chat send button not found on topic page",
            "topic_url": resolved_topic or getattr(driver, "current_url", ""),
        }

    send_btn = send_buttons[0]

    # 6. Click send if not dry run
    if not dry_run:
        send_btn.click()
        if not fast_typing:
            time.sleep(random.uniform(1.0, 2.0))

        # 7. Update SQLite DB
        try:
            init_database(target_db)
            conn = get_connection(target_db)
            conn.execute(
                """
                UPDATE applications
                SET cover_letter_sent = 1,
                    notes = CASE
                        WHEN notes IS NULL OR notes = '' THEN 'Cover letter sent via chat'
                        WHEN notes NOT LIKE '%Cover letter sent via chat%' THEN notes || '; Cover letter sent via chat'
                        ELSE notes
                    END
                WHERE vacancy_id = ?
                """,
                (str(vacancy_id),),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            log_event("warn", f"Could not update DB for chat send on {vacancy_id}: {exc}")

        # 8. Update queue file if exists
        try:
            q_file = Config.DATA_DIR / "hh_autonomy_queue.json"
            if q_file.exists():
                with open(q_file, "r", encoding="utf-8") as f:
                    q_data = json.load(f)
                items = q_data.get("items", {})
                if str(vacancy_id) in items and isinstance(items[str(vacancy_id)], dict):
                    items[str(vacancy_id)]["cover_letter_sent_to_chat"] = True
                    items[str(vacancy_id)]["detail"] = "Cover letter sent to employer chat"
                    items[str(vacancy_id)]["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                    with open(q_file, "w", encoding="utf-8") as f:
                        json.dump(q_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return {
        "status": "sent" if not dry_run else "dry_run",
        "vacancy_id": str(vacancy_id),
        "topic_url": resolved_topic or getattr(driver, "current_url", ""),
        "dry_run": dry_run,
    }


def connect_or_launch_edge(port: Optional[int] = None) -> Any:
    """Connects to existing Edge with remote debugging or launches new Edge instance."""
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.edge.service import Service as EdgeService
    from scripts.hh_apply import _find_cached_msedgedriver

    opts = EdgeOptions()
    if port:
        opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    else:
        profile_dir = Config.HH_SESSION_PROFILE_DIR
        profile_dir.mkdir(parents=True, exist_ok=True)
        opts.add_argument(f"--user-data-dir={profile_dir}")
        opts.add_argument("--window-size=1120,860")
        opts.add_argument("--window-position=360,20")
        opts.add_argument("--no-first-run")
        opts.add_argument("--no-default-browser-check")

        edge_bin = Config.get_edge_binary()
        if edge_bin:
            opts.binary_location = str(edge_bin)

    cached_driver = _find_cached_msedgedriver()
    if cached_driver:
        driver = webdriver.Edge(service=EdgeService(executable_path=str(cached_driver)), options=opts)
    else:
        driver = webdriver.Edge(options=opts)

    driver.set_page_load_timeout(30)
    return driver


def main() -> int:
    parser = argparse.ArgumentParser(description="HeadHunter direct chat cover letter sender.")
    parser.add_argument("--vacancy-id", type=str, help="Specific vacancy ID to send cover letter to.")
    parser.add_argument("--all-applied", action="store_true", help="Send cover letters to all pending applied vacancies.")
    parser.add_argument("--limit", type=int, default=0, help="Max number of vacancies to process (0 = all).")
    parser.add_argument("--list-pending", action="store_true", help="List all applied vacancies pending chat delivery.")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without sending message or updating DB.")
    parser.add_argument("--fast-typing", action="store_true", help="Fast typing without human delay.")
    parser.add_argument("--port", type=int, default=None, help="Connect to running Edge debug port (e.g. 9222).")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Output results in JSON format.")
    args = parser.parse_args()

    # List pending
    if args.list_pending:
        pending = get_pending_chat_vacancies()
        if args.as_json:
            print(json.dumps({"total": len(pending), "vacancies": pending}, ensure_ascii=False, indent=2))
        else:
            print(f"=== Pending Vacancies for Chat Cover Letter ({len(pending)}) ===")
            for item in pending:
                print(f"[{item['vacancy_id']}] {item['company']} — {item['title']}")
        return 0

    pending_list = []
    if args.vacancy_id:
        # Load specific vacancy cover letter from queue
        q_file = Config.DATA_DIR / "hh_autonomy_queue.json"
        letter = ""
        comp = ""
        title = ""
        if q_file.exists():
            try:
                with open(q_file, "r", encoding="utf-8") as f:
                    q_data = json.load(f)
                it = q_data.get("items", {}).get(str(args.vacancy_id), {})
                letter = it.get("cover_letter", "")
                comp = it.get("company", "")
                title = it.get("title", "")
            except Exception:
                pass
        if not letter or letter in ("1", "0"):
            print(f"[ERROR] No valid cover letter found in queue for vacancy {args.vacancy_id}", file=sys.stderr)
            return 1
        pending_list.append({"vacancy_id": str(args.vacancy_id), "cover_letter": letter, "company": comp, "title": title})
    elif args.all_applied:
        pending_list = get_pending_chat_vacancies()
        if args.limit > 0:
            pending_list = pending_list[: args.limit]
    else:
        parser.print_help()
        return 2

    if not pending_list:
        msg = {"status": "ok", "message": "No pending vacancies to send chat cover letters to.", "processed": 0}
        if args.as_json:
            print(json.dumps(msg, ensure_ascii=False))
        else:
            print(msg["message"])
        return 0

    # Launch or connect to browser
    print(f"[INIT] Connecting/Launching Edge to process {len(pending_list)} chat cover letters...", flush=True)
    driver = None
    try:
        driver = connect_or_launch_edge(port=args.port)
    except Exception as exc:
        print(f"[ERROR] Could not start or connect to Edge: {exc}", file=sys.stderr)
        return 1

    results = []
    try:
        for idx, item in enumerate(pending_list, 1):
            vid = item["vacancy_id"]
            comp = item.get("company", "")
            title = item.get("title", "")
            print(f"[{idx}/{len(pending_list)}] Sending chat letter to {comp} ({title}) [ID: {vid}]...", flush=True)

            res = send_chat_cover_letter(
                driver=driver,
                vacancy_id=vid,
                cover_letter=item["cover_letter"],
                fast_typing=args.fast_typing,
                dry_run=args.dry_run,
            )
            res["company"] = comp
            res["title"] = title
            results.append(res)
            print(f"    -> Result: {res.get('status')} | {res.get('detail', '')}", flush=True)

            if not args.fast_typing and idx < len(pending_list):
                pause = random.uniform(5.0, 10.0)
                print(f"    -> Pausing {pause:.1f}s before next chat message...", flush=True)
                time.sleep(pause)

    finally:
        # We leave browser open if user is watching or keep session alive
        pass

    # Refresh dashboard
    try:
        build_dashboard_artifacts()
    except Exception:
        pass

    if args.as_json:
        print(json.dumps({"results": results, "total": len(results)}, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
