import sys
import time
import json
from pathlib import Path
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
    url = "https://tashkent.hh.uz/vacancy/139427809"
    driver.get(url)
    time.sleep(2.5)

    title = driver.find_element(By.CSS_SELECTOR, "h1, [data-qa='vacancy-title']").text
    try:
        company = driver.find_element(By.CSS_SELECTOR, "[data-qa='vacancy-company-name'], a[data-qa='vacancy-company-name']").text
    except Exception:
        company = ""

    try:
        salary = driver.find_element(By.CSS_SELECTOR, "[data-qa='vacancy-salary']").text
    except Exception:
        salary = ""

    try:
        desc = driver.find_element(By.CSS_SELECTOR, "[data-qa='vacancy-description']").text
    except Exception:
        desc = driver.find_element(By.TAG_NAME, "body").text

    try:
        skills = [el.text for el in driver.find_elements(By.CSS_SELECTOR, "[data-qa='skills-element'], [class*='skill-badge']")]
    except Exception:
        skills = []

    res = {
        "vid": "139427809",
        "title": title,
        "company": company,
        "salary": salary,
        "skills": skills,
        "description": desc,
    }
    with open("data/vacancy_139427809.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("SUCCESS")
    print(f"Title: {title}")
    print(f"Company: {company}")
    print(f"Salary: {salary}")
    print("Skills:", skills)
    print("\n--- Description ---")
    print(desc)
finally:
    driver.quit()
