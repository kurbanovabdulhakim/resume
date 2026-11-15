import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

options = Options()
options.use_chromium = True
options.add_argument(r"--user-data-dir=C:\Users\Abdulkhakim\.gemini\hh_main_session")
options.add_argument("--profile-directory=Default")
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1600,1000")

driver = webdriver.Edge(options=options)
try:
    print("Navigating to negotiations page 7...")
    driver.get("https://tashkent.hh.uz/applicant/negotiations?page=6")
    time.sleep(3.0)

    btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='open_chat']")
    print(f"Found {len(btns)} open_chat buttons.")

    # Check card index 4 (item 5: INTERNATIONAL GOLDSTARS SCHOOL)
    card_idx = 4
    btn = btns[card_idx]
    driver.execute_script("arguments[0].click();", btn)
    time.sleep(2.5)

    iframes = driver.find_elements(By.CSS_SELECTOR, "iframe.chatik-integration-iframe")
    print(f"iframes found: {len(iframes)}")
    if iframes:
        driver.switch_to.frame(iframes[0])
        time.sleep(1.5)

        tas = driver.find_elements(By.CSS_SELECTOR, "textarea[data-qa='text-input'], textarea")
        print(f"Textareas in chatik: {len(tas)}")
        for ta in tas:
            print("  ta tag:", ta.tag_name, "qa:", ta.get_attribute("data-qa"), "enabled:", ta.is_enabled())

        send_btns_before = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='chatik-do-send-message'], button[type='submit']")
        print(f"Send buttons before typing: {len(send_btns_before)}")

        # Check messages
        msgs = driver.execute_script("""
            const m = [];
            document.querySelectorAll("[data-qa*='message'], [class*='message'], [class*='Message']").forEach(el => {
                const t = (el.innerText || '').trim();
                if (t && !m.includes(t)) m.push(t);
            });
            return m;
        """)
        print(f"Messages in chat ({len(msgs)}):")
        for m in msgs:
            print("   msg:", m[:80])

        # Test typing
        if tas:
            ta = tas[0]
            ta.send_keys("Тестовое сообщение")
            time.sleep(1.5)
            send_btns_after = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='chatik-do-send-message'], button[type='submit']")
            print(f"Send buttons after typing: {len(send_btns_after)}")
            for b in send_btns_after:
                print("   send btn:", b.get_attribute("data-qa"), "enabled:", b.is_enabled(), "displayed:", b.is_displayed())
finally:
    driver.quit()
