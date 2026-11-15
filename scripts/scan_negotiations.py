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

    # Let's inspect the first 10 cards and see what their text says
    cards_info = driver.execute_script("""
        const cards = [];
        const btns = Array.from(document.querySelectorAll("button[data-qa='open_chat']"));
        btns.forEach((btn, idx) => {
            let p = btn;
            for (let i = 0; i < 8; i++) {
                if (p && p.innerText && p.innerText.includes('Перейти в') && p.innerText.length < 500) {
                    cards.push({
                        idx: idx,
                        text: p.innerText.trim()
                    });
                    break;
                }
                if (p && p.parentElement) p = p.parentElement;
            }
        });
        return cards;
    """)
    print(f"Total negotiation cards found: {len(cards_info)}")
    for c in cards_info[:15]:
        lines = [line.strip() for line in c['text'].split('\n') if line.strip()]
        print(f"Card {c['idx']}: {' | '.join(lines[:4])}")

finally:
    driver.quit()
