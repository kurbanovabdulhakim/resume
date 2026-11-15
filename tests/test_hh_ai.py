import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.hh_ai import (
    audit_cover_letter,
    generate_cover_letter,
    load_candidate_profile,
    score_vacancy,
)


class TestHHAI(unittest.TestCase):
    def test_load_candidate_profile_reads_master_resume(self):
        profile = load_candidate_profile()
        self.assertIn("Абдулхаким Курбанов", profile["name"])
        self.assertIn("EXPLORER LOGISTICS", profile["raw_text"])
        self.assertIn("Ravnaq Bank", profile["raw_text"])

    def test_deterministic_scoring_accepts_finance_rejects_mismatch(self):
        good = {
            "id": "139244548",
            "title": "Старший финансовый аналитик",
            "company": "AVO.UZ",
            "tier": 1,
            "sector": "Finance",
        }
        bad = {
            "id": "139272294",
            "title": "Scrum-мастер",
            "company": "HamkorBank",
            "tier": 1,
            "sector": "Finance",
        }
        bad_mkt = {
            "id": "139188607",
            "title": "Директор по маркетингу (Chief Marketing Officer)",
            "company": "АО OPEN BANK AJ",
            "tier": 1,
            "sector": "Finance",
        }

        res_good = score_vacancy(good, use_llm=False)
        res_bad = score_vacancy(bad, use_llm=False)
        res_mkt = score_vacancy(bad_mkt, use_llm=False)

        self.assertTrue(res_good["fit"])
        self.assertGreaterEqual(res_good["score"], 70)
        self.assertEqual(res_good["cv_variant"], "financial_analyst")

        self.assertFalse(res_bad["fit"])
        self.assertLess(res_bad["score"], 55)
        self.assertFalse(res_mkt["fit"])
        self.assertLess(res_mkt["score"], 55)

    def test_audit_cover_letter_flags_ai_tells_and_hallucinations(self):
        bad_em_dash = "Здравствуйте! Я хочу — работать у вас в компании AVO.UZ на позиции аналитика и принести пользу." * 3
        self.assertFalse(audit_cover_letter(bad_em_dash, "AVO.UZ", "Финансовый аналитик")["ok"])

        bad_third_person = (
            "Искренне рад приветствовать тебя. В команду пришел Абдулхаким Курбанов, его опыт в оптимизации "
            "позволит достичь новых высот и привести компанию к процветанию и синергии."
        )
        audit_3p = audit_cover_letter(bad_third_person, "AVO.UZ", "Финансовый аналитик")
        self.assertFalse(audit_3p["ok"])
        self.assertGreaterEqual(len(audit_3p["issues"]), 2)

        bad_role = (
            "Здравствуйте! Откликаюсь на позицию Старший финансовый аналитик в AVO.UZ. "
            "Ранее я работал финансовым аналитиком в Ravnaq Bank и руководил операциями в Explorer Logistics, "
            "где оптимизировал затраты на 18% и ускорил обработку заказов на 25%. Буду рад обсудить задачи на встрече."
        )
        audit_role = audit_cover_letter(bad_role, "AVO.UZ", "Старший финансовый аналитик")
        self.assertFalse(audit_role["ok"])

        bad_cliche = (
            "Добрый день! Я идеальным кандидатом считаю себя для AVO.UZ и готов внести свой вклад в успех компании. "
            "Мое опыт в аналитике поможет решить любые задачи руководства в ближайшее время и дальше."
        )
        self.assertFalse(audit_cover_letter(bad_cliche, "AVO.UZ", "Старший финансовый аналитик")["ok"])

        bad_truncated = (
            "Здравствуйте! Откликаюсь на позицию Финансовый аналитик в AVO.UZ. "
            "В Explorer Logistics настроил отчетность P&L и снизил затраты на 18%, а также ускорил заказы на 25%, что"
        )
        self.assertFalse(audit_cover_letter(bad_truncated, "AVO.UZ", "Финансовый аналитик")["ok"])

        bad_not_only = (
            "Здравствуйте! Откликаюсь на позицию Финансовый аналитик в AVO.UZ. "
            "Эти навыки позволили мне не только оценить показатели, но и сократить издержки на 18% в компании Explorer Logistics. "
            "Буду рад обсудить задачи на собеседовании."
        )
        self.assertFalse(audit_cover_letter(bad_not_only, "AVO.UZ", "Финансовый аналитик")["ok"])

        clean = (
            "Здравствуйте! Меня заинтересовала вакансия «Старший финансовый аналитик» в AVO.UZ.\n\n"
            "У меня экономическое образование (Ташкентский финансовый институт) и практический опыт "
            "финансового контроля и операционного управления: в Explorer Logistics (CEO/COO) настроил "
            "управленческую отчетность P&L и снизил накладные расходы на 18%, а в АКБ «Равнак-банк» "
            "курировал стандарты сервиса и сократил операционные ошибки на 22%.\n\n"
            "Работаю с SQL, Excel, Power BI и Python. Буду рад обсудить ваши задачи на собеседовании."
        )
        clean_signed = (
            "Здравствуйте! Меня заинтересовала вакансия «Старший финансовый аналитик» в AVO.UZ.\n\n"
            "В Explorer Logistics я выстроил управленческий P&L и снизил накладные расходы на 18%, "
            "а в Ravnaq Bank отвечал за контроль стандартов сервиса (-22% ошибок).\n\n"
            "Работаю в Excel, SQL, Power BI и Python. Буду рад обсудить задачи на встрече.\n\n"
            "С уважением,\nАбдулхаким Курбанов"
        )
        self.assertTrue(audit_cover_letter(clean_signed, "AVO.UZ", "Старший финансовый аналитик")["ok"])

        audit_clean = audit_cover_letter(clean, "AVO.UZ", "Старший финансовый аналитик")
        self.assertTrue(audit_clean["ok"], f"Unexpected issues: {audit_clean['issues']}")

    def test_generate_cover_letter_falls_back_cleanly_if_llm_produces_garbage(self):
        vac = {
            "id": "139244548",
            "title": "Старший финансовый аналитик",
            "company": "AVO.UZ",
            "tier": 1,
            "sector": "Finance",
        }
        garbage = "В команду пришел Абдулхаким — бесспорно это не просто опыт, а синергия к процветанию!"
        with patch("scripts.hh_ai._call_ollama_chat", return_value=garbage):
            res = generate_cover_letter(vac, backend="ollama")
        self.assertEqual(res["source"], "template_fallback")
        self.assertTrue(res["audit"]["ok"])
        self.assertNotIn("—", res["text"])
        self.assertIn("AVO.UZ", res["text"])

    def test_generate_cover_letter_accepts_clean_llm_output(self):
        vac = {
            "id": "138707593",
            "title": "Финансовый бизнес партнер",
            "company": "UZUM TECHNOLOGIES",
            "tier": 1,
            "sector": "Finance",
        }
        clean_llm = (
            "Здравствуйте! Откликаюсь на позицию «Финансовый бизнес партнер» в UZUM TECHNOLOGIES.\n\n"
            "Опираюсь на экономическое образование в ТФИ и опыт руководства в Explorer Logistics (CEO/COO), "
            "где выстроил управленческий P&L, перераспределил ресурсы по маржинальности и снизил накладные расходы на 18%. "
            "Ранее в Ravnaq Bank отвечал за контроль стандартов обслуживания и уменьшил операционные ошибки на 22%.\n\n"
            "Свободно использую Excel, SQL, Power BI и Python для анализа показателей. Буду рад обсудить задачи на интервью."
        )
        with patch("scripts.hh_ai._call_ollama_chat", return_value=clean_llm):
            res = generate_cover_letter(vac, backend="ollama")
        self.assertEqual(res["source"], "llm")
        self.assertTrue(res["audit"]["ok"])
        self.assertEqual(res["cv_variant"], "financial_analyst")

    def test_finance_english_title_matches_financial_analyst_and_respect_excludes_flag(self):
        eng_vac = {
            "id": "13999001",
            "title": "Finance Specialist (строительство)",
            "company": "OOO UET CONSTRUCTION",
            "tier": 2,
            "sector": "General",
        }
        res_eng = score_vacancy(eng_vac, use_llm=False, min_score=55)
        self.assertTrue(res_eng["fit"])
        self.assertEqual(res_eng["cv_variant"], "financial_analyst")

        excluded_title = {
            "id": "13999002",
            "title": "Бухгалтер по маркетингу (Marketing Finance)",
            "company": "TestCorp",
            "tier": 2,
            "sector": "Finance",
        }
        res_blocked = score_vacancy(excluded_title, use_llm=False, min_score=0, respect_excludes=True)
        self.assertFalse(res_blocked["fit"])

        res_forced = score_vacancy(excluded_title, use_llm=False, min_score=0, respect_excludes=False)
        self.assertTrue(res_forced["fit"])


if __name__ == "__main__":
    unittest.main()
