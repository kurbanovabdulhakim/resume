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
    vid = "139134530" # UzCarlsberg
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

            # Check for elements containing "сопроводительное"
            els = driver.find_elements(By.XPATH, "//*[contains(., 'сопроводительное') or contains(., 'Сопроводительное')]")
            print(f"Elements with 'сопроводительное': {len(els)}")
            for el in els:
                print("  tag:", el.tag_name, "qa:", el.get_attribute("data-qa"), "role:", el.get_attribute("role"), "text:", el.text)

            # Check why textarea was 0 - is chat closed / read only?
            all_inputs = driver.find_elements(By.CSS_SELECTOR, "input, textarea, [contenteditable='true']")
            print(f"All editable elements: {len(all_inputs)}")
finally:
    driver.quit()
