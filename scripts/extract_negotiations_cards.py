import json
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
    driver.get("https://tashkent.hh.uz/applicant/negotiations")
    time.sleep(3)

    cards = driver.execute_script("""
        const result = [];
        // Each card on negotiations page has a specific container
        const items = document.querySelectorAll("[data-qa='negotiations-item'], [class*='negotiation-card'], [class*='negotiationItem']");
        if (items.length > 0) {
            items.forEach((item, idx) => {
                result.push({idx, text: item.innerText.substring(0, 150)});
            });
        } else {
            // Find containers that hold 'open_chat' buttons
            const btns = document.querySelectorAll("button[data-qa='open_chat']");
            btns.forEach((btn, idx) => {
                let p = btn;
                let foundCard = null;
                for (let i = 0; i < 12; i++) {
                    if (p && p.innerText && (p.innerText.includes('сегодня') || p.innerText.includes('вчера') || p.innerText.includes('Отказаться'))) {
                        foundCard = p;
                    }
                    if (p && p.parentElement) p = p.parentElement;
                }
                if (foundCard) {
                    result.push({
                        idx,
                        text: foundCard.innerText.trim().substring(0, 250)
                    });
                }
            });
        }
        return result;
    """)
    print(f"Cards extracted: {len(cards)}")
    for c in cards[:10]:
        print(f"--- CARD {c['idx']} ---")
        print(c['text'])

finally:
    driver.quit()
