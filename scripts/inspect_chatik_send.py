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
    driver.get("https://tashkent.hh.uz/chat/5794363483")
    time.sleep(4)

    # Let's type something into textarea and see what button appears/activates
    ta = driver.find_element(By.CSS_SELECTOR, "textarea[data-qa='text-input']")
    ta.send_keys("Тест")
    time.sleep(1)

    btns = driver.execute_script("""
        return Array.from(document.querySelectorAll("button")).map(b => ({
            tag: b.tagName,
            qa: b.getAttribute('data-qa'),
            class: b.className,
            text: b.innerText,
            disabled: b.disabled
        })).filter(b => (b.qa && b.qa.includes('send')) || b.class.includes('send') || (b.text && b.text.includes('Отправ')));
    """)
    print("Send buttons found after typing:\n" + json.dumps(btns, ensure_ascii=False, indent=2))

    # Clear textarea
    ta.clear()
finally:
    driver.quit()
