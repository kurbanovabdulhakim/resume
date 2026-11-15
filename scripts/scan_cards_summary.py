import json
import time
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from scripts.config import Config
from scripts.hh_apply import _find_cached_msedgedriver

opts = Options()
opts.add_argument(f"--user-data-dir={Config.HH_SESSION_PROFILE_DIR}")
opts.add_argument("--headless=new")
opts.add_argument("--no-first-run")
edge_bin = Config.get_edge_binary()
if edge_bin:
    opts.binary_location = str(edge_bin)

cached = _find_cached_msedgedriver()
driver = webdriver.Edge(service=Service(executable_path=str(cached)), options=opts) if cached else webdriver.Edge(options=opts)

try:
    all_cards = []
    # Let's inspect pages 0 to 5
    for p in range(6):
        url = f"https://tashkent.hh.uz/applicant/negotiations?page={p}"
        driver.get(url)
        time.sleep(2.5)
        page_cards = driver.execute_script("""
            const res = [];
            document.querySelectorAll("button[data-qa='open_chat']").forEach((btn, idx) => {
                let p = btn;
                let found = null;
                for (let i = 0; i < 10; i++) {
                    if (p && p.innerText && (p.innerText.includes('сегодня') || p.innerText.includes('вчера') || p.innerText.includes('Отказаться'))) {
                        found = p;
                        break;
                    }
                    if (p && p.parentElement) p = p.parentElement;
                }
                const text = found ? found.innerText.trim() : '';
                const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
                res.push({
                    cardIndex: idx,
                    title: lines[1] || '',
                    company: lines[2] || '',
                    date: lines[3] || ''
                });
            });
            return res;
        """)
        print(f"Page {p}: found {len(page_cards)} cards.")
        for c in page_cards:
            c["page"] = p
            all_cards.append(c)

    print(f"Total cards across 6 pages: {len(all_cards)}")
    with open(Config.DATA_DIR / "negotiation_cards_p0_p5.json", "w", encoding="utf-8") as f:
        json.dump(all_cards, f, ensure_ascii=False, indent=2)

    # Search for specific companies like BUSINESS AUTOMATIZATION, MY FREIGHTER, etc.
    targets = ["BUSINESS", "FREIGHTER", "Clean", "DREAMLIFE", "ANNEXURE", "EY", "NILSTROY"]
    for c in all_cards:
        for t in targets:
            if t.lower() in c["company"].lower() or t.lower() in c["title"].lower():
                print(f"Found target card on page {c['page']}: {c['company']} — {c['title']} ({c['date']})")

finally:
    driver.quit()
