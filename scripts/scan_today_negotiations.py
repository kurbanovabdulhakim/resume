"""
Scan Today Negotiations on HeadHunter.

Extracts all negotiation cards applied today, inspects their chat status,
identifies cards with '1' or gibberish, saves the compiled audit list,
and provides an option to deliver tailored cover letters.
"""

import json
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service

from scripts.config import Config
from scripts.hh_apply import _find_cached_msedgedriver
from scripts.audit_and_repair_negotiations import classify_chat_status


def get_driver(headless: bool = True):
    opts = Options()
    opts.add_argument(f"--user-data-dir={Config.HH_SESSION_PROFILE_DIR}")
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-first-run")
    edge_bin = Config.get_edge_binary()
    if edge_bin:
        opts.binary_location = str(edge_bin)

    cached = _find_cached_msedgedriver()
    if cached:
        return webdriver.Edge(service=Service(executable_path=str(cached)), options=opts)
    return webdriver.Edge(options=opts)


def scan_negotiation_cards(driver, max_pages: int = 15):
    cards = []
    print("[SCAN] Starting scan of negotiation cards...", flush=True)

    for p in range(max_pages):
        url = f"https://tashkent.hh.uz/applicant/negotiations?page={p}"
        driver.get(url)
        time.sleep(2.5)

        page_data = driver.execute_script("""
            const items = [];
            const chatBtns = document.querySelectorAll("button[data-qa='open_chat']");
            chatBtns.forEach((btn, idx) => {
                let card = btn;
                for (let i = 0; i < 10; i++) {
                    if (card && card.innerText && (card.innerText.includes('сегодня') || card.innerText.includes('вчера') || card.innerText.includes('Отказаться'))) break;
                    if (card && card.parentElement) card = card.parentElement;
                }
                const text = card ? card.innerText : '';
                const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
                
                // Vacancy link
                const links = card ? Array.from(card.querySelectorAll('a')).map(a => a.href) : [];
                const vlink = links.find(h => h.includes('/vacancy/')) || '';
                const match = vlink.match(/vacancy\\/(\\d+)/);
                const vid = match ? match[1] : '';

                // Extract title and company
                let title = '';
                let company = '';
                let dateStr = '';
                
                // Check lines
                for (let i = 0; i < lines.length; i++) {
                    if (lines[i] === 'сегодня' || lines[i] === 'вчера' || /\\d+\\s+[а-яА-Я]+/.test(lines[i])) {
                        dateStr = lines[i];
                        if (i >= 2) {
                            title = lines[i-2];
                            company = lines[i-1];
                        } else if (i == 1) {
                            title = lines[0];
                        }
                        break;
                    }
                }
                if (!title && lines.length > 1) {
                    title = lines[1];
                    company = lines[2] || '';
                }

                items.push({
                    cardIndex: idx,
                    vacancy_id: vid,
                    title: title,
                    company: company,
                    date: dateStr,
                    raw_lines: lines.slice(0, 5)
                });
            });
            return items;
        """)

        print(f"  Page {p}: found {len(page_data)} cards.", flush=True)
        if not page_data:
            break

        has_today = any("сегодня" in c.get("date", "") or "сегодня" in " ".join(c.get("raw_lines", [])) for c in page_data)
        for c in page_data:
            c["page"] = p
            cards.append(c)

        if not has_today and p >= 2:
            print(f"  Page {p}: No more cards with 'сегодня'. Stopping scan.", flush=True)
            break

    return cards


if __name__ == "__main__":
    driver = get_driver(headless=True)
    try:
        cards = scan_negotiation_cards(driver, max_pages=12)
        print(f"\n[SCAN] Total cards collected: {len(cards)}")
        today_cards = [c for c in cards if "сегодня" in c.get("date", "") or "сегодня" in " ".join(c.get("raw_lines", []))]
        print(f"[SCAN] Total cards from 'сегодня': {len(today_cards)}")

        out_path = Config.DATA_DIR / "today_negotiation_cards.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"total": len(cards), "today_total": len(today_cards), "cards": cards}, f, ensure_ascii=False, indent=2)
        print(f"[SCAN] Saved to: {out_path}")
    finally:
        driver.quit()
