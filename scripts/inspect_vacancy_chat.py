import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from scripts.config import Config
import time

parser = argparse.ArgumentParser()
parser.add_argument("--vid", type=str, required=True)
args = parser.parse_args()

opts = Options()
opts.add_argument(f"--user-data-dir={Config.HH_SESSION_PROFILE_DIR}")
opts.add_argument("--headless=new")
d = webdriver.Edge(options=opts)

try:
    url = f"https://tashkent.hh.uz/vacancy/{args.vid}"
    print(f"Loading vacancy page: {url}")
    d.get(url)
    time.sleep(3.0)

    page_info = d.execute_script("""
        return {
            title: document.title,
            responseButtons: Array.from(document.querySelectorAll("[data-qa*='response'], [data-qa*='apply']")).map(b => ({
                qa: b.getAttribute('data-qa'),
                text: b.innerText.trim(),
                href: b.getAttribute('href')
            })),
            links: Array.from(document.querySelectorAll("a")).filter(a => a.href && (a.href.includes('negotiation') || a.href.includes('chat'))).map(a => ({
                href: a.href,
                text: a.innerText.trim()
            })),
            bodyTextSample: (document.body.innerText || '').slice(0, 300)
        };
    """)
    print("Page Info:")
    import pprint
    pprint.pprint(page_info)
finally:
    d.quit()
