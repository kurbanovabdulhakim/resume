import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config


class TestTemplates(unittest.TestCase):
    def test_master_resume_exists(self):
        master_file = Config.MASTER_DIR / "resume.md"
        self.assertTrue(master_file.exists(), f"Missing {master_file}")
        content = master_file.read_text(encoding="utf-8")
        self.assertIn("Абдулхаким Курбанов", content)

    def test_role_variants_exist(self):
        variants = ["business_analyst.md", "financial_analyst.md", "operations_manager.md"]
        for v in variants:
            vf = Config.VARIANTS_DIR / v
            self.assertTrue(vf.exists(), f"Variant {v} missing")
            content = vf.read_text(encoding="utf-8")
            self.assertGreater(len(content), 100)

    def test_cover_letters_have_standard_placeholders(self):
        templates = [
            "_template_base.md",
            "banking_finance.md",
            "logistics_aviation.md",
            "fmcg_distribution.md",
            "it_analytics.md",
        ]
        required_placeholders = ["{{company}}", "{{position}}", "{{candidate_name}}"]

        for t in templates:
            tf = Config.TEMPLATES_DIR / t
            self.assertTrue(tf.exists(), f"Cover letter template {t} missing")
            content = tf.read_text(encoding="utf-8")
            for req in required_placeholders:
                self.assertIn(req, content, f"Template {t} missing required placeholder {req}")


if __name__ == "__main__":
    unittest.main()
