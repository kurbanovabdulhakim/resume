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
    print("Navigating to vacancy 138928260...")
    driver.get("https://tashkent.hh.uz/vacancy/138928260")
    time.sleep(2.0)
    print("Current URL:", driver.current_url)

    topic_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='negotiations/topic'], [data-qa='vacancy-response-link-view-topic']")
    print("Topic links count:", len(topic_links))
    for t in topic_links:
        print("Topic link:", t.get_attribute("href"), t.text)

    if topic_links:
        driver.get(topic_links[0].get_attribute("href"))
        time.sleep(2.5)
        print("Topic page URL:", driver.current_url)
        driver.save_screenshot(r"C:\Users\Abdulkhakim\.gemini\antigravity\brain\6fe0475c-f728-4085-bff1-0567211fa473\test_topic_138928260.png")
        
        # Check textareas and buttons
        tas = driver.find_elements(By.CSS_SELECTOR, "textarea")
        print("Textareas found on topic page:", len(tas))
        for ta in tas:
            print("  ta tag:", ta.tag_name, "qa:", ta.get_attribute("data-qa"), "placeholder:", ta.get_attribute("placeholder"))

        btns = driver.find_elements(By.CSS_SELECTOR, "button")
        print("Buttons found on topic page:", len(btns))
        for b in btns:
            qa = b.get_attribute("data-qa")
            if qa or "отправ" in (b.text or "").lower() or "send" in (b.text or "").lower():
                print("  btn qa:", qa, "text:", b.text)
finally:
    driver.quit()
