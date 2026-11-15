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
    vid = "139148269" # ONEFOOD
    print(f"Navigating to vacancy {vid}...", flush=True)
    driver.get(f"https://tashkent.hh.uz/vacancy/{vid}")
    time.sleep(2.0)

    topic_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='vacancy-response-link-view-topic'], a[data-qa='vacancy-response-link-view-topic']")
    print(f"Topic buttons found: {len(topic_btns)}", flush=True)
    if topic_btns:
        driver.execute_script("arguments[0].click();", topic_btns[0])
        time.sleep(2.5)

        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe.chatik-integration-iframe")
        print(f"iframes found: {len(iframes)}", flush=True)
        if iframes:
            driver.switch_to.frame(iframes[0])
            time.sleep(1.5)

            action_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='chatik-chat-message-applicant-action'], button[data-qa*='applicant-action']")
            print(f"Action buttons: {len(action_btns)}", flush=True)
            if action_btns:
                driver.execute_script("arguments[0].click();", action_btns[0])
                time.sleep(1.5)

            tas = driver.find_elements(By.CSS_SELECTOR, "textarea[data-qa='text-input'], textarea")
            print(f"Textareas: {len(tas)}", flush=True)
            if tas:
                letter = "Здравствуйте! Меня заинтересовала позиция Помощник операционного директора в ONEFOOD."
                tas[0].send_keys(letter)
                time.sleep(2.0)

                send_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='chatik-do-send-message'], button[type='submit']")
                print(f"Send buttons: {len(send_btns)}", flush=True)
                for b in send_btns:
                    print(f"  Send btn qa: {b.get_attribute('data-qa')}, enabled: {b.is_enabled()}, displayed: {b.is_displayed()}", flush=True)

                if send_btns:
                    driver.execute_script("arguments[0].click();", send_btns[0])
                    time.sleep(2.0)
                    print("[DELIVERED SUCCESS!]", flush=True)

            driver.save_screenshot(r"C:\Users\Abdulkhakim\.gemini\antigravity\brain\6fe0475c-f728-4085-bff1-0567211fa473\onefood_chat.png")
finally:
    driver.quit()
