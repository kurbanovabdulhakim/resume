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
    print(f"Total buttons: {len(btns)}")

    for idx in range(min(5, len(btns))):
        # Refresh elements
        btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='open_chat']")
        btn = btns[idx]

        # Get card title and company
        card_info = driver.execute_script("""
            let p = arguments[0];
            for (let i = 0; i < 10; i++) {
                if (p && p.innerText && (p.innerText.includes('сегодня') || p.innerText.includes('вчера') || p.innerText.includes('Отказаться'))) {
                    return p.innerText;
                }
                if (p && p.parentElement) p = p.parentElement;
            }
            return '';
        """, btn)
        lines = [line.strip() for line in card_info.split('\n') if line.strip()]
        title = lines[1] if len(lines) > 1 else 'Unknown'
        company = lines[2] if len(lines) > 2 else 'Unknown'

        # Click open chat
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(3)

        # Get iframe src
        iframe_src = driver.execute_script("""
            const iframe = document.querySelector('iframe.chatik-integration-iframe');
            return iframe ? iframe.src : '';
        """)

        # Extract chat_id
        chat_id = ""
        if "chat/" in iframe_src:
            chat_id = iframe_src.split("chat/")[1].split("?")[0]

        # Let's inspect the messages inside iframe or by opening chatik directly
        # To be clean and fast, switch to iframe:
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe.chatik-integration-iframe")
        msgs = []
        if iframes:
            try:
                driver.switch_to.frame(iframes[0])
                time.sleep(1)
                msgs = driver.execute_script("""
                    const m = [];
                    document.querySelectorAll("[data-qa*='message'], [class*='message'], [class*='Message']").forEach(el => {
                        const t = (el.innerText || '').trim();
                        if (t && !m.includes(t)) m.push(t);
                    });
                    return m.slice(0, 5);
                """)
                driver.switch_to.default_content()
            except Exception as e:
                driver.switch_to.default_content()

        # Close chatik
        driver.execute_script("""
            const closeBtn = document.querySelector("button[data-qa='chatik-close-chatik']");
            if (closeBtn) closeBtn.click();
        """)
        time.sleep(1)

        print(f"[{idx}] {company} — {title} (Chat ID: {chat_id})")
        print(f"    Messages sample: {msgs[:2]}")
        print()

finally:
    driver.quit()
