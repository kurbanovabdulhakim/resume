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
    btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='open_chat']")
    print(f"Buttons found: {len(btns)}")
    if btns:
        driver.execute_script("arguments[0].click();", btns[0])
        time.sleep(4)

        iframe_src = driver.execute_script("""
            const iframe = document.querySelector('iframe.chatik-integration-iframe');
            return iframe ? iframe.src : '';
        """)
        print("Iframe SRC:", iframe_src)

        # Switch to iframe and check DOM
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe.chatik-integration-iframe")
        if iframes:
            driver.switch_to.frame(iframes[0])
            time.sleep(2)
            inside_info = driver.execute_script("""
                const inputs = Array.from(document.querySelectorAll("textarea, [contenteditable='true'], input")).map(el => ({
                    tag: el.tagName,
                    qa: el.getAttribute('data-qa'),
                    placeholder: el.getAttribute('placeholder'),
                    contenteditable: el.getAttribute('contenteditable')
                }));
                const messages = Array.from(document.querySelectorAll("[data-qa*='message'], [class*='message']")).map(el => el.innerText.trim()).filter(t => t.length > 0).slice(0, 5);
                const sendBtns = Array.from(document.querySelectorAll("button")).filter(b => (b.innerText || '').includes('Отправить') || (b.getAttribute('data-qa') || '').includes('send')).map(b => ({
                    qa: b.getAttribute('data-qa'),
                    text: b.innerText
                }));
                return { inputs, messages, sendBtns };
            """)
            print("Inside Iframe Info:\n" + json.dumps(inside_info, ensure_ascii=False, indent=2))
            driver.switch_to.default_content()
finally:
    driver.quit()
