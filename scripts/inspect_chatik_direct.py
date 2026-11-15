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
    url = "https://chatik.hh.uz/chat/5794363483"
    driver.get(url)
    time.sleep(4)
    print("Direct Chatik URL:", driver.current_url)
    print("Page Title:", driver.title)

    # Save screenshot of direct chatik
    ss = Path("C:/Users/Abdulkhakim/.gemini/antigravity/brain/6fe0475c-f728-4085-bff1-0567211fa473/chatik_direct.png")
    driver.save_screenshot(str(ss))

    info = driver.execute_script("""
        const textareas = Array.from(document.querySelectorAll("textarea, [contenteditable='true']")).map(el => ({
            tag: el.tagName,
            qa: el.getAttribute('data-qa'),
            placeholder: el.getAttribute('placeholder'),
            class: el.className
        }));
        const buttons = Array.from(document.querySelectorAll("button")).map(el => ({
            tag: el.tagName,
            qa: el.getAttribute('data-qa'),
            text: el.innerText ? el.innerText.trim() : ''
        }));
        const msgs = Array.from(document.querySelectorAll("[data-qa*='message'], [class*='message'], [class*='Message']")).map(el => el.innerText ? el.innerText.trim() : '').filter(t => t.length > 0).slice(0, 10);
        return { textareas, buttons, msgs };
    """)
    print("Direct Chatik inspection:\n" + json.dumps(info, ensure_ascii=False, indent=2))
finally:
    driver.quit()
