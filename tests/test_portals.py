import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.portals.olx_scraper import parse_olx_listing_html
from scripts.portals.hh_watcher import parse_hh_search_snippet


class TestPortals(unittest.TestCase):
    def test_parse_olx_listing_html(self):
        sample_html = """
        <div data-cy="l-card" class="css-1sw7q4x">
          <a href="/d/obyavlenie/finansovyy-analitik-IDabc123.html" class="css-rc5s2u">
            <h6 class="css-16v5mdi er34gjf0">Финансовый аналитик</h6>
          </a>
          <p class="css-10b0gli er34gjf0">15 000 000 сум</p>
          <span class="css-19yf5ke">Ташкент, Мирзо-Улугбекский район</span>
        </div>
        """
        items = parse_olx_listing_html(sample_html)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Финансовый аналитик")
        self.assertIn("olx.uz", items[0]["url"])
        self.assertEqual(items[0]["source"], "olx")
        self.assertEqual(items[0]["sector"], "Finance")

    def test_parse_hh_snippet(self):
        sample = {
            "id": "999111",
            "name": "Senior Business Analyst",
            "employer": {"name": "TBC Bank"},
            "alternate_url": "https://hh.uz/vacancy/999111",
            "salary": {"from": 2000, "to": 3000, "currency": "USD"},
        }
        res = parse_hh_search_snippet(sample)
        self.assertEqual(res["id"], "999111")
        self.assertEqual(res["company"], "TBC Bank")
        self.assertEqual(res["tier"], 1)
        self.assertEqual(res["sector"], "Finance")


if __name__ == "__main__":
    unittest.main()
