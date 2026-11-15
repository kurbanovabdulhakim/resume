import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from selenium import webdriver
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
    driver.get("https://tashkent.hh.uz/applicant/negotiations")
    time.sleep(3)

    script = """
    const items = [];
    // Find all links to topics or chat
    const links = Array.from(document.querySelectorAll("a")).filter(a => a.href.includes("topicId=") || a.innerText.includes("Перейти в чат"));
    for (const a of links) {
        // find parent card
        let parent = a.closest("[data-qa*='negotiation'], [class*='negotiation'], div");
        for (let i = 0; i < 5; i++) {
            if (parent && parent.innerText && parent.innerText.length > 50 && parent.innerText.length < 500) break;
            if (parent && parent.parentElement) parent = parent.parentElement;
        }
        items.push({
            href: a.href,
            linkText: a.innerText.trim(),
            qa: a.getAttribute("data-qa"),
            cardText: parent ? parent.innerText.trim().substring(0, 200) : ""
        });
    }
    return {
        totalLinks: links.length,
        items: items.slice(0, 15)
    };
    """
    res = driver.execute_script(script)
    print(json.dumps(res, ensure_ascii=False, indent=2))
finally:
    driver.quit()
