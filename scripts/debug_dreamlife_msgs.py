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
from scripts.hh_negotiations_chat_sender import is_candidate_chat

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
    btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='open_chat']")
    # Open card 1 (DREAMLIFE)
    driver.execute_script("arguments[0].click();", btns[1])
    time.sleep(3)

    iframes = driver.find_elements(By.CSS_SELECTOR, "iframe.chatik-integration-iframe")
    driver.switch_to.frame(iframes[0])
    time.sleep(1.5)

    msgs = driver.execute_script("""
        const m = [];
        document.querySelectorAll("[data-qa*='message'], [class*='message'], [class*='Message']").forEach(el => {
            const t = (el.innerText || '').trim();
            if (t && !m.includes(t)) m.push(t);
        });
        return m;
    """)
    print("Extracted msgs for card 1:")
    for idx, msg in enumerate(msgs):
        print(f"[{idx}] length={len(msg)}: {repr(msg[:80])}")

    print("is_candidate_chat result:", is_candidate_chat(msgs))

finally:
    driver.quit()
