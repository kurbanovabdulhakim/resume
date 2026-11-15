import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import get_connection, init_database
from scripts.hh_queue import (
    load_autonomy_state,
    normalize_target_url,
    record_daily_apply,
    remaining_daily_quota,
    select_candidate_vacancies,
    upsert_queue_item,
)


class TestHHQueue(unittest.TestCase):
    def setUp(self):
        self.test_db = Config.TESTS_DIR / "test_hh_queue.db"
        self.test_queue = Config.TESTS_DIR / "test_hh_queue.json"
        self.test_state = Config.TESTS_DIR / "test_hh_state.json"
        for p in (self.test_db, self.test_queue, self.test_state):
            if p.exists():
                p.unlink()
        init_database(self.test_db)

        conn = get_connection(self.test_db)
        rows = [
            ("v1", "Старший финансовый аналитик", "AVO.UZ", "https://hh.uz/vacancy/1", "hh.uz", 1, "Finance", 1),
            ("v2", "Scrum-мастер", "HamkorBank", "https://hh.uz/vacancy/2", "hh.uz", 1, "Finance", 1),
            ("v3", "Бизнес-аналитик", "Click", "https://hh.uz/vacancy/3", "hh.uz", 1, "Analytics", 1),
            ("v4", "Операционный менеджер", "Alpha LLC", "https://hh.uz/vacancy/4", "hh.uz", 3, "Logistics", 1),
            ("v5", "Финансовый аналитик (Applied)", "Uzum", "https://hh.uz/vacancy/5", "hh.uz", 1, "Finance", 1),
            ("v6", "Финансовый аналитик (Archived)", "TBC", "https://hh.uz/vacancy/6", "hh.uz", 1, "Finance", 0),
        ]
        conn.executemany(
            "INSERT INTO vacancies (id, title, company, url, source, tier, sector, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.execute(
            "INSERT INTO applications (vacancy_id, status) VALUES ('v5', 'applied')"
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        for p in (self.test_db, self.test_queue, self.test_state):
            if p.exists():
                p.unlink()

    def test_select_candidates_filters_applied_archived_and_mismatches(self):
        upsert_queue_item({"vacancy_id": "v4", "status": "needs_human"}, queue_path=self.test_queue)
        candidates = select_candidate_vacancies(
            db_path=self.test_db, limit=10, min_score=55, queue_path=self.test_queue
        )
        ids = [c["id"] for c in candidates]
        self.assertIn("v1", ids)
        self.assertIn("v3", ids)
        self.assertNotIn("v2", ids)  # Scrum-master excluded
        self.assertNotIn("v4", ids)  # Already deferred needs_human
        self.assertNotIn("v5", ids)  # Already applied in DB
        self.assertNotIn("v6", ids)  # Inactive in DB

    def test_daily_quota_tracking_and_rollover(self):
        self.assertEqual(remaining_daily_quota(200, state_path=self.test_state, today="2026-11-11"), 200)
        record_daily_apply(state_path=self.test_state, count=5, today="2026-11-11")
        self.assertEqual(remaining_daily_quota(200, state_path=self.test_state, today="2026-11-11"), 195)
        record_daily_apply(state_path=self.test_state, count=200, today="2026-11-11")
        self.assertEqual(remaining_daily_quota(200, state_path=self.test_state, today="2026-11-11"), 0)

        # Next calendar day resets daily count to 0 -> 200 remaining
        state_next = load_autonomy_state(state_path=self.test_state, today="2026-11-12")
        self.assertEqual(state_next["applied_today"], 0)
        self.assertEqual(remaining_daily_quota(200, state_path=self.test_state, today="2026-11-12"), 200)

    def test_target_url_candidates_prioritized_first_with_min_score_zero(self):
        target = normalize_target_url("https://tashkent.hh.uz/vacancies/finansovyy_analitik?page=3")
        self.assertEqual(target, "https://tashkent.hh.uz/vacancies/finansovyy_analitik")

        # Add lower-score/excluded-keyword target vacancies that belong to the explicit URL batch
        conn = get_connection(self.test_db)
        conn.executemany(
            "INSERT INTO vacancies (id, title, company, url, source, tier, sector, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
            [
                ("t1", "Finance Specialist (строительство)", "OOO UET CONSTRUCTION", "https://tashkent.hh.uz/vacancy/101", "hh.uz", 2, "General"),
                ("t2", "Младший ассистент в отдел маркетинга и финансов", "Apex", "https://tashkent.hh.uz/vacancy/102", "hh.uz", 3, "General"),
            ],
        )
        conn.commit()
        conn.close()

        upsert_queue_item({"vacancy_id": "t2", "status": "skipped", "priority_url": target, "priority_rank": 2}, queue_path=self.test_queue)
        upsert_queue_item({"vacancy_id": "t1", "status": "queued", "priority_url": target, "priority_rank": 1}, queue_path=self.test_queue)

        ordered = select_candidate_vacancies(
            db_path=self.test_db,
            limit=10,
            min_score=55,
            queue_path=self.test_queue,
            target_url=target,
            target_min_score=0,
        )
        ids = [c["id"] for c in ordered]
        # Target URL rows appear strictly before high-score non-target DB rows (v1, v3), in rank order
        self.assertEqual(ids[:2], ["t1", "t2"])
        self.assertIn("v1", ids[2:])
        self.assertIn("v3", ids[2:])

        only_target = select_candidate_vacancies(
            db_path=self.test_db,
            limit=10,
            min_score=55,
            queue_path=self.test_queue,
            target_url=target,
            target_min_score=0,
            target_only=True,
        )
        self.assertEqual([c["id"] for c in only_target], ["t1", "t2"])


if __name__ == "__main__":
    unittest.main()
