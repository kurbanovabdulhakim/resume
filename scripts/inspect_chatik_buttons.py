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
    d.get("https://tashkent.hh.uz/applicant/negotiations?page=6")
    time.sleep(3)
    btns = d.find_elements(By.CSS_SELECTOR, "button[data-qa='open_chat']")
    print(f"Cards found on page 6: {len(btns)}")
    # card 4 is 5th card (INTERNATIONAL GOLDSTARS SCHOOL)
    d.execute_script("arguments[0].click();", btns[4])
    time.sleep(2.5)
    iframes = d.find_elements(By.CSS_SELECTOR, "iframe.chatik-integration-iframe")
    if iframes:
        d.switch_to.frame(iframes[0])
        time.sleep(1.5)
        tas = d.find_elements(By.CSS_SELECTOR, "textarea[data-qa='text-input'], textarea")
        print(f"Textareas found: {len(tas)}")
        if tas:
            tas[0].send_keys("Здравствуйте! Это тестовое сообщение.")
            time.sleep(1.5)
            buttons = d.execute_script("""
                return Array.from(document.querySelectorAll('button')).map(b => ({
                    qa: b.getAttribute('data-qa'),
                    type: b.getAttribute('type'),
                    text: b.innerText.trim(),
                    disabled: b.disabled,
                    className: b.className
                }));
            """)
            print("Buttons found in Chatik after typing:")
            import pprint
            pprint.pprint(buttons)
finally:
    d.quit()
