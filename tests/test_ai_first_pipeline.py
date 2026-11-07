import unittest
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config


class TestAIFirstPipeline(unittest.TestCase):
    def test_full_agent_workflow(self):
        py = sys.executable

        # 1. Initialize test database
        test_db = Config.TESTS_DIR / "test_e2e_agent.db"
        if test_db.exists():
            test_db.unlink()

        init_cmd = [py, str(Config.SCRIPTS_DIR / "init_db.py"), "--db-path", str(test_db), "--json"]
        out_init = subprocess.check_output(init_cmd, text=True)
        data_init = json.loads(out_init)
        self.assertTrue(data_init["success"])
        self.assertIn("vacancies", data_init["tables"])

        # 2. Add sample position via CLI
        add_cmd = [
            py, str(Config.SCRIPTS_DIR / "add_position.py"),
            "--title", "Lead Financial Controller",
            "--company", "Apex Insurance",
            "--url", "https://hh.uz/vacancy/888777",
            "--tier", "1",
            "--sector", "Finance",
            "--notes", "Direct outreach from partner",
            "--db-path", str(test_db),
            "--json",
        ]
        out_add = subprocess.check_output(add_cmd, text=True)
        data_add = json.loads(out_add)
        self.assertTrue(data_add["success"])
        vid = data_add["vacancy_id"]
        self.assertEqual(data_add["tier"], 1)

        # 3. Advance recruitment status to 'invited'
        status_cmd = [
            py, str(Config.SCRIPTS_DIR / "update_status.py"),
            "--vacancy-id", vid,
            "--status", "invited",
            "--notes", "Interview scheduled with Head of Finance",
            "--db-path", str(test_db),
            "--json",
        ]
        out_status = subprocess.check_output(status_cmd, text=True)
        data_status = json.loads(out_status)
        self.assertTrue(data_status["success"])
        self.assertEqual(data_status["status"], "invited")

        # 4. Generate tailored cover letter & CV
        gen_cmd = [
            py, str(Config.SCRIPTS_DIR / "generate_docs.py"),
            "--vacancy-id", vid,
            "--format", "md",
            "--db-path", str(test_db),
            "--json",
        ]
        out_gen = subprocess.check_output(gen_cmd, text=True)
        data_gen = json.loads(out_gen)
        self.assertTrue(data_gen["success"])
        cl_path = Path(data_gen["files"]["cover_letter_md"])
        self.assertTrue(cl_path.exists())
        self.assertIn("Apex Insurance", cl_path.read_text(encoding="utf-8"))

        # 5. Compile dashboard and AI context
        dash_html = Config.TESTS_DIR / "e2e_dashboard.html"
        dash_pipe = Config.TESTS_DIR / "e2e_PIPELINE.md"
        dash_ctx = Config.TESTS_DIR / "e2e_AI_CONTEXT.md"

        dash_cmd = [
            py, str(Config.SCRIPTS_DIR / "dashboard.py"),
            "--db-path", str(test_db),
            "--html-path", str(dash_html),
            "--json",
        ]
        out_dash = subprocess.check_output(dash_cmd, text=True)
        data_dash = json.loads(out_dash)
        self.assertTrue(data_dash["success"])
        self.assertEqual(data_dash["total_vacancies"], 1)
        self.assertEqual(data_dash["status_counts"]["invited"], 1)

        # Cleanup
        for f in (test_db, dash_html, dash_pipe, dash_ctx):
            if f.exists():
                f.unlink()


if __name__ == "__main__":
    unittest.main()
