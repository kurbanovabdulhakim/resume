import unittest
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import init_database, get_connection
from scripts.sync_hermes import sync_hermes_queue


class TestSyncHermes(unittest.TestCase):
    def setUp(self):
        self.test_db = Config.TESTS_DIR / "test_hermes_sync.db"
        self.test_queue = Config.TESTS_DIR / "sample_queue.json"
        if self.test_db.exists():
            self.test_db.unlink()
        init_database(self.test_db)

        # Create dummy queue file
        sample_data = {
            "total_vacancies": 2,
            "total_batches": 1,
            "batch_size": 200,
            "batches": [
                {
                    "batch_number": 1,
                    "status": "completed",
                    "applied_count": 1,
                    "vacancies": [
                        {
                            "id": "111001",
                            "title": "Lead Business Analyst",
                            "company": "Ipoteka Bank",
                            "salary": "до $2,000",
                            "url": "https://hh.uz/111001",
                            "tier": 1,
                            "tier_name": "Tier 1: Bank",
                            "category": "Банковский сектор, Финансы & Аудит",
                            "applied": True,
                        },
                        {
                            "id": "111002",
                            "title": "Operations Specialist",
                            "company": "UzPost",
                            "salary": "до 8 000 000 so'm",
                            "url": "https://hh.uz/111002",
                            "tier": 2,
                            "tier_name": "Tier 2: Mid",
                            "category": "Логистика, ВЭД & Склад",
                            "applied": False,
                        },
                    ],
                }
            ],
        }
        with open(self.test_queue, "w", encoding="utf-8") as f:
            json.dump(sample_data, f, ensure_ascii=False)

    def tearDown(self):
        if self.test_db.exists():
            self.test_db.unlink()
        if self.test_queue.exists():
            self.test_queue.unlink()

    def test_sync_upserts_vacancies_and_applications(self):
        result = sync_hermes_queue(
            queue_path=self.test_queue, db_path=self.test_db, dry_run=False
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["vacancies_synced"], 2)
        self.assertGreaterEqual(result["applications_synced"], 1)

        conn = get_connection(self.test_db)
        cursor = conn.cursor()

        # Check vacancy row
        v1 = cursor.execute(
            "SELECT title, company, tier, sector FROM vacancies WHERE id = '111001'"
        ).fetchone()
        self.assertEqual(v1, ("Lead Business Analyst", "Ipoteka Bank", 1, "Finance"))

        # Check application row
        app1 = cursor.execute(
            "SELECT status FROM applications WHERE vacancy_id = '111001'"
        ).fetchone()
        self.assertIsNotNone(app1)
        self.assertEqual(app1[0], "applied")

        conn.close()


if __name__ == "__main__":
    unittest.main()
