"""
HeadHunter Negotiations List Chat Cover Letter Auto-Sender.

Scans applicant negotiations at https://tashkent.hh.uz/applicant/negotiations.
For any negotiation where the initial message was simply "1" (or empty/missing),
enters the chat and delivers a unique, personalized cover letter directly to the employer.

Usage:
    python scripts/hh_negotiations_chat_sender.py --dry-run --limit 5
    python scripts/hh_negotiations_chat_sender.py --limit 20
    python scripts/hh_negotiations_chat_sender.py --all-pages
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.dashboard import build_dashboard_artifacts
from scripts.hh_apply import _find_cached_msedgedriver, type_human_paced_text
from scripts.init_db import get_connection, init_database
from scripts.logger import log_event


def is_candidate_chat(messages: List[str]) -> bool:
    """Returns True if the negotiation chat contains '1' as application and lacks a real cover letter."""
    if not messages:
        return True

    # 1. Did the candidate already send a real cover letter?
    has_real_letter = False
    for msg in messages:
        t = msg.strip().lower()
        if any(kw in t for kw in ("explorer logistics", "равнак-банк", "курбанов", "абдулхаким")):
            has_real_letter = True
            break

    if has_real_letter:
        return False

    # 2. Check if the initial response was '1' or trivial
    for msg in messages:
        t = msg.strip()
        if re.search(r"отклик на\s+вакансию\s*\n+1\b", t.lower()) or "\n\n1\n\n" in t or "\n1\n" in t:
            return True
        lines = [l.strip() for l in t.split("\n") if l.strip()]
        if "1" in lines:
            return True

    return False


def extract_chat_metadata(links: List[Dict[str, str]], header_text: str = "") -> Dict[str, str]:
    """Extracts vacancy_id, company, and vacancy title from chat links and header text."""
    vid = ""
    comp = ""
    title = ""

    for l in links:
        href = l.get("href", "")
        text = l.get("text", "").strip()

        # Check vacancy link
        if "/vacancy/" in href:
            m = re.search(r"/vacancy/(\d+)", href)
            if m:
                vid = m.group(1)
        # Check employer link
        if "/employer/" in href and text and not comp:
            comp = text

    # Parse header text for title and company if not found
    if header_text:
        lines = [line.strip() for line in header_text.split("\n") if line.strip()]
        for idx, line in enumerate(lines):
            if line.lower() == "вакансия" and idx + 1 < len(lines):
                title = lines[idx + 1]
            elif not comp and idx == 0 and "онлайн" not in line.lower() and "вакансия" not in line.lower():
                comp = line

    return {
        "vacancy_id": vid,
        "company": comp,
        "title": title,
    }


def generate_tailored_letter(title: str, company: str, vacancy_id: str = "") -> str:
    """Fetches letter from queue or generates a unique, humanized cover letter via Ollama."""
    # 1. Check if queue already has pre-generated tailored letter
    q_file = Config.DATA_DIR / "hh_autonomy_queue.json"
    if q_file.exists():
        try:
            with open(q_file, "r", encoding="utf-8") as f:
                q_data = json.load(f)
            items = q_data.get("items", {})
            if vacancy_id and str(vacancy_id) in items:
                let = items[str(vacancy_id)].get("cover_letter", "")
                if isinstance(let, str) and len(let.strip()) > 50 and let.strip() not in ("1", "0"):
                    return let.strip()
            # Try matching by company and title
            for it in items.values():
                if isinstance(it, dict) and it.get("company") == company and it.get("title") == title:
                    let = it.get("cover_letter", "")
                    if isinstance(let, str) and len(let.strip()) > 50 and let.strip() not in ("1", "0"):
                        return let.strip()
        except Exception:
            pass

    # 2. Try Ollama generation
    prompt = f"""Ты Абдулхаким Курбанов. Напиши краткое, сильное, персонализированное сопроводительное письмо на русском языке на вакансию «{title}» в компанию «{company}».
