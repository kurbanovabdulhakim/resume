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
    print(f"Opening vacancy {vid}...")
    driver.get(f"https://tashkent.hh.uz/vacancy/{vid}")
    time.sleep(2.0)

    topic_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='vacancy-response-link-view-topic'], a[data-qa='vacancy-response-link-view-topic']")
    if topic_btns:
        driver.execute_script("arguments[0].click();", topic_btns[0])
        time.sleep(2.5)

        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe.chatik-integration-iframe")
        if iframes:
            driver.switch_to.frame(iframes[0])
            time.sleep(1.5)

            # Find button with "Добавить сопроводительное"
            btns = driver.find_elements(By.XPATH, "//button[contains(., 'сопроводительное')] | //a[contains(., 'сопроводительное')] | //*[contains(@data-qa, 'applicant-action')]")
            print(f"Add cover letter buttons: {len(btns)}")
            for b in btns:
                print("  btn tag:", b.tag_name, "qa:", b.get_attribute("data-qa"), "text:", b.text)

            if btns:
                driver.execute_script("arguments[0].click();", btns[0])
                time.sleep(1.5)

                tas = driver.find_elements(By.CSS_SELECTOR, "textarea[data-qa='text-input'], textarea")
                print(f"Textareas after clicking 'Добавить сопроводительное': {len(tas)}")
                if tas:
                    print("  textarea enabled:", tas[0].is_enabled(), "placeholder:", tas[0].get_attribute("placeholder"))
                    tas[0].send_keys("Здравствуйте! Меня заинтересовала ваша позиция.")
                    time.sleep(1.0)
                    send_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='chatik-do-send-message'], button[type='submit']")
                    print(f"  send buttons found: {len(send_btns)}")
finally:
    driver.quit()
