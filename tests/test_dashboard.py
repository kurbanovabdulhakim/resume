import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import init_database, get_connection
from scripts.dashboard import build_dashboard_artifacts


class TestDashboard(unittest.TestCase):
    def setUp(self):
        self.test_db = Config.TESTS_DIR / "test_dash.db"
        if self.test_db.exists():
            self.test_db.unlink()
        init_database(self.test_db)

        # Insert some test vacancies and applications
        conn = get_connection(self.test_db)
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO vacancies (id, title, company, url, tier, sector)
            VALUES 
                ('v1', 'BA', 'Bank 1', 'https://hh.uz/1', 1, 'Finance'),
                ('v2', 'FA', 'Corp 2', 'https://hh.uz/2', 2, 'Finance'),
                ('v3', 'Ops', 'Logistics 3', 'https://hh.uz/3', 3, 'Logistics')
        """
        )
        c.execute(
            """
            INSERT INTO applications (vacancy_id, status, applied_at, last_updated)
            VALUES 
                ('v1', 'interview', '2026-11-01', '2026-11-07'),
                ('v2', 'applied', '2026-11-05', '2026-11-05'),
                ('v3', 'rejected', '2026-10-20', '2026-10-25')
        """
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        if self.test_db.exists():
            self.test_db.unlink()

    def test_generates_all_three_artifacts(self):
        out_html = Config.TESTS_DIR / "test_dashboard.html"
        out_pipe = Config.TESTS_DIR / "test_PIPELINE.md"
        out_ctx = Config.TESTS_DIR / "test_AI_CONTEXT.md"

        try:
            res = build_dashboard_artifacts(
                db_path=self.test_db,
                html_path=out_html,
                pipeline_md_path=out_pipe,
                ai_context_path=out_ctx,
            )
            self.assertTrue(res["success"])
            self.assertTrue(out_html.exists())
            self.assertTrue(out_pipe.exists())
            self.assertTrue(out_ctx.exists())

            # Verify contents
            html_text = out_html.read_text(encoding="utf-8")
            self.assertIn("Bank 1", html_text)
            self.assertIn("interview", html_text.lower())

            pipe_text = out_pipe.read_text(encoding="utf-8")
            self.assertIn("Pipeline Summary", pipe_text)
            self.assertIn("interview", pipe_text.lower())

            ctx_text = out_ctx.read_text(encoding="utf-8")
            self.assertIn("ai-context", ctx_text.lower())
            self.assertIn("total_applications", ctx_text)
        finally:
            for f in (out_html, out_pipe, out_ctx):
                if f.exists():
                    f.unlink()


if __name__ == "__main__":
    unittest.main()
