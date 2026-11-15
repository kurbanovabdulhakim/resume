import json
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

data = json.load(open('data/belberda_vacancies.json', encoding='utf-8'))
flagged = [x for x in data['items'] if x.get('status') == 'flagged']
print(f"Total flagged to verify: {len(flagged)}")

driver = webdriver.Edge(options=options)
results = []

try:
    for item in flagged:
        vid = item.get("vacancy_id")
        comp = item.get("company")
        title = item.get("title")
        print(f"\nChecking vid={vid} ({comp} - {title})...")
        driver.get(f"https://tashkent.hh.uz/vacancy/{vid}")
        time.sleep(2.0)

        topic_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='vacancy-response-link-view-topic'], a[data-qa='vacancy-response-link-view-topic']")
        if not topic_btns:
            print("  No topic buttons on vacancy page!")
            results.append({"vid": vid, "company": comp, "status": "no_chat_button", "notes": "No topic button"})
            continue

        driver.execute_script("arguments[0].click();", topic_btns[0])
        time.sleep(2.0)

        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe.chatik-integration-iframe")
        if not iframes:
            print("  No chatik iframe found!")
            results.append({"vid": vid, "company": comp, "status": "no_iframe", "notes": "No iframe"})
            continue

        driver.switch_to.frame(iframes[0])
        time.sleep(1.2)

        # Check messages
        chat_body = driver.execute_script("return (document.body.innerText || '').trim();")
        tas = driver.find_elements(By.CSS_SELECTOR, "textarea[data-qa='text-input'], textarea")
        has_textarea = len(tas) > 0 and tas[0].is_enabled()
        
        is_rejected = "Работодатель отклонил отклик" in chat_body or "Отказ" in chat_body
        already_has_real_letter = "Меня заинтересовала" in chat_body or "Направляю отклик" in chat_body

        print(f"  has_textarea: {has_textarea}, is_rejected: {is_rejected}, already_has_letter: {already_has_real_letter}")
        
        res = {
            "vid": vid,
            "company": comp,
            "has_textarea": has_textarea,
            "is_rejected": is_rejected,
            "already_has_letter": already_has_real_letter,
            "snippet": chat_body[:150].replace("\n", " ")
        }
        results.append(res)
        
        # If textarea is present and no real letter, let's send it right now!
        if has_textarea and not already_has_real_letter and not is_rejected:
            from scripts.audit_and_repair_negotiations import generate_tailored_letter
            letter = generate_tailored_letter(title, comp, vid)
            ta = tas[0]
            ta.send_keys(letter)
            time.sleep(1.2)
            send_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='chatik-do-send-message'], button[type='submit']")
            if send_btns:
                driver.execute_script("arguments[0].click();", send_btns[0])
                time.sleep(1.5)
                res["action"] = "sent_now"
                print("  --> [SENT LIVE NOW!]")
            else:
                res["action"] = "send_button_not_found"
                print("  --> send button not found")
        else:
            res["action"] = "skipped"
            
        driver.switch_to.default_content()
        driver.execute_script("""
            const c = document.querySelector("button[data-qa='chatik-close-chatik']");
            if (c) c.click();
        """)
        time.sleep(0.5)

finally:
    driver.quit()
    with open("data/flagged_resolution.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nResolution saved to data/flagged_resolution.json")
