import unittest
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.logger import log_event, get_today_log_file


class TestConfig(unittest.TestCase):
    def test_paths_derivable(self):
        self.assertEqual(Config.PROJECT_ROOT.resolve(), PROJECT_ROOT.resolve())
        self.assertEqual(Config.DB_PATH.name, "positions.db")
        self.assertEqual(Config.DB_PATH.parent.name, "db")
        self.assertEqual(Config.GENERATED_DIR.name, "generated")
        self.assertEqual(Config.TEMPLATES_DIR.name, "cover_letters")
        self.assertEqual(Config.VARIANTS_DIR.name, "variants")
        self.assertEqual(Config.MASTER_DIR.name, "master")

    def test_exit_codes(self):
        self.assertEqual(Config.EXIT_SUCCESS, 0)
        self.assertEqual(Config.EXIT_ERROR, 1)
        self.assertEqual(Config.EXIT_NO_DATA, 2)

    def test_logger_writes_jsonl(self):
        log_file = get_today_log_file()
        test_payload = {"action": "unit_test_run", "status": "ok"}
        log_event("TEST_EVENT", test_payload)
        self.assertTrue(log_file.exists())
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            self.assertTrue(any("TEST_EVENT" in line for line in lines))

    def test_default_hermes_queue_paths_no_dot(self):
        self.assertNotIn(Path(""), Config.DEFAULT_HERMES_QUEUE_PATHS)
        self.assertNotIn(Path("."), Config.DEFAULT_HERMES_QUEUE_PATHS)

    def test_hh_autonomy_config_constants(self):
        self.assertEqual(Config.DATA_DIR.name, "data")
        self.assertEqual(Config.HH_QUEUE_FILE.parent.name, "data")
        self.assertEqual(Config.HH_STATE_FILE.parent.name, "data")
        self.assertEqual(Config.OLLAMA_NUM_CTX, 12288)
        self.assertEqual(Config.HH_SESSION_PROFILE_DIR.name, "hh_main_session")
        self.assertTrue(Config.OLLAMA_BASE_URL.startswith("http://"))


if __name__ == "__main__":
    unittest.main()
