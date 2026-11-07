import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import init_database, get_connection
from scripts.add_position import add_vacancy
from scripts.update_status import update_application_status


class TestPositionCRUD(unittest.TestCase):
    def setUp(self):
        self.test_db = Config.TESTS_DIR / "test_crud.db"
        if self.test_db.exists():
            self.test_db.unlink()
        init_database(self.test_db)

    def tearDown(self):
        if self.test_db.exists():
            self.test_db.unlink()

    def test_add_and_update_lifecycle(self):
        # 1. Add vacancy manually
        res_add = add_vacancy(
            title="Senior Financial Controller",
            company="Orient Group",
            url="https://hh.uz/vacancy/999888",
            source="manual",
            tier=1,
            sector="Finance",
            notes="Added manually after networking",
            db_path=self.test_db,
        )
        self.assertTrue(res_add["success"])
        vid = res_add["vacancy_id"]

        # Verify added in DB
        conn = get_connection(self.test_db)
        c = conn.cursor()
        v_row = c.execute("SELECT company, tier FROM vacancies WHERE id = ?", (vid,)).fetchone()
        self.assertEqual(v_row, ("Orient Group", 1))

        # 2. Update status to 'interview'
        res_update = update_application_status(
            vacancy_id=vid,
            status="interview",
            notes="Technical interview scheduled for Tuesday",
            db_path=self.test_db,
        )
        self.assertTrue(res_update["success"])
        self.assertEqual(res_update["status"], "interview")

        # Verify application status in DB
        app_row = c.execute("SELECT status, notes FROM applications WHERE vacancy_id = ?", (vid,)).fetchone()
        self.assertIsNotNone(app_row)
        self.assertEqual(app_row[0], "interview")
        self.assertIn("Technical interview scheduled", app_row[1])

        conn.close()

    def test_invalid_status_rejected(self):
        res_update = update_application_status(
            vacancy_id="non_existent",
            status="flying_to_mars",
            db_path=self.test_db,
        )
        self.assertFalse(res_update["success"])


if __name__ == "__main__":
    unittest.main()
