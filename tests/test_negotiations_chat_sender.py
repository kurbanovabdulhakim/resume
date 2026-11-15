import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.init_db import init_database


class TestNegotiationsChatSender(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.tmp_dir.name)
        self.test_db = self.test_dir / "test_positions.db"
        init_database(self.test_db)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_detect_candidate_chat_with_one(self):
        from scripts.hh_negotiations_chat_sender import is_candidate_chat

        # 1. Chat with only '1' as response
        msgs_one = [
            "DREAMLIFE\nБыл онлайн вчера\nВакансия\nSotuv xodimlari\nСегодня\nОтклик на вакансию\n\n1\n\n18:30"
        ]
        self.assertTrue(is_candidate_chat(msgs_one))

        # 2. Chat with already complete cover letter
        msgs_complete = [
            "ANNEXURE\nВакансия\nЗаместитель директора\nОтклик на вакансию\n\nЗдравствуйте! Меня заинтересовала позиция в ООО ANNEXURE..."
        ]
        self.assertFalse(is_candidate_chat(msgs_complete))

        # 3. Empty chat
        self.assertTrue(is_candidate_chat([]))

        # 4. Chat where initial message was 1, but later a full letter was sent
        msgs_repaired = [
            "Отклик на вакансию\n\n1",
            "Здравствуйте! Направляю актуальное сопроводительное письмо. В Explorer Logistics я улучшил процессы... С уважением, Абдулхаким Курбанов"
        ]
        self.assertFalse(is_candidate_chat(msgs_repaired))

    def test_extract_vacancy_info_from_chat(self):
        from scripts.hh_negotiations_chat_sender import extract_chat_metadata

        links = [
            {"href": "https://hh.uz/employer/12406906?hhtmFrom=chat", "text": "DREAMLIFE"},
            {"href": "https://hh.uz/vacancy/139555666?hhtmFrom=chat", "text": "Перейти"},
        ]
        meta = extract_chat_metadata(links, header_text="DREAMLIFE\nВакансия\nSotuv xodimlari")
        self.assertEqual(meta["vacancy_id"], "139555666")
        self.assertEqual(meta["company"], "DREAMLIFE")
        self.assertEqual(meta["title"], "Sotuv xodimlari")


if __name__ == "__main__":
    unittest.main()