Опыт кандидата:
- Explorer Logistics (CEO/COO): регламентировал операционные процессы, ускорил обработку заказов на 25%, построил управленческий P&L и снизил накладные расходы на 18%.
- АКБ «Равнак-банк» (Супервайзер стандартов обслуживания): контроль операционных стандартов, снижение ошибок на 22%.
- Навыки: SQL, Excel, Power BI, Python, 1C.
Требования к тексту:
- Строго без искусственных восторгов ('с большим энтузиазмом', 'идеально подхожу').
- Без лишней воды, 2-3 коротких абзаца.
- Формат:
Здравствуйте! Меня заинтересовала позиция «{title}» в «{company}».
[1-2 конкретных абзаца с привязкой опыта к задачам]
Буду рад обсудить задачи на собеседовании.
С уважением,
Абдулхаким Курбанов
"""
    try:
        req_data = json.dumps({
            "model": "qwen2.5-coder:7b",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.4, "top_p": 0.9}
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            gen_text = data.get("response", "").strip()
            if len(gen_text) > 80:
                return gen_text
    except Exception:
        pass

    # 3. Deterministic high-quality fallback adhering to humanizer rule
    return (
        f"Здравствуйте! Меня заинтересовала вакансия «{title}» в компании «{company}».\n\n"
        f"В Explorer Logistics я регламентировал операционные процессы, ускорил обработку заказов на 25% "
        f"и выстроил управленческий P&L, сократив накладные расходы на 18%. Ранее в АКБ «Равнак-банк» "
        f"контролировал стандарты обслуживания и снизил операционные ошибки на 22%.\n\n"
        f"Уверенно работаю с SQL, Excel, Power BI и Python. Буду рад обсудить задачи на собеседовании.\n\n"
        f"С уважением,\nАбдулхаким Курбанов"
    )


def type_human_paced_chat(
    element: Any,
    text: str,
    word_delay_range: Tuple[float, float] = (1.5, 2.5),
) -> None:
    """Types word by word with configurable human delay per word."""
    if not text:
        return
    tokens = re.findall(r"\S+|\s+", text)
    min_w, max_w = word_delay_range
    for token in tokens:
        element.send_keys(token)
        if not token.isspace():
            time.sleep(random.uniform(min_w, max_w))


def process_negotiation_card(
    driver: Any,
    card_button: Any,
    db_path: Path,
    dry_run: bool = False,
    fast_typing: bool = False,
    word_delay_range: Tuple[float, float] = (1.5, 2.5),
) -> Dict[str, Any]:
    """Clicks open_chat on a card, inspects messages, and sends unique cover letter if candidate."""
    from selenium.webdriver.common.by import By

    # Click open_chat
    driver.execute_script("arguments[0].click();", card_button)
    time.sleep(2.5)

    # Locate chat iframe
    iframes = driver.find_elements(By.CSS_SELECTOR, "iframe.chatik-integration-iframe")
    if not iframes:
        return {"status": "error", "detail": "Chat iframe not opened"}

    chat_iframe = iframes[0]
    driver.switch_to.frame(chat_iframe)
    time.sleep(1.5)

    try:
        # Extract messages
        msgs = driver.execute_script("""
            const m = [];
            document.querySelectorAll("[data-qa*='message'], [class*='message'], [class*='Message']").forEach(el => {
                const t = (el.innerText || '').trim();
                if (t && !m.includes(t)) m.push(t);
            });
            return m;
        """)

        # Extract links and header
        links = driver.execute_script("""
            return Array.from(document.querySelectorAll('a')).map(a => ({href: a.href, text: a.innerText.trim()}));
        """)
        header_text = driver.execute_script("""
            const h = document.querySelector('[class*="header"], [class*="Header"], [data-qa*="header"]');
            return h ? h.innerText : '';
        """)

        meta = extract_chat_metadata(links, header_text)
        comp = meta["company"] or "Работодатель"
        title = meta["title"] or "Позиция"
        vid = meta["vacancy_id"]

        # Check candidate status
        if not is_candidate_chat(msgs):
            return {
                "status": "already_sent",
                "company": comp,
                "title": title,
                "vacancy_id": vid,
                "detail": "Chat already has substantive cover letter",
            }

        # Need to send letter!
        print(f"    -> [CANDIDATE] Found negotiation with '1' / empty letter for {comp} — {title} (ID: {vid})", flush=True)
        letter = generate_tailored_letter(title, comp, vid)
        print(f"    -> [LETTER] Prepared {len(letter)} chars letter. Starting human-paced typing...", flush=True)

        # Locate textarea
        tas = driver.find_elements(By.CSS_SELECTOR, "textarea[data-qa='text-input'], textarea")
        if not tas:
            return {"status": "error", "company": comp, "title": title, "vacancy_id": vid, "detail": "Textarea not found"}

        input_el = tas[0]

        if fast_typing:
            input_el.send_keys(letter)
        else:
            type_human_paced_chat(input_el, letter, word_delay_range=word_delay_range)

        time.sleep(1.0)

        # Locate send button
        send_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='chatik-do-send-message']")
        if not send_btns:
            return {"status": "error", "company": comp, "title": title, "vacancy_id": vid, "detail": "Send button not found"}

        send_btn = send_btns[0]

        if not dry_run:
            driver.execute_script("arguments[0].click();", send_btn)
            time.sleep(2.0)

            # Update DB
            if vid:
                try:
                    init_database(db_path)
                    conn = get_connection(db_path)
                    conn.execute(
                        """
                        UPDATE applications
                        SET cover_letter_sent = 1,
                            notes = CASE
                                WHEN notes IS NULL OR notes = '' THEN 'Cover letter sent via negotiation chat'
                                WHEN notes NOT LIKE '%negotiation chat%' THEN notes || '; Cover letter sent via negotiation chat'
                                ELSE notes
                            END
                        WHERE vacancy_id = ?
                        """,
                        (str(vid),),
                    )
                    conn.commit()
                    conn.close()
                except Exception as exc:
                    log_event("warn", f"Could not update DB for negotiation send on {vid}: {exc}")

        return {
            "status": "sent" if not dry_run else "dry_run",
            "company": comp,
            "title": title,
            "vacancy_id": vid,
            "letter_length": len(letter),
            "dry_run": dry_run,
        }

    finally:
        driver.switch_to.default_content()
        # Close chatik drawer
        try:
            driver.execute_script("""
                const closeBtn = document.querySelector("button[data-qa='chatik-close-chatik']");
                if (closeBtn) closeBtn.click();
            """)
            time.sleep(1.0)
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="HeadHunter negotiations list chat cover letter sender.")
    parser.add_argument("--limit", type=int, default=10, help="Max candidates to repair/send (0 = all).")
    parser.add_argument("--all-pages", action="store_true", help="Scan across multiple pages of negotiations.")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without sending message or updating DB.")
    parser.add_argument("--fast-typing", action="store_true", help="Skip human typing delays.")
    parser.add_argument("--visible", action="store_true", help="Launch visible Edge window.")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Output JSON results.")
    args = parser.parse_args()

    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.edge.options import Options
    from selenium.webdriver.edge.service import Service

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

    results = []
    repaired_count = 0

    print("=== HERMES NEGOTIATIONS CHAT COVER LETTER SENDER ===", flush=True)
    print(f"Target URL: https://tashkent.hh.uz/applicant/negotiations | Limit: {args.limit} | Dry-run: {args.dry_run}", flush=True)

    try:
        driver.get("https://tashkent.hh.uz/applicant/negotiations")
        time.sleep(3.5)

        current_page = 0
        while True:
            btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='open_chat']")
            print(f"[PAGE {current_page + 1}] Found {len(btns)} negotiation cards on page...", flush=True)

            for idx in range(len(btns)):
                if args.limit > 0 and repaired_count >= args.limit:
                    print(f"[LIMIT] Reached limit of {args.limit} candidates repaired.", flush=True)
                    break

                # Re-fetch buttons in case DOM reloaded
                btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='open_chat']")
                if idx >= len(btns):
                    break

                btn = btns[idx]
                res = process_negotiation_card(
                    driver=driver,
                    card_button=btn,
                    db_path=Config.DB_PATH,
                    dry_run=args.dry_run,
                    fast_typing=args.fast_typing,
                )
                results.append(res)

                if res.get("status") in ("sent", "dry_run"):
                    repaired_count += 1
                    status_lbl = "[OK SENT]" if not args.dry_run else "[DRY RUN]"
                    print(
                        f"  -> {status_lbl} {res.get('company')} — {res.get('title')} "
                        f"(ID: {res.get('vacancy_id')}) | Письмо: {res.get('letter_length')} симв.",
                        flush=True,
                    )
                else:
                    print(f"  -> [SKIP] {res.get('company')} — {res.get('title')}: {res.get('detail')}", flush=True)

                if not args.fast_typing:
                    pause = random.uniform(3.0, 6.0)
                    time.sleep(pause)

            if args.limit > 0 and repaired_count >= args.limit:
                break

            if not args.all_pages:
                break

            # Try next page
            next_btns = driver.find_elements(By.CSS_SELECTOR, "[data-qa='pager-next']")
            if next_btns and next_btns[0].is_displayed():
                current_page += 1
                driver.execute_script("arguments[0].click();", next_btns[0])
                time.sleep(3.0)
            else:
                break

    finally:
        driver.quit()

    try:
        build_dashboard_artifacts()
    except Exception:
        pass

    summary = {
        "status": "ok",
        "total_scanned": len(results),
        "repaired_sent": repaired_count,
        "dry_run": args.dry_run,
        "results": results,
    }

    if args.as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"\n[DONE] Обработано карточек: {len(results)}. Отправлено писем: {repaired_count}.", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
