import unittest
import sqlite3
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.repair_db_cover_letters import repair_database_cover_letters


class TestRepairDBCoverLetters(unittest.TestCase):
    def setUp(self):
        self.test_db = PROJECT_ROOT / "tests" / "test_repair.db"
        if self.test_db.exists():
            self.test_db.unlink()
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE vacancies (
                id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                url TEXT
            )
        """)
        c.execute("""
            CREATE TABLE applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vacancy_id TEXT,
                status TEXT,
                applied_at TEXT,
                cover_letter_sent TEXT,
                notes TEXT
            )
        """)
        c.execute("INSERT INTO vacancies VALUES ('999001', 'Финансовый аналитик', 'Тест Банк', 'http://hh/999001')")
        c.execute("INSERT INTO applications (vacancy_id, status, applied_at, cover_letter_sent, notes) VALUES ('999001', 'applied', '2026-11-15T12:00:00', '1', 'Dashboard test')")
        conn.commit()
        conn.close()

    def tearDown(self):
        if self.test_db.exists():
            self.test_db.unlink()

    def test_repair_replaces_one_with_letter(self):
        count = repair_database_cover_letters(self.test_db, dry_run=False)
        self.assertGreaterEqual(count, 1)

        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        row = c.execute("SELECT cover_letter_sent FROM applications WHERE vacancy_id = '999001'").fetchone()
        conn.close()

        letter = row[0]
        self.assertNotEqual(letter, "1")
        self.assertIn("Финансовый аналитик", letter)
        self.assertIn("Тест Банк", letter)
        self.assertIn("Explorer Logistics", letter)
        self.assertIn("Абдулхаким Курбанов", letter)


if __name__ == "__main__":
    unittest.main()
