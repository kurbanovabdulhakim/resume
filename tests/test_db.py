import unittest
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import init_database, get_connection


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.test_db = Config.TESTS_DIR / "test_positions.db"
        if self.test_db.exists():
            self.test_db.unlink()

    def tearDown(self):
        if self.test_db.exists():
            self.test_db.unlink()

    def test_init_creates_tables_and_indexes(self):
        res = init_database(db_path=self.test_db)
        self.assertTrue(res["success"])
        self.assertEqual(res["code"], Config.EXIT_SUCCESS)

        conn = get_connection(self.test_db)
        cursor = conn.cursor()

        # Check tables
        tables = [
            r[0]
            for r in cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        self.assertIn("vacancies", tables)
        self.assertIn("applications", tables)
        self.assertIn("documents", tables)

        # Check indexes
        indexes = [
            r[0]
            for r in cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        ]
        self.assertIn("idx_vacancies_tier", indexes)
        self.assertIn("idx_vacancies_sector", indexes)
        self.assertIn("idx_applications_status", indexes)

        # Test insert vacancy and application
        cursor.execute(
            """
            INSERT INTO vacancies (id, title, company, url, source, tier, sector)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "v001",
                "Senior Business Analyst",
                "Kapitalbank",
                "https://hh.uz/123",
                "hh.uz",
                1,
                "Finance",
            ),
        )

        cursor.execute(
            """
            INSERT INTO applications (vacancy_id, status, applied_at)
            VALUES (?, ?, ?)
        """,
            ("v001", "applied", "2026-11-08T00:00:00"),
        )
        conn.commit()

        # Query join
        row = cursor.execute(
            """
            SELECT v.title, v.company, a.status 
            FROM vacancies v 
            JOIN applications a ON v.id = a.vacancy_id 
            WHERE v.id = 'v001'
        """
        ).fetchone()
        self.assertEqual(row, ("Senior Business Analyst", "Kapitalbank", "applied"))

        conn.close()


if __name__ == "__main__":
    unittest.main()
