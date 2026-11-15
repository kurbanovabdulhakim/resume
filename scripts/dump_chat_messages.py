import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from scripts.config import Config
import time

opts = Options()
opts.add_argument(f"--user-data-dir={Config.HH_SESSION_PROFILE_DIR}")
opts.add_argument("--headless=new")
d = webdriver.Edge(options=opts)

try:
    d.get("https://tashkent.hh.uz/applicant/negotiations?page=4")
    time.sleep(3)
    btns = d.find_elements(By.CSS_SELECTOR, "button[data-qa='open_chat']")
    print(f"Buttons found: {len(btns)}")
    d.execute_script("arguments[0].click();", btns[4])
    time.sleep(2.5)
    iframes = d.find_elements(By.CSS_SELECTOR, "iframe.chatik-integration-iframe")
    if iframes:
        d.switch_to.frame(iframes[0])
        time.sleep(1.5)
        msgs = d.execute_script("""
            return Array.from(document.querySelectorAll("[data-qa*='message'], [class*='message']"))
                .map(e => (e.innerText || '').trim())
                .filter(Boolean);
        """)
        print(f"Total elements matching: {len(msgs)}")
        for idx, m in enumerate(msgs):
            print(f"--- MSG {idx} ---")
            print(m)
            print("-----------------")
finally:
    d.quit()
