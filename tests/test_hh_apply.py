import io
import json
import subprocess
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import get_connection, init_database
from scripts.hh_apply import (
    OfficialApiDriver,
    SubmitResult,
    build_hh_page_url,
    extract_serp_cards_from_html,
    inspect_hh_page,
    run_apply_session,
    upsert_harvested_cards,
)
from scripts.hh_queue import load_queue, remaining_daily_quota


class _FakeDriver:
    def __init__(self, script_map):
        self.script_map = script_map
        self.calls = []
        self.closed = False

    def prepare(self):
        return None

    def apply(self, item, confirm_mode="none", on_questions="defer", prompt_fn=None):
        vid = item["id"]
        self.calls.append((vid, confirm_mode))
        res = self.script_map[vid]
        if callable(res):
            return res(item, confirm_mode, on_questions, prompt_fn)
        return res

    def close(self):
        self.closed = True


class TestHHApply(unittest.TestCase):
    def setUp(self):
        self.test_db = Config.TESTS_DIR / "test_hh_apply.db"
        self.test_queue = Config.TESTS_DIR / "test_hh_apply_queue.json"
        self.test_state = Config.TESTS_DIR / "test_hh_apply_state.json"
        self.dash_html = Config.TESTS_DIR / "test_apply_dash.html"
        self.dash_pipe = Config.TESTS_DIR / "test_apply_pipe.md"
        self.dash_ctx = Config.TESTS_DIR / "test_apply_ctx.md"
        for p in (self.test_db, self.test_queue, self.test_state, self.dash_html, self.dash_pipe, self.dash_ctx):
            if p.exists():
                p.unlink()
        init_database(self.test_db)

    def tearDown(self):
        for p in (self.test_db, self.test_queue, self.test_state, self.dash_html, self.dash_pipe, self.dash_ctx):
            if p.exists():
                p.unlink()

    def test_inspect_hh_page_states(self):
        self.assertEqual(
            inspect_hh_page("https://hh.uz/account/login", "Войти", {"apply_btn": False}),
            "captcha_or_login",
        )
        self.assertEqual(
            inspect_hh_page("https://tashkent.hh.uz/vacancy/123", "Напишите телефон, чтобы работодатель мог связаться с вами", {"auth_form": True}),
            "captcha_or_login",
        )
        self.assertEqual(
            inspect_hh_page("https://tashkent.hh.uz/vacancy/123", "Войти Создать резюме", {"login_btn": True, "apply_btn": True}),
            "captcha_or_login",
        )
        self.assertEqual(
            inspect_hh_page("https://tashkent.hh.uz/vacancy/123", "Подтвердите, что вы не робот smartcaptcha", {}),
            "captcha_or_login",
        )
        self.assertEqual(
            inspect_hh_page("https://tashkent.hh.uz/vacancy/123", "Вакансия в архиве", {"apply_btn": False}),
            "archived",
        )
        self.assertEqual(
            inspect_hh_page("https://tashkent.hh.uz/vacancy/123", "Вы откликнулись на эту вакансию", {"already_applied": True}),
            "already_applied",
        )
        self.assertEqual(
            inspect_hh_page("https://tashkent.hh.uz/vacancy/123", "Обязанности финансового аналитика", {"apply_btn": True}),
            "ready",
        )

    def test_run_apply_session_handles_all_outcomes_and_db_sync(self):
        conn = get_connection(self.test_db)
        conn.executemany(
            "INSERT INTO vacancies (id, title, company, url, source, tier, sector, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
            [
                ("v_apply", "Старший финансовый аналитик", "AVO.UZ", "https://hh.uz/vacancy/1", "hh.uz", 1, "Finance"),
                ("v_arch", "Финансовый аналитик", "OldCorp", "https://hh.uz/vacancy/2", "hh.uz", 1, "Finance"),
                ("v_done", "Бизнес-аналитик", "Payme", "https://hh.uz/vacancy/3", "hh.uz", 1, "Analytics"),
                ("v_quest", "Операционный менеджер", "Uzum", "https://hh.uz/vacancy/4", "hh.uz", 1, "Logistics"),
            ],
        )
        conn.commit()
        conn.close()

        driver = _FakeDriver(
            {
                "v_apply": SubmitResult("applied", "Cover letter submitted", "financial_analyst"),
                "v_arch": SubmitResult("archived", "Vacancy archived"),
                "v_done": SubmitResult("already_applied", "Synced from HH badge", "business_analyst"),
                "v_quest": SubmitResult("needs_human", "Employer screening questions required"),
            }
        )

        with patch("scripts.hh_apply.sleep_with_jitter"):
            summary = run_apply_session(
                driver=driver,
                mode="browser",
                confirm_mode="none",
                limit=10,
                daily_limit=200,
                backend="none",
                dry_run=False,
                db_path=self.test_db,
                queue_path=self.test_queue,
                state_path=self.test_state,
                refresh_dash=False,
            )

        self.assertTrue(driver.closed)
        self.assertTrue(summary["success"])
        self.assertEqual(summary["applied"], 1)
        self.assertEqual(summary["already_applied"], 1)
        self.assertEqual(summary["archived"], 1)
        self.assertEqual(summary["needs_human"], 1)
        self.assertEqual(remaining_daily_quota(200, state_path=self.test_state), 199)

        conn = get_connection(self.test_db)
        apps = dict(conn.execute("SELECT vacancy_id, status FROM applications").fetchall())
        active_arch = conn.execute("SELECT is_active FROM vacancies WHERE id = 'v_arch'").fetchone()[0]
        conn.close()

        self.assertEqual(apps.get("v_apply"), "applied")
        self.assertEqual(apps.get("v_done"), "applied")
        self.assertNotIn("v_quest", apps)
        self.assertEqual(active_arch, 0)

        q = load_queue(self.test_queue)
        self.assertEqual(q["v_quest"]["status"], "needs_human")
        self.assertEqual(q["v_apply"]["status"], "applied")

    def test_run_apply_session_live_switch_from_mode1_to_mode2_on_captcha(self):
        conn = get_connection(self.test_db)
        conn.execute(
            "INSERT INTO vacancies (id, title, company, url, source, tier, sector, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
            ("v1", "Финансовый аналитик", "HamkorBank", "https://hh.uz/vacancy/11", "hh.uz", 1, "Finance"),
        )
        conn.commit()
        conn.close()

        attempts = {"n": 0}

        def _behavior(item, confirm_mode, on_questions, prompt_fn):
            attempts["n"] += 1
            if attempts["n"] == 1:
                return SubmitResult("captcha_paused", "CAPTCHA detected")
            return SubmitResult("applied", f"Submitted under {confirm_mode}", "financial_analyst")

        driver = _FakeDriver({"v1": _behavior})
        with patch("scripts.hh_apply.sleep_with_jitter"):
            summary = run_apply_session(
                driver=driver,
                mode="browser",
                confirm_mode="none",
                limit=5,
                daily_limit=200,
                backend="none",
                dry_run=False,
                db_path=self.test_db,
                queue_path=self.test_queue,
                state_path=self.test_state,
                prompt_fn=lambda msg: "2",
                refresh_dash=False,
            )

        self.assertEqual(summary["confirm_mode"], "each")
        self.assertEqual(summary["applied"], 1)
        self.assertEqual(driver.calls, [("v1", "none"), ("v1", "each")])

    def test_official_api_driver_handles_403_and_201(self):
        driver = OfficialApiDriver(access_token="fake_token")
        item = {"id": "123", "title": "Финансовый аналитик", "company": "Test", "cv_variant": "financial_analyst", "cover_letter": "Здравствуйте!"}

        class _Resp:
            def __init__(self, status, body):
                self.status = status
                self._body = body.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return self._body

        with patch("urllib.request.urlopen") as m_open:
            m_open.side_effect = [
                _Resp(200, '{"items": [{"id": "res_1", "title": "Финансовый аналитик"}]}'),
                urllib.error.HTTPError("https://api.hh.ru/negotiations", 403, "Forbidden", {}, io.BytesIO(b'{"errors":[{"type":"forbidden"}]}')),
            ]
            res_403 = driver.apply(item)
        self.assertEqual(res_403.status, "needs_human")
        self.assertIn("403", res_403.detail)

        with patch("urllib.request.urlopen") as m_open:
            m_open.side_effect = [
                _Resp(200, '{"items": [{"id": "res_1", "title": "Финансовый аналитик"}]}'),
                _Resp(201, "{}"),
            ]
            res_201 = driver.apply(item)
        self.assertEqual(res_201.status, "applied")

    def test_cli_dry_run_exits_cleanly(self):
        conn = get_connection(self.test_db)
        conn.execute(
            "INSERT INTO vacancies (id, title, company, url, source, tier, sector, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
            ("v99", "Бизнес-аналитик", "Click", "https://hh.uz/vacancy/99", "hh.uz", 1, "Analytics"),
        )
        conn.commit()
        conn.close()

        cmd = [
            sys.executable,
            str(Config.SCRIPTS_DIR / "hh_apply.py"),
            "--dry-run",
            "--limit",
            "1",
            "--backend",
            "none",
            "--db-path",
            str(self.test_db),
            "--queue-path",
            str(self.test_queue),
            "--state-path",
            str(self.test_state),
            "--json",
        ]
        out = subprocess.check_output(cmd, text=True)
        payload = json.loads(out)
        self.assertTrue(payload["success"])
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["simulated"], 1)

    def test_extract_serp_cards_from_html_and_url_page_builder(self):
        self.assertEqual(
            build_hh_page_url("https://tashkent.hh.uz/vacancies/finansovyy_analitik", 0),
            "https://tashkent.hh.uz/vacancies/finansovyy_analitik?page=0",
        )
        self.assertEqual(
            build_hh_page_url("https://tashkent.hh.uz/vacancies/finansovyy_analitik?page=1&items_on_page=50", 4),
            "https://tashkent.hh.uz/vacancies/finansovyy_analitik?items_on_page=50&page=4",
        )

        sample_html = """
        <div data-qa="vacancy-serp__vacancy">
            <a data-qa="serp-item__title" href="https://tashkent.hh.uz/vacancy/140001?query=fin">Finance Specialist (строительство)</a>
            <a data-qa="vacancy-serp__vacancy-employer" href="/employer/1">OOO UET CONSTRUCTION</a>
        </div>
        <div data-qa="vacancy-serp__vacancy">
            <a data-qa="serp-item__title" href="https://tashkent.hh.uz/vacancy/140002?from=vacancy_search_list">Финансовый менеджер</a>
            <span data-qa="vacancy-serp__vacancy-employer">OSMAN Group</span>
            <span>Вы откликнулись</span>
        </div>
        """
        cards = extract_serp_cards_from_html(sample_html)
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["id"], "140001")
        self.assertEqual(cards[0]["company"], "OOO UET CONSTRUCTION")
        self.assertFalse(cards[0]["already_applied"])
        self.assertEqual(cards[1]["id"], "140002")
        self.assertEqual(cards[1]["company"], "OSMAN Group")
        self.assertTrue(cards[1]["already_applied"])

    def test_run_apply_session_harvests_start_url_and_prioritizes_before_general_db(self):
        conn = get_connection(self.test_db)
        conn.execute(
            "INSERT INTO vacancies (id, title, company, url, source, tier, sector, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
            ("db_other", "Старший финансовый аналитик", "AVO.UZ", "https://hh.uz/vacancy/db_other", "hh.uz", 1, "Finance"),
        )
        conn.commit()
        conn.close()

        cards = [
            {
                "id": "u1",
                "title": "Finance Specialist (строительство)",
                "company": "OOO UET CONSTRUCTION",
                "url": "https://tashkent.hh.uz/vacancy/u1",
                "already_applied": False,
            }
        ]

        class _HarvestDriver(_FakeDriver):
            def harvest_url(self, start_url, max_pages=25, limit=500, db_path=None, queue_path=None):
                res = upsert_harvested_cards(
                    cards,
                    db_path=db_path,
                    queue_path=queue_path,
                    priority_url=start_url,
                )
                return res["queued"]

        drv = _HarvestDriver(
            {
                "u1": SubmitResult("applied", "OK u1", "financial_analyst", "Letter u1"),
                "db_other": SubmitResult("applied", "OK db", "financial_analyst", "Letter db"),
            }
        )
        stats = run_apply_session(
            driver=drv,
            confirm_mode="none",
            limit=5,
            daily_limit=200,
            min_score=55,
            target_min_score=0,
            wave_size=0,
            min_delay=0.0,
            max_delay=0.0,
            backend="none",
            start_url="https://tashkent.hh.uz/vacancies/finansovyy_analitik",
            db_path=self.test_db,
            queue_path=self.test_queue,
            state_path=self.test_state,
            refresh_dash=False,
            verbose=False,
        )
        self.assertEqual(stats["harvested"], 1)
        self.assertEqual(stats["applied"], 2)
        self.assertEqual([c[0] for c in drv.calls], ["u1", "db_other"])

    def test_type_human_paced_text_sends_keys_and_respects_word_pacing(self):
        from scripts.hh_apply import type_human_paced_text

        class MockBox:
            def __init__(self):
                self.keys = []
            def send_keys(self, s):
                self.keys.append(s)

        box = MockBox()
        text = "Здравствуйте! Меня заинтересовала данная вакансия аналитика."
        word_count = len(text.split()) # 5 words

        sleeps = []
        def mock_sleeper(sec):
            sleeps.append(sec)

        type_human_paced_text(box, text, word_delay_range=(2.0, 3.0), sleeper=mock_sleeper)

        reconstructed = "".join(box.keys)
        self.assertEqual(reconstructed, text)
        total_time = sum(sleeps)
        avg_per_word = total_time / word_count
        self.assertGreaterEqual(avg_per_word, 2.0)
        self.assertLessEqual(avg_per_word, 3.0)
        self.assertGreater(len(box.keys), word_count)


if __name__ == "__main__":
    unittest.main()
