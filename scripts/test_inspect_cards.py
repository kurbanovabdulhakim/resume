import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from scripts.config import Config
from scripts.audit_and_repair_negotiations import classify_chat_status
import time

parser = argparse.ArgumentParser()
parser.add_argument("--page", type=int, default=0)
parser.add_argument("--start", type=int, default=0)
parser.add_argument("--end", type=int, default=10)
args = parser.parse_args()

opts = Options()
opts.add_argument(f"--user-data-dir={Config.HH_SESSION_PROFILE_DIR}")
opts.add_argument("--headless=new")
d = webdriver.Edge(options=opts)

try:
    d.get(f"https://tashkent.hh.uz/applicant/negotiations?page={args.page}")
    time.sleep(3)
    btns = d.find_elements(By.CSS_SELECTOR, "button[data-qa='open_chat']")
    print(f"Page {args.page}: found {len(btns)} open_chat buttons.")
    end_idx = min(args.end, len(btns))
    for i in range(args.start, end_idx):
        btns = d.find_elements(By.CSS_SELECTOR, "button[data-qa='open_chat']")
        btn = btns[i]
        d.execute_script("arguments[0].click();", btn)
        time.sleep(2.0)
        iframes = d.find_elements(By.CSS_SELECTOR, "iframe.chatik-integration-iframe")
        if iframes:
            d.switch_to.frame(iframes[0])
            time.sleep(1.2)
            msgs = d.execute_script("""
                return Array.from(document.querySelectorAll("[data-qa*='message'], [class*='message']"))
                    .map(e => (e.innerText || '').trim())
                    .filter(Boolean);
            """)
            status = classify_chat_status(msgs)
            print(f"Card {i}: {status['category']} | reason: {status['reason']} | initial: {repr(status['initial_text'][:60])}", flush=True)
            d.switch_to.default_content()
            d.execute_script("""
                const c = document.querySelector("button[data-qa='chatik-close-chatik']");
                if (c) c.click();
            """)
            time.sleep(0.8)
finally:
    d.quit()
