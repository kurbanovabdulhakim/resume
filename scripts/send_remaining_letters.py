import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from scripts.audit_and_repair_negotiations import generate_tailored_letter
from scripts.init_db import get_connection
from scripts.config import Config

options = Options()
options.use_chromium = True
options.add_argument(r"--user-data-dir=C:\Users\Abdulkhakim\.gemini\hh_main_session")
options.add_argument("--profile-directory=Default")
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1600,1000")

# Vacancies that are not rejected
target_vids = [
    {"vid": "139148269", "company": "ONEFOOD", "title": "Помощник операционного директора"},
    {"vid": "139115408", "company": "ОOO Lactalis Central Asia", "title": "Специалист по закупкам"},
    {"vid": "139114696", "company": "Национальный комитет по статистике", "title": "Iqtisodchi-tahlilchi (yetakchi/bosh mutaxassis)"},
    {"vid": "138928759", "company": "Assorti Discount Markets", "title": "Аналитик"},
    {"vid": "138928260", "company": "INTERNATIONAL GOLDSTARS SCHOOL", "title": "Кассир (отдел бухгалтерии школы)"},
]

driver = webdriver.Edge(options=options)
delivered = []

try:
    for item in target_vids:
        vid = item["vid"]
        comp = item["company"]
        title = item["title"]
        print(f"\n[PROCESSING] {comp} — {title} (ID: {vid})...", flush=True)

        driver.get(f"https://tashkent.hh.uz/vacancy/{vid}")
        time.sleep(2.0)

        topic_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='vacancy-response-link-view-topic'], a[data-qa='vacancy-response-link-view-topic']")
        if not topic_btns:
            print("  [SKIP] No topic button", flush=True)
            continue

        driver.execute_script("arguments[0].click();", topic_btns[0])
        time.sleep(2.5)

        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe.chatik-integration-iframe")
        if not iframes:
            print("  [SKIP] No iframe found", flush=True)
            continue

        driver.switch_to.frame(iframes[0])
        time.sleep(1.5)

        # Check for 'Добавить сопроводительное' button
        action_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='chatik-chat-message-applicant-action'], button[data-qa*='applicant-action']")
        if action_btns:
            print("  Found 'Добавить сопроводительное' button, clicking...", flush=True)
            driver.execute_script("arguments[0].click();", action_btns[0])
            time.sleep(1.5)

        tas = driver.find_elements(By.CSS_SELECTOR, "textarea[data-qa='text-input'], textarea")
        if not tas:
            print("  [WARN] Textarea not available in chat.", flush=True)
            driver.switch_to.default_content()
            continue

        letter = generate_tailored_letter(title, comp, vid)
        print(f"  Typing tailored cover letter ({len(letter)} chars)...", flush=True)
        ta = tas[0]
        ta.send_keys(letter)
        time.sleep(1.5)

        send_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-qa='chatik-do-send-message'], button[type='submit']")
        if send_btns:
            driver.execute_script("arguments[0].click();", send_btns[0])
            time.sleep(2.0)
            print(f"  [DELIVERED] Letter successfully sent into chat for {comp}!", flush=True)
            delivered.append({"vid": vid, "company": comp, "title": title, "status": "sent"})

            # Update DB
            try:
                conn = get_connection(Config.DB_PATH)
                conn.execute(
                    """
                    UPDATE applications
                    SET cover_letter_sent = ?,
                        notes = CASE
                            WHEN notes IS NULL OR notes = '' THEN 'Cover letter repaired and sent via chat'
                            WHEN notes NOT LIKE '%repaired%' THEN notes || '; Cover letter repaired and sent via chat'
                            ELSE notes
                        END
                    WHERE vacancy_id = ?
                    """,
                    (letter, str(vid)),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"  DB update note: {e}", flush=True)
        else:
            print("  [WARN] Send button not enabled after typing.", flush=True)

        driver.switch_to.default_content()
        driver.execute_script("""
            const c = document.querySelector("button[data-qa='chatik-close-chatik']");
            if (c) c.click();
        """)
        time.sleep(1.0)

finally:
    driver.quit()
    print(f"\nAll done! Successfully delivered {len(delivered)} additional cover letters.", flush=True)
