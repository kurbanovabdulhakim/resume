"""
Audit and Repair Negotiations Cover Letters.

Scans https://tashkent.hh.uz/applicant/negotiations across all pages.
Identifies any negotiation where the application has '1', empty, or gibberish ('бельберда')
instead of a real candidate cover letter.

Can compile an exhaustive audit list (--scan-only) or deliver tailored cover letters
directly into the chat (--all-in-one or default).
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
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service

from scripts.config import Config
from scripts.dashboard import build_dashboard_artifacts
from scripts.hh_apply import _find_cached_msedgedriver
from scripts.hh_negotiations_chat_sender import (
    extract_chat_metadata,
    generate_tailored_letter,
    type_human_paced_chat,
)
from scripts.init_db import get_connection, init_database
from scripts.logger import log_event


AUDIT_FILE = Config.DATA_DIR / "belberda_vacancies.json"


def classify_chat_status(messages: List[str]) -> Dict[str, Any]:
    """Analyzes message history. Returns classification: 'has_letter', 'belberda', or 'empty'."""
    if not messages:
        return {"category": "empty", "reason": "No messages found in chat", "initial_text": ""}

    # 1. Did the candidate already send a real cover letter?
    for msg in messages:
        t = msg.strip().lower()
        if any(kw in t for kw in ("explorer logistics", "равнак-банк", "курбанов", "абдулхаким")):
            return {"category": "has_letter", "reason": "Contains verified candidate cover letter", "initial_text": msg[:80]}

    # 2. Check for "1" or gibberish / trivial placeholders in application message
    for msg in messages:
        t = msg.strip()
        lines = [l.strip() for l in t.split("\n") if l.strip()]

        # Check if message is literally "1"
        if t == "1" or "1" in lines:
            return {"category": "belberda", "reason": "Application message is literal '1'", "initial_text": t}

        # Check regex match for response with 1
        if re.search(r"отклик на\s+вакансию\s*\n+1\b", t.lower()):
            return {"category": "belberda", "reason": "Application response is '1'", "initial_text": t}

        # If it's a response with very short gibberish (<= 15 chars)
        if "отклик на вакансию" in t.lower() and len(t) < 50:
            sub = t.lower().replace("отклик на вакансию", "").strip()
            if len(sub) <= 10 or sub in ("1", "0", ".", "-", "+", "!", "й", "ф"):
                return {"category": "belberda", "reason": f"Trivial/placeholder text: '{sub}'", "initial_text": t}

    # If messages exist (e.g. quick reply chips or employer greeting) but candidate never sent letter
    return {"category": "belberda", "reason": "No candidate cover letter sent", "initial_text": messages[0][:60] if messages else ""}


def run_audit_and_repair(
    driver: Any,
    start_page: int = 0,
    max_pages: int = 12,
    scan_only: bool = False,
    dry_run: bool = False,
    fast_typing: bool = False,
    only_today: bool = True,
) -> Dict[str, Any]:
    """Scans negotiations pages, identifies '1'/belberda vacancies, and repairs them via chat."""
    flagged_list: List[Dict[str, Any]] = []
    scanned_total = 0
    repaired_count = 0

    print(f"\n[AUDIT] Starting scan from page {start_page + 1} across up to {max_pages} pages...", flush=True)

    for page_idx in range(start_page, max_pages):
        page_url = f"https://tashkent.hh.uz/applicant/negotiations?page={page_idx}"
        driver.get(page_url)
        time.sleep(2.5)

        btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='open_chat']")
        if not btns:
            print(f"[AUDIT] Page {page_idx}: No open_chat buttons found. Ending scan.", flush=True)
            break

        print(f"\n[AUDIT PAGE {page_idx + 1}] Found {len(btns)} negotiation cards.", flush=True)

        for card_idx in range(len(btns)):
            scanned_total += 1
            btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='open_chat']")
            if card_idx >= len(btns):
                break
            btn = btns[card_idx]

            # Click open_chat
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(2.0)

            iframes = driver.find_elements(By.CSS_SELECTOR, "iframe.chatik-integration-iframe")
            if not iframes:
                continue

            driver.switch_to.frame(iframes[0])
            time.sleep(1.2)

            try:
                msgs = driver.execute_script("""
                    const m = [];
                    document.querySelectorAll("[data-qa*='message'], [class*='message'], [class*='Message']").forEach(el => {
                        const t = (el.innerText || '').trim();
                        if (t && !m.includes(t)) m.push(t);
                    });
                    return m;
                """)

                links = driver.execute_script("""
                    return Array.from(document.querySelectorAll('a')).map(a => ({href: a.href, text: (a.innerText || '').trim()}));
                """)
                header_text = driver.execute_script("""
                    const h = document.querySelector('[class*="header"], [class*="Header"], [data-qa*="header"]');
                    return h ? (h.innerText || '') : '';
                """)

                meta = extract_chat_metadata(links, header_text)
                comp = meta["company"] or f"Компания {card_idx + 1}"
                title = meta["title"] or f"Позиция {card_idx + 1}"
                vid = meta["vacancy_id"]

                classification = classify_chat_status(msgs)
                cat = classification["category"]

                if cat in ("belberda", "empty"):
                    item = {
                        "vacancy_id": vid,
                        "company": comp,
                        "title": title,
                        "reason": classification["reason"],
                        "initial_text": classification["initial_text"][:100],
                        "page": page_idx,
                        "card_index": card_idx,
                        "status": "flagged",
                    }
                    flagged_list.append(item)
                    print(f"  [!] БЕЛЬБЕРДА #{len(flagged_list)}: {comp} — {title} (ID: {vid}) | {classification['reason']}", flush=True)

                    # Deliver cover letter if not scan_only
                    if not scan_only:
                        letter = generate_tailored_letter(title, comp, vid)
                        print(f"      -> Генерация письма: «{letter[:80]}...»", flush=True)

                        tas = driver.find_elements(By.CSS_SELECTOR, "textarea[data-qa='text-input'], textarea")
                        if tas:
                            ta = tas[0]
                            if fast_typing:
                                ta.send_keys(letter)
                            else:
                                type_human_paced_chat(ta, letter, word_delay_range=(0.8, 1.8))
                            time.sleep(1.0)

                            send_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='chatik-do-send-message'], button[type='submit']")
                            if send_btns:
                                if not dry_run:
                                    driver.execute_script("arguments[0].click();", send_btns[0])
                                    time.sleep(2.0)
                                    repaired_count += 1
                                    item["status"] = "sent"
                                    print(f"      -> [УСПЕШНО ОТПРАВЛЕНО] Сопроводительное письмо доставлено в чат!", flush=True)

                                    # Update DB
                                    if vid:
                                        try:
                                            conn = get_connection(Config.DB_PATH)
                                            conn.execute(
                                                """
                                                UPDATE applications
                                                SET cover_letter_sent = ?,
                                                    notes = CASE
                                                        WHEN notes IS NULL OR notes = '' THEN 'Cover letter repaired and sent via chat'
                                                        WHEN notes NOT LIKE '%repaired%' THEN notes || '; Cover letter repaired and sent via chat'
                                                        ELSE notes
                                                    END
                                                WHERE vacancy_id = ?
                                                """,
                                                (letter, str(vid)),
                                            )
                                            conn.commit()
                                            conn.close()
                                        except Exception as exc:
                                            log_event("warn", f"Could not update DB for {vid}: {exc}")
                                else:
                                    item["status"] = "dry_run"
                                    print(f"      -> [DRY RUN] Отправка пропущена (тестовый режим).", flush=True)

                                if not fast_typing:
                                    time.sleep(random.uniform(2.0, 4.0))
                else:
                    print(f"  [OK] {comp} — {title}: Реальное письмо уже в чате, пропускаем.", flush=True)

            finally:
                driver.switch_to.default_content()
                try:
                    driver.execute_script("""
                        const closeBtn = document.querySelector("button[data-qa='chatik-close-chatik']");
                        if (closeBtn) closeBtn.click();
                    """)
                    time.sleep(0.8)
                except Exception:
                    pass

    # Save to JSON
    audit_data = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_scanned": scanned_total,
        "total_flagged": len(flagged_list),
        "total_repaired": repaired_count,
        "items": flagged_list,
    }
    with open(AUDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, ensure_ascii=False, indent=2)

    print(f"\n=== AUDIT SUMMARY ===", flush=True)
    print(f"Всего проверено диалогов: {scanned_total}")
    print(f"Выявлено вакансий с бельбердой / '1': {len(flagged_list)}")
    print(f"Отправлено новых сопроводительных писем: {repaired_count}")
    print(f"Список сохранен в: {AUDIT_FILE}")

    return audit_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and repair HH negotiations cover letters.")
    parser.add_argument("--scan-only", action="store_true", help="Only scan and compile list without sending.")
    parser.add_argument("--start-page", type=int, default=0, help="Starting page index (0-indexed).")
    parser.add_argument("--max-pages", type=int, default=12, help="Max pages to scan on negotiations.")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without clicking send.")
    parser.add_argument("--fast-typing", action="store_true", help="Skip typing delay.")
    parser.add_argument("--visible", action="store_true", help="Show browser window.")
    args = parser.parse_args()

    opts = Options()
    opts.add_argument(f"--user-data-dir={Config.HH_SESSION_PROFILE_DIR}")
    if not args.visible:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1200,900")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")

    edge_bin = Config.get_edge_binary()
    if edge_bin:
        opts.binary_location = str(edge_bin)

    cached = _find_cached_msedgedriver()
    driver = webdriver.Edge(service=Service(executable_path=str(cached)), options=opts) if cached else webdriver.Edge(options=opts)

    try:
        run_audit_and_repair(
            driver=driver,
            start_page=args.start_page,
            max_pages=args.max_pages,
            scan_only=args.scan_only,
            dry_run=args.dry_run,
            fast_typing=args.fast_typing,
        )
    finally:
        driver.quit()

    try:
        build_dashboard_artifacts()
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
