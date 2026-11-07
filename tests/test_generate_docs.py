import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import init_database, get_connection
from scripts.generate_docs import generate_documents_for_vacancy


class TestGenerateDocs(unittest.TestCase):
    def setUp(self):
        self.test_db = Config.TESTS_DIR / "test_docs_gen.db"
        if self.test_db.exists():
            self.test_db.unlink()
        init_database(self.test_db)

        # Seed sample vacancy
        conn = get_connection(self.test_db)
        conn.execute(
            """
            INSERT INTO vacancies (id, title, company, url, source, tier, sector)
            VALUES (?, ?, ?, ?, 'hh.uz', 1, 'Finance')
        """,
            ("v_test_99", "Chief Financial Officer", "Asia Alliance Bank", "https://hh.uz/99"),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        if self.test_db.exists():
            self.test_db.unlink()

    def test_generates_markdown_and_records_in_db(self):
        res = generate_documents_for_vacancy(
            vacancy_id="v_test_99",
            doc_formats=["md"],
            db_path=self.test_db,
        )
        self.assertTrue(res["success"])
        self.assertIn("cover_letter_md", res["files"])
        self.assertIn("cv_md", res["files"])

        cl_path = Path(res["files"]["cover_letter_md"])
        self.assertTrue(cl_path.exists())
        content = cl_path.read_text(encoding="utf-8")
        self.assertIn("Asia Alliance Bank", content)
        self.assertIn("Chief Financial Officer", content)

        # Verify DB entry in documents table
        conn = get_connection(self.test_db)
        doc_rows = conn.execute(
            "SELECT doc_type, file_path FROM documents WHERE vacancy_id = 'v_test_99'"
        ).fetchall()
        self.assertGreaterEqual(len(doc_rows), 2)
        conn.close()


if __name__ == "__main__":
    unittest.main()
