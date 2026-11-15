import unittest
import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import init_database, get_connection
from scripts.portals.olx_scraper import parse_olx_listing_html
from scripts.portals.olx_outreach import process_pending_olx_vacancies
from scripts.portals.hh_watcher import parse_hh_search_snippet, fetch_hh_vacancies


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

    def test_olx_outreach_no_illegal_db_status(self):
        test_db = Config.TESTS_DIR / "test_olx_outreach.db"
        if test_db.exists():
            test_db.unlink()
        init_database(test_db)
        conn = get_connection(test_db)
        conn.execute(
            "INSERT INTO vacancies (id, title, company, url, source, tier, sector, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
            ("olx_123", "Финансовый аналитик", "Apex", "https://olx.uz/d/obyavlenie/test-ID123.html", "olx", 2, "Finance"),
        )
        conn.commit()
        conn.close()

        try:
            with patch("scripts.portals.olx_outreach.fetch_page_html", return_value="<html>Писать @hr_apex +998901234567</html>"):
                res = process_pending_olx_vacancies(limit=5, db_path=test_db)
            self.assertTrue(res["success"])
            self.assertEqual(res["processed"], 1)
            self.assertIn("Абдулхаким", res["results"][0]["draft_letter"])
        finally:
            if test_db.exists():
                test_db.unlink()

    def test_hh_watcher_sends_hh_user_agent_header(self):
        captured = {}

        class _FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"items": []}'

        def _fake_urlopen(req, timeout=10):
            captured["headers"] = dict(req.header_items())
            return _FakeResp()

        with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
            res = fetch_hh_vacancies(query="финансовый аналитик", limit=2)
        self.assertEqual(res, [])
        lower_keys = {k.lower(): v for k, v in captured["headers"].items()}
        self.assertIn("hh-user-agent", lower_keys)


if __name__ == "__main__":
    unittest.main()
