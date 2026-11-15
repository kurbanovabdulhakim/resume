import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import init_database


class TestCopilotServer(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.tmp_dir.name)
        self.test_db = self.test_dir / "test_positions.db"
        self.test_queue = self.test_dir / "test_queue.json"
        self.test_state = self.test_dir / "test_state.json"

        init_database(self.test_db)
        # Populate test vacancy
        conn = sqlite3.connect(self.test_db)
        conn.execute(
            """
            INSERT INTO vacancies (id, title, company, url, tier, sector, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            ("12345", "Senior Financial Analyst", "Test Corp", "https://hh.uz/vacancy/12345", 1, "Finance"),
        )
        conn.commit()
        conn.close()

        # Populate test queue
        queue_data = {
            "updated_at": "2026-11-15T00:00:00",
            "total_items": 1,
            "items": {
                "12345": {
                    "vacancy_id": "12345",
                    "title": "Senior Financial Analyst",
                    "company": "Test Corp",
                    "url": "https://hh.uz/vacancy/12345",
                    "priority_rank": 1,
                    "status": "queued",
                    "cover_letter": "Тестовое письмо для Test Corp",
                    "cv_variant": "financial_analyst",
                }
            },
        }
        self.test_queue.write_text(json.dumps(queue_data), encoding="utf-8")

        state_data = {
            "date": "2026-11-15",
            "applied_today": 0,
            "waves_completed": 0,
            "last_applied_at": None,
        }
        self.test_state.write_text(json.dumps(state_data), encoding="utf-8")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_copilot_service_logic_apply_and_queue(self):
        from scripts.copilot_server import CopilotService

        service = CopilotService(
            db_path=self.test_db,
            queue_path=self.test_queue,
            state_path=self.test_state,
        )

        items = service.get_queue()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["vacancy_id"], "12345")
        self.assertEqual(items[0]["status"], "queued")
        self.assertEqual(items[0]["cover_letter"], "Тестовое письмо для Test Corp")

        # Now mark as applied
        res = service.mark_applied(
            vacancy_id="12345",
            cover_letter="Тестовое письмо для Test Corp",
            cv_variant="financial_analyst",
        )
        self.assertTrue(res.get("success"))

        # Verify DB updated
        conn = sqlite3.connect(self.test_db)
        row = conn.execute("SELECT status, cv_variant FROM applications WHERE vacancy_id = '12345'").fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "applied")
        self.assertEqual(row[1], "financial_analyst")

        # Verify queue updated
        updated_items = service.get_queue()
        self.assertEqual(updated_items[0]["status"], "applied")

        # Verify state updated
        state = json.loads(self.test_state.read_text(encoding="utf-8"))
        self.assertEqual(state["applied_today"], 1)


if __name__ == "__main__":
    unittest.main()
