import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_and_repair_negotiations import classify_chat_status


class TestAuditNegotiations(unittest.TestCase):
    def test_classify_literal_one(self):
        msgs = ["DREAMLIFE\nОтклик на вакансию\n\n1\n\n18:30"]
        res = classify_chat_status(msgs)
        self.assertEqual(res["category"], "belberda")

    def test_classify_already_sent_cover_letter(self):
        msgs = [
            "Отклик на вакансию\n\nЗдравствуйте! Меня заинтересовала позиция в ООО ANNEXURE.\n"
            "В Explorer Logistics я руководил процессами... С уважением, Абдулхаким Курбанов"
        ]
        res = classify_chat_status(msgs)
        self.assertEqual(res["category"], "has_letter")

    def test_classify_empty_messages(self):
        res = classify_chat_status([])
        self.assertEqual(res["category"], "empty")

    def test_classify_short_gibberish(self):
        msgs = ["Отклик на вакансию\n\n."]
        res = classify_chat_status(msgs)
        self.assertEqual(res["category"], "belberda")

    def test_classify_prompt_chips_without_candidate_letter(self):
        msgs = [
            "Здравствуйте!",
            "Какой график работы?",
            "Можно без опыта?",
            "Где находится место работы?"
        ]
        res = classify_chat_status(msgs)
        self.assertEqual(res["category"], "belberda")


if __name__ == "__main__":
    unittest.main()
