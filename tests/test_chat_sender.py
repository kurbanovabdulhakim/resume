import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.init_db import init_database


class TestChatSender(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.tmp_dir.name)
        self.test_db = self.test_dir / "test_positions.db"
        init_database(self.test_db)

        conn = sqlite3.connect(self.test_db)
        conn.execute(
            """
            INSERT INTO vacancies (id, title, company, url, is_active)
            VALUES ('111222', 'Финансовый аналитик', 'Test Company', 'https://hh.uz/vacancy/111222', 1)
            """
        )
        conn.execute(
            """
            INSERT INTO applications (vacancy_id, status, applied_at, cover_letter_sent)
            VALUES ('111222', 'applied', '2026-11-15T00:00:00', 0)
            """
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_send_chat_cover_letter_success(self):
        from scripts.hh_chat_sender import send_chat_cover_letter

        class MockElement:
            def __init__(self, tag="div", text="", href=""):
                self.tag = tag
                self.text = text
                self._href = href
                self.keys = []
                self.clicked = False

            def get_attribute(self, name):
                if name == "href":
                    return self._href
                return ""

            def send_keys(self, s):
                self.keys.append(s)

            def click(self):
                self.clicked = True

            def is_displayed(self):
                return True

        class MockDriver:
            def __init__(self):
                self.current_url = ""
                self.topic_btn = MockElement("a", "Перейти к переписке", "https://tashkent.hh.uz/applicant/negotiations/topic?topicId=999")
                self.textarea = MockElement("textarea")
                self.send_btn = MockElement("button", "Отправить")
                self.history = []

            def get(self, url):
                self.current_url = url

            def find_elements(self, by, selector):
                if "vacancy-response-link-view-topic" in selector or "topic" in selector:
                    return [self.topic_btn]
                if "chat-input" in selector or "textarea" in selector:
                    return [self.textarea]
                if "send" in selector:
                    return [self.send_btn]
                if "chat-message" in selector:
                    return self.history
                return []

        drv = MockDriver()
        letter = "Здравствуйте! Направляю резюме и сопроводительное письмо."
        res = send_chat_cover_letter(
            driver=drv,
            vacancy_id="111222",
            cover_letter=letter,
            db_path=self.test_db,
            fast_typing=True,
        )

        self.assertEqual(res["status"], "sent")
        self.assertTrue(self.test_db.exists())
        self.assertTrue(drv.send_btn.clicked)
        self.assertEqual("".join(drv.textarea.keys), letter)

        # Check DB updated
        conn = sqlite3.connect(self.test_db)
        row = conn.execute("SELECT cover_letter_sent, notes FROM applications WHERE vacancy_id = '111222'").fetchone()
        conn.close()
        self.assertEqual(row[0], 1)
        self.assertIn("chat", row[1].lower())

    def test_send_chat_cover_letter_dry_run(self):
        from scripts.hh_chat_sender import send_chat_cover_letter

        class MockElement:
            def __init__(self, tag="div", text="", href=""):
                self.tag = tag
                self.text = text
                self._href = href
                self.keys = []
                self.clicked = False

            def get_attribute(self, name):
                return self._href if name == "href" else ""

            def send_keys(self, s):
                self.keys.append(s)

            def click(self):
                self.clicked = True

        class MockDriver:
            def __init__(self):
                self.current_url = ""
                self.topic_btn = MockElement("a", "Перейти", "https://tashkent.hh.uz/applicant/negotiations/topic?topicId=999")
                self.textarea = MockElement("textarea")
                self.send_btn = MockElement("button", "Отправить")

            def get(self, url):
                self.current_url = url

            def find_elements(self, by, selector):
                if "topic" in selector:
                    return [self.topic_btn]
                if "chat-input" in selector or "textarea" in selector:
                    return [self.textarea]
                if "send" in selector:
                    return [self.send_btn]
                return []

        drv = MockDriver()
        res = send_chat_cover_letter(
            driver=drv,
            vacancy_id="111222",
            cover_letter="Тестовое письмо",
            db_path=self.test_db,
            fast_typing=True,
            dry_run=True,
        )

        self.assertEqual(res["status"], "dry_run")
        self.assertFalse(drv.send_btn.clicked)

        conn = sqlite3.connect(self.test_db)
        row = conn.execute("SELECT cover_letter_sent FROM applications WHERE vacancy_id = '111222'").fetchone()
        conn.close()
        # In dry run, DB should remain 0
        self.assertEqual(row[0], 0)

    def test_send_chat_cover_letter_already_in_chat(self):
        from scripts.hh_chat_sender import send_chat_cover_letter

        class MockElement:
            def __init__(self, text=""):
                self.text = text
                self.clicked = False

            def get_attribute(self, name):
                return "https://tashkent.hh.uz/applicant/negotiations/topic?topicId=999"

        class MockDriver:
            def __init__(self):
                self.current_url = ""
                self.topic_btn = MockElement()
                self.existing_msg = MockElement("Здравствуйте! Направляю резюме и сопроводительное письмо.")

            def get(self, url):
                self.current_url = url

            def find_elements(self, by, selector):
                if "topic" in selector:
                    return [self.topic_btn]
                if "chat-message" in selector:
                    return [self.existing_msg]
                return []

        drv = MockDriver()
        res = send_chat_cover_letter(
            driver=drv,
            vacancy_id="111222",
            cover_letter="Здравствуйте! Направляю резюме и сопроводительное письмо.",
            db_path=self.test_db,
            fast_typing=True,
        )

        self.assertEqual(res["status"], "already_sent")

    def test_get_pending_chat_vacancies(self):
        import json
        from scripts.hh_chat_sender import get_pending_chat_vacancies

        q_file = self.test_dir / "test_queue.json"
        q_data = {
            "items": {
                "111222": {
                    "vacancy_id": "111222",
                    "title": "Финансовый аналитик",
                    "company": "Test Company",
                    "status": "applied",
                    "cover_letter": "Здравствуйте! Это полное сопроводительное письмо более 20 символов.",
                },
                "333444": {
                    "vacancy_id": "333444",
                    "title": "Менеджер",
                    "company": "Other",
                    "status": "queued",  # not applied
                    "cover_letter": "Письмо",
                },
                "555666": {
                    "vacancy_id": "555666",
                    "title": "Аналитик",
                    "company": "Other 2",
                    "status": "applied",
                    "cover_letter": "1",  # invalid letter (digit 1)
                },
            }
        }
        with open(q_file, "w", encoding="utf-8") as f:
            json.dump(q_data, f)

        pending = get_pending_chat_vacancies(queue_path=q_file, db_path=self.test_db)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["vacancy_id"], "111222")


if __name__ == "__main__":
    unittest.main()
