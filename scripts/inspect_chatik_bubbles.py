import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from scripts.config import Config
from scripts.hh_apply import _find_cached_msedgedriver

opts = Options()
opts.add_argument(f"--user-data-dir={Config.HH_SESSION_PROFILE_DIR}")
opts.add_argument("--headless=new")
opts.add_argument("--no-first-run")
edge_bin = Config.get_edge_binary()
if edge_bin:
    opts.binary_location = str(edge_bin)

cached = _find_cached_msedgedriver()
driver = webdriver.Edge(service=Service(executable_path=str(cached)), options=opts) if cached else webdriver.Edge(options=opts)

try:
    driver.get("https://tashkent.hh.uz/chat/5794363483")
    time.sleep(3)

    # Let's inspect the actual message elements
    script = """
        return Array.from(document.querySelectorAll('*')).filter(el => {
            const qa = el.getAttribute('data-qa') || '';
            const cl = el.className || '';
            return (qa.includes('message') || cl.includes('message') || cl.includes('Message')) && el.children.length === 0;
        }).map(el => ({
            tag: el.tagName,
            qa: el.getAttribute('data-qa'),
            class: el.className,
            text: el.innerText
        })).slice(0, 20);
    """
    res = driver.execute_script(script)
    print("Leaf message elements:\n" + json.dumps(res, ensure_ascii=False, indent=2))
finally:
    driver.quit()
