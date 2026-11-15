"""
HeadHunter (hh.uz) Multi-Mode Visible Application Runner.

Supports three switchable submission modes (`browser`, `api`, `assist`) and three
confirmation modes (`none`, `batch`, `each`), defaulting to visible Edge +
`hh_main_session` in autonomous wave mode with strict CAPTCHA/login human pauses.

Usage:
    python scripts/hh_apply.py --dry-run --limit 5 --json
    python scripts/hh_apply.py --mode browser --confirm none --daily-limit 200 --wave-size 25
    python scripts/hh_apply.py --mode browser --confirm each --limit 30
    python scripts/hh_apply.py --mode api --limit 20
"""

from __future__ import annotations
import argparse
import dataclasses
import datetime
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.dashboard import build_dashboard_artifacts
from scripts.hh_ai import generate_cover_letter, load_candidate_profile, score_vacancy
from scripts.hh_queue import (
    TERMINAL_QUEUE_STATUSES,
    load_autonomy_state,
    load_queue,
    normalize_target_url,
    record_daily_apply,
    remaining_daily_quota,
    save_queue,
    select_candidate_vacancies,
    upsert_queue_item,
)
from scripts.init_db import get_connection, init_database
from scripts.logger import log_event
from scripts.portals.hh_watcher import classify_tier
from scripts.sync_hermes import normalize_sector
from scripts.update_status import update_application_status


@dataclasses.dataclass
class SubmitResult:
    status: str  # applied | already_applied | archived | needs_human | captcha_paused | skipped | error | dry_run
    detail: str = ""
    cv_variant: Optional[str] = None
    cover_letter: Optional[str] = None


def _beep_alert() -> None:
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        print("\a", end="", flush=True)


def sleep_with_jitter(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def type_human_paced_text(
    element: Any,
    text: str,
    word_delay_range: Tuple[float, float] = (2.0, 3.0),
    sleeper: Callable[[float], None] = sleep_with_jitter,
) -> None:
    """Simulates realistic human typing with configurable average delay per word."""
    if not text:
        return

    words = re.findall(r"\S+|\s+", text)
    word_tokens = [w for w in words if w.strip()]
    if not word_tokens:
        element.send_keys(text)
        return

    min_w, max_w = word_delay_range
    word_budgets = [random.uniform(min_w, max_w) for _ in range(len(word_tokens))]
    w_idx = 0

    for token in words:
        if token.isspace():
            element.send_keys(token)
            continue

        budget = word_budgets[w_idx]
        w_idx += 1
        num_chars = len(token)

        if num_chars <= 1:
            element.send_keys(token)
            sleeper(budget)
            continue

        raw_delays = [random.uniform(0.7, 1.3) for _ in range(num_chars)]
        total_raw = sum(raw_delays)
        scaled_delays = [budget * (r / total_raw) for r in raw_delays]

        for ch, d in zip(token, scaled_delays):
            element.send_keys(ch)
            sleeper(d)


def inspect_hh_page(
    url: str,
    page_text: str,
    selectors_present: Optional[Dict[str, bool]] = None,
) -> str:
    """Classifies current HH page state cleanly without false positives."""
    url_lower = (url or "").lower()
    text_lower = (page_text or "").lower()
    sel = selectors_present or {}

    captcha_markers = (
        "/account/login",
        "/captcha",
        "smartcaptcha",
        "g-recaptcha",
        "ddos-guard",
        "пройдите капчу",
        "текст с картинки",
        "введите текст с картинки",
        "введите код с картинки",
        "подтвердите, что вы не робот",
        "подтвердите, что вы человек",
        "verify you are human",
        "войдите, чтобы откликнуться",
        "введите код из смс",
        "напишите телефон, чтобы работодатель мог связаться с вами",
    )
    if sel.get("auth_form") or sel.get("login_btn") or any(m in url_lower or m in text_lower for m in captcha_markers):
        return "captcha_or_login"

    archived_markers = (
        "вакансия в архиве",
        "вакансия закрыта",
        "работодатель закрыл вакансию",
        "вакансия не найдена",
        "страница не найдена",
    )
    if any(m in text_lower for m in archived_markers):
        return "archived"

    if sel.get("already_applied") or any(
        m in text_lower for m in ("вы откликнулись", "отклик отправлен", "вы уже откликнулись")
    ):
        return "already_applied"

    if sel.get("apply_btn"):
        return "ready"

    return "unknown"


def _find_cached_msedgedriver() -> Optional[Path]:
    cache_root = Path.home() / ".cache" / "selenium" / "msedgedriver" / "win64"
    if not cache_root.is_dir():
        return None
    candidates = sorted(cache_root.glob("*/msedgedriver.exe"), reverse=True)
    return candidates[0] if candidates else None


def _copy_to_clipboard(text: str) -> None:
    try:
        subprocess.run(["clip.exe"], input=text, text=True, check=False)
    except Exception:
        pass


_VOID_HTML_TAGS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
)


def build_hh_page_url(base_url: str, page: int) -> str:
    """Returns a HeadHunter search/category URL pinned to the requested 0-based page."""
    raw = str(base_url or "").strip()
    parts = urllib.parse.urlsplit(raw)
    query_pairs = [
        (k, v)
        for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() != "page"
    ]
    query_pairs.append(("page", str(max(0, int(page)))))
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(query_pairs), "")
    )


class _HHSerpCardParser(HTMLParser):
    """Stdlib HTML parser extracting vacancy cards, employers, and applied markers from HH SERP HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: List[Dict[str, Any]] = []
        self._in_card = False
        self._card_depth = 0
        self._card: Dict[str, Any] = {}
        self._cap_title = False
        self._cap_employer = False
        self._title_parts: List[str] = []
        self._emp_parts: List[str] = []
        self._text_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}
        data_qa = attr_map.get("data-qa", "")
        is_void = tag.lower() in _VOID_HTML_TAGS

        if not self._in_card and data_qa == "vacancy-serp__vacancy":
            self._in_card = True
            self._card_depth = 0 if is_void else 1
            self._card = {"id": "", "title": "", "company": "", "url": "", "already_applied": False}
            self._title_parts = []
            self._emp_parts = []
            self._text_parts = []
            return

        if not self._in_card:
            return

        if not is_void:
            self._card_depth += 1

        if tag.lower() == "a" and (data_qa == "serp-item__title" or (not self._card["id"] and "/vacancy/" in attr_map.get("href", ""))):
            href = attr_map.get("href", "")
            m = re.search(r"/vacancy/(\d+)", href)
            if m:
                self._card["id"] = m.group(1)
                self._card["url"] = f"https://tashkent.hh.uz/vacancy/{m.group(1)}"
                self._cap_title = True
        elif data_qa == "vacancy-serp__vacancy-employer":
            self._cap_employer = True

    def handle_endtag(self, tag: str) -> None:
        if not self._in_card or tag.lower() in _VOID_HTML_TAGS:
            return
        if tag.lower() == "a" and self._cap_title:
            self._card["title"] = re.sub(r"\s+", " ", "".join(self._title_parts)).strip()
            self._cap_title = False
        elif self._cap_employer and tag.lower() in ("a", "span", "div"):
            self._card["company"] = re.sub(r"\s+", " ", "".join(self._emp_parts)).strip()
            self._cap_employer = False

        self._card_depth -= 1
        if self._card_depth <= 0:
            full_text = " ".join(self._text_parts).lower()
            self._card["already_applied"] = any(
                marker in full_text for marker in ("вы откликнулись", "отклик отправлен")
            )
            if self._card["id"] and self._card["title"]:
                if not self._card["company"]:
                    self._card["company"] = "HH Employer"
                self.cards.append(dict(self._card))
            self._in_card = False
            self._card_depth = 0

    def handle_data(self, data: str) -> None:
        if not self._in_card:
            return
        self._text_parts.append(data)
        if self._cap_title:
            self._title_parts.append(data)
        if self._cap_employer:
            self._emp_parts.append(data)


def extract_serp_cards_from_html(html_text: str) -> List[Dict[str, Any]]:
    """Parses HH search/category HTML into deduplicated vacancy card dictionaries."""
    parser = _HHSerpCardParser()
    parser.feed(html_text or "")
    parser.close()

    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    for card in parser.cards:
        vid = str(card.get("id", "")).strip()
        if not vid or vid in seen:
            continue
        seen.add(vid)
        unique.append(card)
    return unique


def upsert_harvested_cards(
    cards: List[Dict[str, Any]],
    db_path: Path | None = None,
    queue_path: Path | None = None,
    priority_url: Optional[str] = None,
) -> Dict[str, int]:
    """Saves harvested HH search cards into positions.db and optional priority URL queue."""
    target_db = Path(db_path) if db_path else Config.DB_PATH
    init_database(target_db)
    conn = get_connection(target_db)
    now_iso = datetime.datetime.now().isoformat()

    canon_url = normalize_target_url(priority_url) if priority_url else ""
    q_items = load_queue(queue_path=queue_path) if canon_url else {}
    inserted = 0
    synced_applied = 0
    queued = 0

    try:
        existing_apps = {
            str(row[0]) for row in conn.execute("SELECT vacancy_id FROM applications").fetchall()
        }

        for rank, card in enumerate(cards, 1):
            vid = str(card.get("id") or "").strip()
            title = str(card.get("title") or "").strip()
            company = re.sub(r"\s+", " ", str(card.get("company") or "HH Employer")).strip() or "HH Employer"
            if not vid or not title:
                continue

            clean_url = f"https://tashkent.hh.uz/vacancy/{vid}"
            existing_row = conn.execute("SELECT company FROM vacancies WHERE id = ?", (vid,)).fetchone()
            if not existing_row:
                conn.execute(
                    """
                    INSERT INTO vacancies (id, title, company, url, source, tier, sector, scraped_at, is_active)
                    VALUES (?, ?, ?, ?, 'hh.uz', ?, ?, ?, 1)
                    """,
                    (vid, title, company, clean_url, classify_tier(company), normalize_sector(title, title), now_iso),
                )
                inserted += 1
            elif company != "HH Employer" and existing_row[0] in ("", None, "HH Employer"):
                conn.execute(
                    "UPDATE vacancies SET company = ?, tier = ?, is_active = 1 WHERE id = ?",
                    (company, classify_tier(company), vid),
                )

            is_already_applied = bool(card.get("already_applied")) or (vid in existing_apps)
            if bool(card.get("already_applied")) and vid not in existing_apps:
                synced_applied += 1
                existing_apps.add(vid)

            if canon_url and not is_already_applied:
                prev = dict(q_items.get(vid, {}))
                prev_status = prev.get("status")
                if prev_status not in {"applied", "archived", "needs_human"}:
                    prev.update(
                        {
                            "vacancy_id": vid,
                            "title": title,
                            "company": company,
                            "url": clean_url,
                            "priority_url": canon_url,
                            "priority_rank": rank,
                            "status": "queued",
                            "updated_at": now_iso,
                        }
                    )
                    q_items[vid] = prev
                    queued += 1

        conn.commit()
    finally:
        conn.close()

    if synced_applied > 0:
        for card in cards:
            vid = str(card.get("id") or "").strip()
            if vid and card.get("already_applied"):
                update_application_status(
                    vacancy_id=vid,
                    status="applied",
                    notes="Synced from HH category search card ('Вы откликнулись')",
                    cover_letter_sent=0,
                    db_path=target_db,
                )

    if canon_url and queued > 0:
        save_queue(q_items, queue_path=queue_path)

    return {"inserted": inserted, "queued": queued, "synced_applied": synced_applied}


class DryRunDriver:
    """Non-mutating simulation driver used by --dry-run and dry checks."""

    def prepare(self) -> None:
        return None

    def apply(
        self,
        item: Dict[str, Any],
        confirm_mode: str = "none",
        on_questions: str = "defer",
        prompt_fn: Optional[Callable[[str], str]] = None,
    ) -> SubmitResult:
        return SubmitResult(
            status="dry_run",
            detail=f"Dry-run simulated ({confirm_mode})",
            cv_variant=item.get("cv_variant"),
            cover_letter=item.get("cover_letter"),
        )

    def close(self) -> None:
        return None


class OfficialApiDriver:
    """Official dev.hh.ru OAuth application driver (`POST /negotiations`)."""

    def __init__(self, access_token: Optional[str] = None) -> None:
        self.access_token = (access_token or os.environ.get("HH_ACCESS_TOKEN", "")).strip()
        self._resumes_cache: Optional[List[Dict[str, str]]] = None

    def prepare(self) -> None:
        if not self.access_token:
            raise RuntimeError(
                "HH_ACCESS_TOKEN is not set. Official dev.hh.ru mode requires an OAuth token."
            )

    def _headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.access_token}",
            "HH-User-Agent": f"Resume-Job-Tracker/1.0 ({Config.CANDIDATE_EMAIL})",
            "User-Agent": f"Resume-Job-Tracker/1.0 ({Config.CANDIDATE_EMAIL})",
        }
        if content_type:
            h["Content-Type"] = content_type
        return h

    def _pick_resume_id(self, cv_variant: Optional[str]) -> Optional[str]:
        if self._resumes_cache is None:
            req = urllib.request.Request("https://api.hh.ru/resumes/mine", headers=self._headers())
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._resumes_cache = data.get("items", [])
        if not self._resumes_cache:
            return None
        target_kw = {
            "financial_analyst": ("финанс", "financial", "экономист"),
            "operations_manager": ("операц", "директор", "руководит", "manager"),
            "business_analyst": ("бизнес", "аналит", "analyst"),
        }.get(cv_variant or "", ())
        for res in self._resumes_cache:
            title_l = str(res.get("title", "")).lower()
            if any(k in title_l for k in target_kw):
                return str(res.get("id"))
        return str(self._resumes_cache[0].get("id"))

    def apply(
        self,
        item: Dict[str, Any],
        confirm_mode: str = "none",
        on_questions: str = "defer",
        prompt_fn: Optional[Callable[[str], str]] = None,
    ) -> SubmitResult:
        try:
            resume_id = self._pick_resume_id(item.get("cv_variant"))
            if not resume_id:
                return SubmitResult("needs_human", "No published HH resumes returned by /resumes/mine")
            body = urllib.parse.urlencode(
                {
                    "vacancy_id": str(item["id"]),
                    "resume_id": resume_id,
                    "message": item.get("cover_letter", ""),
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                "https://api.hh.ru/negotiations",
                data=body,
                headers=self._headers("application/x-www-form-urlencoded"),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status in (200, 201, 204):
                    return SubmitResult("applied", f"Submitted via HH API (resume={resume_id})", item.get("cv_variant"))
                return SubmitResult("error", f"Unexpected HH API status: {resp.status}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")[:300]
            if e.code == 403:
                return SubmitResult(
                    "needs_human",
                    f"HH API 403 Forbidden (dev.hh.ru restricted POST /negotiations for this token): {err_body}",
                )
            if e.code == 400 and "already_applied" in err_body.lower():
                return SubmitResult("already_applied", "HH API reports already applied")
            return SubmitResult("error", f"HH API HTTP {e.code}: {err_body}")
        except Exception as e:
            return SubmitResult("error", str(e))

    def close(self) -> None:
        return None


class EdgeSeleniumDriver:
    """Visible Microsoft Edge Selenium driver using persistent hh_main_session profile."""

    def __init__(
        self,
        profile_dir: Optional[Path] = None,
        word_delay_range: Tuple[float, float] = (2.0, 3.0),
    ) -> None:
        self.profile_dir = Path(profile_dir) if profile_dir else Config.HH_SESSION_PROFILE_DIR
        self.word_delay_range = word_delay_range
        self.driver: Any = None

    def prepare(self) -> None:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options as EdgeOptions
        from selenium.webdriver.edge.service import Service as EdgeService

        print(f"[INIT] Открываю Microsoft Edge (профиль: {self.profile_dir})...", flush=True)
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        opts = EdgeOptions()
        opts.add_argument(f"--user-data-dir={self.profile_dir}")
        opts.add_argument("--window-size=1080,820")
        opts.add_argument("--window-position=360,20")
        opts.add_argument("--no-first-run")
        opts.add_argument("--no-default-browser-check")

        edge_bin = Config.get_edge_binary()
        if edge_bin:
            opts.binary_location = str(edge_bin)

        cached_driver = _find_cached_msedgedriver()
        if cached_driver:
            self.driver = webdriver.Edge(service=EdgeService(executable_path=str(cached_driver)), options=opts)
        else:
            self.driver = webdriver.Edge(options=opts)
        self.driver.set_page_load_timeout(30)

    def _safe_text(self) -> str:
        try:
            return self.driver.execute_script("return document.body ? document.body.innerText : '';") or ""
        except Exception:
            return ""

    def _has_selector(self, css: str) -> bool:
        from selenium.webdriver.common.by import By

        try:
            return len(self.driver.find_elements(By.CSS_SELECTOR, css)) > 0
        except Exception:
            return False

    def _page_flags(self) -> Dict[str, bool]:
        return {
            "apply_btn": any(
                self._has_selector(sel)
                for sel in (
                    "[data-qa='vacancy-response-link-top']",
                    "[data-qa='vacancy-response-link-bottom']",
                    "a[href*='vacancy_response']",
                )
            ),
            "already_applied": any(
                self._has_selector(sel)
                for sel in (
                    "[data-qa='vacancy-response-link-view-topic']",
                    "[data-qa='vacancy-response-link-top-applied']",
                )
            ),
            "auth_form": self._has_selector("[data-qa='auth-form']") or self._has_selector("[data-qa='account-signup-submit']"),
            "login_btn": self._has_selector("a[data-qa~='login'], button[data-qa~='login'], [data-qa*='mainmenu_loginButton']"),
        }

    def _natural_scroll_and_read(self) -> str:
        from selenium.webdriver.common.by import By

        steps = random.randint(2, 4)
        for _ in range(steps):
            px = random.randint(240, 480)
            try:
                self.driver.execute_script(f"window.scrollBy({{top: {px}, behavior: 'smooth'}});")
            except Exception:
                pass
            sleep_with_jitter(random.uniform(1.0, 2.3))
        try:
            self.driver.execute_script("window.scrollTo({top: 0, behavior: 'smooth'});")
            sleep_with_jitter(random.uniform(0.8, 1.5))
        except Exception:
            pass
        try:
            el = self.driver.find_elements(By.CSS_SELECTOR, "[data-qa='vacancy-description']")
            if el:
                return el[0].text[:1500]
        except Exception:
            pass
        return self._safe_text()[:1200]

    def _click_first(self, selectors: List[str]) -> bool:
        from selenium.webdriver.common.by import By

        for sel in selectors:
            try:
                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    if el.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                        sleep_with_jitter(random.uniform(0.3, 0.7))
                        el.click()
                        return True
            except Exception:
                continue
        return False

    def _select_matching_resume(self, cv_variant: Optional[str]) -> None:
        from selenium.webdriver.common.by import By

        kw_map = {
            "financial_analyst": ("финанс", "financial", "экономист"),
            "operations_manager": ("операц", "директор", "руковод", "manager"),
            "business_analyst": ("бизнес", "аналит", "analyst"),
        }
        keywords = kw_map.get(cv_variant or "", ())
        try:
            items = self.driver.find_elements(
                By.CSS_SELECTOR,
                "[data-qa='resume-select-item'], [data-qa='vacancy-response-popup-resume-item'], label[data-qa*='resume']",
            )
            if len(items) <= 1:
                return
            for el in items:
                txt = (el.text or "").lower()
                if any(k in txt for k in keywords):
                    if el.is_displayed():
                        el.click()
                        sleep_with_jitter(0.5)
                    return
        except Exception:
            pass

    def _enter_cover_letter(self, letter: str) -> bool:
        from selenium.webdriver.common.by import By

        if not self._click_first(
            [
                "[data-qa='vacancy-response-letter-toggle']",
                "button[data-qa*='letter-toggle']",
            ]
        ):
            try:
                for btn in self.driver.find_elements(By.CSS_SELECTOR, "button, a"):
                    if btn.is_displayed() and "сопроводительн" in (btn.text or "").lower():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        btn.click()
                        break
            except Exception:
                pass
        sleep_with_jitter(random.uniform(0.6, 1.2))

        for sel in (
            "[data-qa='vacancy-response-popup-form-letter-input']",
            "textarea[data-qa='vacancy-response-letter-text']",
            "textarea[name='letter']",
            "[role='dialog'] textarea",
            "textarea",
        ):
            try:
                boxes = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for box in boxes:
                    if box.is_displayed():
                        box.click()
                        sleep_with_jitter(0.3)
                        box.clear()
                        # Type in human-paced word simulation (2-3 sec per word)
                        type_human_paced_text(box, letter, word_delay_range=self.word_delay_range)
                        return True
            except Exception:
                continue
        return False

    def _extract_live_serp_cards(self) -> List[Dict[str, Any]]:
        try:
            cards = self.driver.execute_script(
                """
                const out = [];
                const nodes = document.querySelectorAll("[data-qa='vacancy-serp__vacancy']");
                nodes.forEach(card => {
                    const titleEl = card.querySelector("a[data-qa='serp-item__title']");
                    if (!titleEl || !titleEl.href) return;
                    const m = titleEl.href.match(/\\/vacancy\\/(\\d+)/);
                    if (!m) return;
                    const empEl = card.querySelector("[data-qa='vacancy-serp__vacancy-employer']");
                    const txt = (card.innerText || "").toLowerCase();
                    out.push({
                        id: m[1],
                        title: (titleEl.innerText || titleEl.textContent || "").trim(),
                        company: empEl ? (empEl.innerText || empEl.textContent || "").trim() : "HH Employer",
                        url: "https://tashkent.hh.uz/vacancy/" + m[1],
                        already_applied: txt.includes("вы откликнулись") || txt.includes("отклик отправлен")
                    });
                });
                return out;
                """
            )
            if isinstance(cards, list) and cards:
                return cards
        except Exception:
            pass
        try:
            return extract_serp_cards_from_html(self.driver.page_source or "")
        except Exception:
            return []

    def harvest_url(
        self,
        start_url: str,
        max_pages: int = 25,
        limit: int = 500,
        db_path: Path | None = None,
        queue_path: Path | None = None,
    ) -> int:
        """Harvests paginated vacancies from an explicit HH category/search URL in priority order."""
        if not self.driver:
            self.prepare()

        collected: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()

        for page in range(max(1, int(max_pages))):
            page_url = build_hh_page_url(start_url, page)
            self.driver.get(page_url)
            sleep_with_jitter(random.uniform(2.0, 3.4))

            while inspect_hh_page(self.driver.current_url, self._safe_text(), self._page_flags()) == "captcha_or_login":
                _beep_alert()
                try:
                    input(
                        f"\n[!] Требуется вход в hh.uz или капча ({self.driver.current_url}).\n"
                        "    Войдите / решите в открытом окне Edge и нажмите Enter..."
                    )
                except EOFError:
                    raise KeyboardInterrupt("Paused cleanly: CAPTCHA or login required without interactive stdin")
                self.driver.get(page_url)
                sleep_with_jitter(random.uniform(2.0, 3.0))

            page_cards = self._extract_live_serp_cards()
            added_this_page = 0
            for card in page_cards:
                vid = str(card.get("id") or "")
                if not vid or vid in seen_ids:
                    continue
                seen_ids.add(vid)
                collected.append(card)
                added_this_page += 1
                if len(collected) >= limit:
                    break

            print(f"    [HARVEST] Стр. {page + 1}: +{added_this_page} (всего {len(collected)})", flush=True)
            if added_this_page == 0 or len(collected) >= limit:
                break

        res = upsert_harvested_cards(
            collected,
            db_path=db_path,
            queue_path=queue_path,
            priority_url=start_url,
        )
        return res["queued"] + res["inserted"]

    def harvest_vacancies(self, queries: List[str], limit_per_query: int = 15, db_path: Path | None = None) -> int:
        """Harvests fresh vacancies via visible logged-in Edge search pages."""
        from selenium.webdriver.common.by import By

        if not self.driver:
            self.prepare()
        target_db = Path(db_path) if db_path else Config.DB_PATH
        init_database(target_db)
        conn = get_connection(target_db)
        now_iso = datetime.datetime.now().isoformat()
        inserted = 0

        for q in queries:
            url = f"https://tashkent.hh.uz/search/vacancy?{urllib.parse.urlencode({'text': q, 'area': 2759, 'order_by': 'publication_time'})}"
            self.driver.get(url)
            sleep_with_jitter(random.uniform(2.5, 4.0))
            state = inspect_hh_page(self.driver.current_url, self._safe_text(), self._page_flags())
            if state == "captcha_or_login":
                _beep_alert()
                input("\n[!] Капча или вход на странице поиска HH. Решите в Edge и нажмите Enter...")
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[data-qa='serp-item__title']")[:limit_per_query]
            for a in links:
                href = a.get_attribute("href") or ""
                title = (a.text or "").strip()
                m = re.search(r"/vacancy/(\d+)", href)
                if not m or not title:
                    continue
                vid = m.group(1)
                if not conn.execute("SELECT 1 FROM vacancies WHERE id = ?", (vid,)).fetchone():
                    clean_url = f"https://tashkent.hh.uz/vacancy/{vid}"
                    conn.execute(
                        """
                        INSERT INTO vacancies (id, title, company, url, source, tier, sector, scraped_at, is_active)
                        VALUES (?, ?, 'HH Employer', ?, 'hh.uz', 2, ?, ?, 1)
                        """,
                        (vid, title, clean_url, normalize_sector(title, title), now_iso),
                    )
                    inserted += 1
        conn.commit()
        conn.close()
        return inserted

    def apply(
        self,
        item: Dict[str, Any],
        confirm_mode: str = "none",
        on_questions: str = "defer",
        prompt_fn: Optional[Callable[[str], str]] = None,
    ) -> SubmitResult:
        if not self.driver:
            self.prepare()

        ask = prompt_fn or input
        url = str(item.get("url", "")).strip()
        if not url:
            return SubmitResult("error", "Vacancy URL is missing")

        try:
            self.driver.get(url)
        except Exception as e:
            return SubmitResult("error", f"Navigation failed: {e}")

        sleep_with_jitter(random.uniform(2.5, 4.2))
        state = inspect_hh_page(self.driver.current_url, self._safe_text(), self._page_flags())

        if state == "captcha_or_login":
            return SubmitResult("captcha_paused", f"Challenge or login required at {self.driver.current_url}")
        if state == "archived":
            return SubmitResult("archived", "Vacancy is archived or closed on HH")
        if state == "already_applied":
            return SubmitResult("already_applied", "Already applied according to HH page", item.get("cv_variant"))

        desc = self._natural_scroll_and_read()
        letter = item.get("cover_letter") or ""
        if (not letter) or (desc and not item.get("description_refined") and item.get("llm_backend", "none") != "none"):
            refined = generate_cover_letter(
                item,
                backend=item.get("llm_backend", "ollama"),
                description=desc,
                cv_variant=item.get("cv_variant"),
            )
            letter = refined["text"]

        clicked = self._click_first(
            [
                "[data-qa='vacancy-response-link-top']",
                "[data-qa='vacancy-response-link-bottom']",
                "a[href*='vacancy_response']",
            ]
        )
        if not clicked:
            restate = inspect_hh_page(self.driver.current_url, self._safe_text(), self._page_flags())
            if restate == "already_applied":
                return SubmitResult("already_applied", "Already applied badge visible", item.get("cv_variant"))
            return SubmitResult("needs_human", "Could not locate active 'Откликнуться' button")

        sleep_with_jitter(random.uniform(1.8, 3.2))
        if self._click_first(["[data-qa='relocation-warning-confirm']"]):
            sleep_with_jitter(random.uniform(1.0, 1.8))

        post_click_state = inspect_hh_page(self.driver.current_url, self._safe_text(), self._page_flags())
        if post_click_state == "captcha_or_login":
            return SubmitResult("captcha_paused", f"Challenge or login triggered after clicking Apply at {self.driver.current_url}")

        page_txt_l = self._safe_text().lower()
        has_questions = self._has_selector("[data-qa='vacancy-response-questions']") or any(
            q in page_txt_l for q in ("ответьте на вопросы", "обязательные вопросы", "пройдите тест работодателя")
        )
        if has_questions:
            if on_questions == "pause":
                _beep_alert()
                ans = ask(
                    f"\n[?] Вакансия «{item.get('title')}» требует ответов на вопросы работодателя в Edge.\n"
                    "    Заполните ответы в окне браузера и выберите: [Enter]=Отправлено | [s]=Отложить -> "
                ).strip().lower()
                if ans == "s":
                    return SubmitResult("needs_human", "Employer questions deferred by user")
                return SubmitResult("applied", "Completed manually after employer questions pause", item.get("cv_variant"), letter)
            return SubmitResult("needs_human", "Mandatory employer screening questions/test", cover_letter=letter)

        self._select_matching_resume(item.get("cv_variant"))
        letter_entered = self._enter_cover_letter(letter) if letter else False

        if confirm_mode == "each":
            _beep_alert()
            print("\n" + "=" * 68)
            print(f"[ПОДТВЕРЖДЕНИЕ] {item.get('company')} — {item.get('title')}")
            print("-" * 68)
            print(letter)
            print("=" * 68)
            choice = ask("  [Enter]=Откликнуться | [1]=Вернуться в авто-режим | [s]=Пропустить | [q]=Стоп: ").strip().lower()
            if choice == "q":
                raise KeyboardInterrupt("Stopped by user at confirm=each")
            if choice == "s":
                return SubmitResult("skipped", "Skipped by user in confirm=each")
            if choice == "1":
                item["_switch_confirm"] = "none"

        submitted = self._click_first(
            [
                "[data-qa='vacancy-response-submit-popup']",
                "[data-qa='vacancy-response-submit']",
                "[data-qa='vacancy-response-letter-submit']",
                "button[type='submit'][data-qa*='response']",
                "form button[data-qa*='letter']",
                "[role='dialog'] button[type='submit']",
            ]
        )
        sleep_with_jitter(random.uniform(2.5, 4.0))

        cur_text_l = self._safe_text().lower()
        after_flags = self._page_flags()
        after_state = inspect_hh_page(self.driver.current_url, cur_text_l, after_flags)

        if after_state == "captcha_or_login" or any(
            k in cur_text_l
            for k in (
                "пройдите капчу",
                "текст с картинки",
                "введите текст с картинки",
                "подтвердите, что вы не робот",
                "smartcaptcha",
            )
        ):
            return SubmitResult("captcha_paused", "Challenge or image CAPTCHA triggered after submit click")

        # Explicitly verify success confirmation from HH
        confirmed_applied = (
            after_state == "already_applied"
            or after_flags.get("already_applied")
            or any(
                w in cur_text_l
                for w in (
                    "вы откликнулись",
                    "отклик отправлен",
                    "резюме отправлено",
                    "вакансия перемещена в список ваших откликов",
                )
            )
            or self._has_selector("[data-qa='vacancy-response-link-view-topic']")
            or self._has_selector("[data-qa='vacancy-response-link-top-applied']")
        )

        if not confirmed_applied:
            from selenium.webdriver.common.by import By
            modal_text = ""
            try:
                for m in self.driver.find_elements(By.CSS_SELECTOR, "[role='dialog'], .bloko-modal"):
                    if m.is_displayed():
                        modal_text = m.text
                        break
            except Exception:
                pass
            if modal_text:
                if any(k in modal_text.lower() for k in ("капч", "робот", "картинк")):
                    return SubmitResult("captcha_paused", f"CAPTCHA detected in modal: {modal_text[:120]}")
                if "видимость резюме" in modal_text.lower():
                    return SubmitResult("needs_human", f"Resume visibility restriction: {modal_text[:140]}")
                return SubmitResult("needs_human", f"Modal remained unsubmitted: {modal_text[:120]}")
            return SubmitResult("needs_human", "Submission not confirmed by HH after clicking apply")

        note = "Submitted via visible Edge with cover letter" if letter_entered else "Submitted via visible Edge"
        return SubmitResult("applied", note, item.get("cv_variant"), letter if letter_entered else "")

    def close(self) -> None:
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None


class AssistDriver:
    """Semi-manual driver: opens Edge and copies tailored cover letter to clipboard."""

    def __init__(
        self,
        profile_dir: Optional[Path] = None,
        word_delay_range: Tuple[float, float] = (2.0, 3.0),
    ) -> None:
        self.edge = EdgeSeleniumDriver(profile_dir=profile_dir, word_delay_range=word_delay_range)

    def prepare(self) -> None:
        self.edge.prepare()

    def apply(
        self,
        item: Dict[str, Any],
        confirm_mode: str = "each",
        on_questions: str = "pause",
        prompt_fn: Optional[Callable[[str], str]] = None,
    ) -> SubmitResult:
        ask = prompt_fn or input
        letter = item.get("cover_letter", "")
        _copy_to_clipboard(letter)
        self.edge.driver.get(item["url"])
        _beep_alert()
        print("\n" + "=" * 68)
        print(f"[ASSIST] {item.get('company')} — {item.get('title')}")
        print("Письмо скопировано в буфер обмена:")
        print("-" * 68)
        print(letter)
        print("=" * 68)
        ans = ask("Нажмите в браузере «Откликнуться» и выберите: [Enter]=Отправлено | [s]=Пропустить | [q]=Стоп: ").strip().lower()
        if ans == "q":
            raise KeyboardInterrupt("Stopped by user in assist mode")
        if ans == "s":
            return SubmitResult("skipped", "Skipped in assist mode")
        return SubmitResult("applied", "Completed manually in assist mode", item.get("cv_variant"), letter)

    def close(self) -> None:
        self.edge.close()


def _mark_vacancy_inactive(db_path: Path, vacancy_id: str) -> None:
    conn = get_connection(db_path)
    conn.execute("UPDATE vacancies SET is_active = 0 WHERE id = ?", (vacancy_id,))
    conn.commit()
    conn.close()


def _create_driver(
    mode: str,
    dry_run: bool,
    profile_dir: Optional[Path],
    word_delay_range: Tuple[float, float] = (2.0, 3.0),
) -> Any:
    if dry_run:
        return DryRunDriver()
    if mode == "browser":
        return EdgeSeleniumDriver(profile_dir=profile_dir, word_delay_range=word_delay_range)
    if mode == "api":
        return OfficialApiDriver()
    if mode == "assist":
        return AssistDriver(profile_dir=profile_dir, word_delay_range=word_delay_range)
    raise ValueError(f"Unsupported mode: {mode}")


def run_apply_session(
    *,
    driver: Optional[Any] = None,
    mode: str = "browser",
    confirm_mode: str = "none",
    on_questions: str = "defer",
    limit: int = 200,
    daily_limit: int = 200,
    wave_size: int = 25,
    wave_pause_sec: int = 120,
    min_delay: float = 5.0,
    max_delay: float = 12.0,
    word_delay_min: float = 2.0,
    word_delay_max: float = 3.0,
    min_score: int = 55,
    backend: str = "ollama",
    dry_run: bool = False,
    db_path: Path | None = None,
    queue_path: Path | None = None,
    state_path: Path | None = None,
    profile_dir: Path | None = None,
    harvest_queries: Optional[List[str]] = None,
    start_url: Optional[str] = None,
    harvest_max_pages: int = 25,
    target_min_score: int = 0,
    target_only: bool = False,
    prompt_fn: Optional[Callable[[str], str]] = None,
    refresh_dash: bool = True,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Executes one complete visible/autonomous HeadHunter application session."""
    def _say(msg: str) -> None:
        if verbose:
            print(msg, flush=True)
    target_db = Path(db_path) if db_path else Config.DB_PATH
    q_path = Path(queue_path) if queue_path else Config.HH_QUEUE_FILE
    s_path = Path(state_path) if state_path else Config.HH_STATE_FILE
    init_database(target_db)

    ask = prompt_fn or input
    active_driver = driver or _create_driver(mode, dry_run, profile_dir, word_delay_range=(word_delay_min, word_delay_max))
    active_confirm = confirm_mode

    stats = {
        "success": True,
        "code": Config.EXIT_SUCCESS,
        "mode": mode,
        "confirm_mode": active_confirm,
        "dry_run": dry_run,
        "applied": 0,
        "already_applied": 0,
        "archived": 0,
        "needs_human": 0,
        "skipped": 0,
        "simulated": 0,
        "errors": 0,
        "harvested": 0,
        "results": [],
    }

    try:
        active_driver.prepare()

        if start_url and hasattr(active_driver, "harvest_url") and not dry_run:
            _say(f"\n[HARVEST] Собираю вакансии по ссылке: {start_url}")
            stats["harvested"] += active_driver.harvest_url(
                start_url,
                max_pages=harvest_max_pages,
                db_path=target_db,
                queue_path=q_path,
            )

        if harvest_queries and hasattr(active_driver, "harvest_vacancies") and not dry_run:
            stats["harvested"] += active_driver.harvest_vacancies(harvest_queries, db_path=target_db)

        rem = remaining_daily_quota(daily_limit=daily_limit, state_path=s_path)
        effective_limit = min(limit, rem) if not dry_run else limit
        if effective_limit <= 0:
            stats["code"] = Config.EXIT_NO_DATA
            stats["detail"] = f"Daily cap reached ({daily_limit}/{daily_limit})."
            return stats

        candidates = select_candidate_vacancies(
            db_path=target_db,
            limit=effective_limit * 2,
            min_score=min_score,
            queue_path=q_path,
            target_url=start_url,
            target_min_score=target_min_score,
            target_only=target_only,
        )[:effective_limit]

        if not candidates:
            stats["code"] = Config.EXIT_NO_DATA
            stats["detail"] = "No eligible unapplied hh.uz vacancies found above min_score."
            return stats

        if active_confirm == "batch" and not dry_run:
            print("\n=== Превью отобранной пачки ===")
            for idx, c in enumerate(candidates, 1):
                tag = "[TARGET] " if c.get("is_target_url") else ""
                print(f"  {idx:2d}. {tag}[Score {c['score']} | T{c['tier']}] {c['company']} — {c['title']}")
            ans = ask(f"\nЗапустить видимую подачу по {len(candidates)} вакансиям? [Enter=Да / q=Отмена]: ").strip().lower()
            if ans == "q":
                stats["code"] = Config.EXIT_NO_DATA
                stats["detail"] = "Cancelled by user at batch preview"
                return stats
            active_confirm = "none"
            stats["confirm_mode"] = active_confirm

        profile = load_candidate_profile()
        processed_in_wave = 0

        for idx, vac in enumerate(candidates, 1):
            if not dry_run and remaining_daily_quota(daily_limit=daily_limit, state_path=s_path) <= 0:
                _say(f"\n[STOP] Достигнут суточный лимит {daily_limit} откликов.")
                break

            eff_min = int(vac.get("effective_min_score", target_min_score if vac.get("is_target_url") else min_score))
            eff_excludes = bool(vac.get("respect_excludes", not (vac.get("is_target_url") and target_min_score <= 0)))
            scoring = score_vacancy(
                vac,
                profile=profile,
                use_llm=(backend != "none" and not vac.get("queued_letter")),
                backend=backend,
                min_score=eff_min,
                respect_excludes=eff_excludes,
            )
            if not scoring["fit"]:
                upsert_queue_item(
                    {
                        "vacancy_id": vac["id"],
                        "title": vac["title"],
                        "company": vac["company"],
                        "url": vac["url"],
                        "score": scoring["score"],
                        "status": "skipped",
                        "detail": scoring["reason"],
                    },
                    queue_path=q_path,
                )
                stats["skipped"] += 1
                continue

            if vac.get("queued_letter"):
                letter_text = vac["queued_letter"]
                variant = scoring["cv_variant"]
            elif isinstance(active_driver, EdgeSeleniumDriver) and not dry_run:
                # EdgeSeleniumDriver reads live HH description on page first, avoiding duplicate Ollama call
                letter_text = ""
                variant = scoring["cv_variant"]
            else:
                letter_info = generate_cover_letter(
                    vac, profile=profile, backend=backend, cv_variant=scoring["cv_variant"]
                )
                letter_text = letter_info["text"]
                variant = letter_info["cv_variant"]

            item = dict(vac)
            item["cover_letter"] = letter_text
            item["cv_variant"] = variant
            item["llm_backend"] = backend
            item["score"] = scoring["score"]

            ts = datetime.datetime.now().strftime("%H:%M:%S")
            _say(f"\n[{ts}] [{idx}/{len(candidates)}] Score={item['score']} | T{item['tier']} | {item['company']} — {item['title']}")

            while True:
                res = active_driver.apply(
                    item,
                    confirm_mode=active_confirm,
                    on_questions=on_questions,
                    prompt_fn=ask,
                )
                if item.pop("_switch_confirm", None) == "none":
                    active_confirm = "none"
                    stats["confirm_mode"] = active_confirm

                if res.status == "captcha_paused":
                    _beep_alert()
                    _say(f"\n[!] ПАУЗА: {res.detail}")
                    try:
                        action = ask(
                            "    Решите капчу/войдите в открытом окне Edge и выберите:\n"
                            "    [Enter] Продолжить текущий режим\n"
                            "    [2]     Переключиться в Вариант 2 (подтверждать каждый отклик вручную)\n"
                            "    [s]     Отложить эту вакансию и пойти дальше\n"
                            "    [q]     Сохранить прогресс и выйти\n"
                            "    Ваш выбор: "
                        ).strip().lower()
                    except EOFError:
                        _say("\n[STOP] Неинтерактивный режим: сохраняю прогресс и выхожу на паузе CAPTCHA.")
                        action = "q"
                    if action == "2":
                        active_confirm = "each"
                        stats["confirm_mode"] = active_confirm
                        _say("    -> Режим переключен на Вариант 2 (--confirm each).")
                        continue
                    if action == "s":
                        res = SubmitResult("needs_human", "Deferred at CAPTCHA pause", variant, letter_text)
                        break
                    if action == "q":
                        stats["detail"] = "Stopped cleanly by user at challenge pause"
                        return stats
                    continue
                break

            stats["results"].append(
                {
                    "vacancy_id": item["id"],
                    "title": item["title"],
                    "company": item["company"],
                    "score": item["score"],
                    "status": res.status,
                    "detail": res.detail,
                }
            )

            if res.status == "dry_run":
                stats["simulated"] += 1
                _say(f"    -> [DRY-RUN] Вариант={variant} | Письмо={len(letter_text)} симв.")
                continue

            if res.status == "applied":
                stats["applied"] += 1
                processed_in_wave += 1
                letter_sent_flag = 1 if (res.cover_letter or letter_text) else 0
                update_application_status(
                    vacancy_id=item["id"],
                    status="applied",
                    notes=f"Auto-applied ({mode}/{active_confirm}): {res.detail}",
                    cv_variant=res.cv_variant or variant,
                    cover_letter_sent=letter_sent_flag,
                    db_path=target_db,
                )
                upsert_queue_item(
                    {
                        "vacancy_id": item["id"],
                        "title": item["title"],
                        "company": item["company"],
                        "url": item["url"],
                        "cv_variant": res.cv_variant or variant,
                        "cover_letter": res.cover_letter or letter_text,
                        "status": "applied",
                        "detail": res.detail,
                    },
                    queue_path=q_path,
                )
                record_daily_apply(state_path=s_path, count=1, mode=f"{mode}:{active_confirm}")
                st_now = load_autonomy_state(state_path=s_path)
                _say(f"    -> [OK] Отклик отправлен! Сегодня: {st_now['applied_today']}/{daily_limit}")

                if idx < len(candidates):
                    if wave_size > 0 and processed_in_wave >= wave_size and wave_pause_sec > 0:
                        processed_in_wave = 0
                        _say(f"\n[ВОЛНА] Пауза между волнами: {wave_pause_sec} сек ({wave_pause_sec // 60} мин) для имитации естественных сессий...")
                        sleep_with_jitter(wave_pause_sec)
                    else:
                        delay = random.uniform(min_delay, max(min_delay, max_delay))
                        _say(f"    -> Естественная пауза перед следующей вакансией: {delay:.1f} сек...")
                        sleep_with_jitter(delay)

            elif res.status == "already_applied":
                stats["already_applied"] += 1
                update_application_status(
                    vacancy_id=item["id"],
                    status="applied",
                    notes="Synced from HH page ('Вы откликнулись')",
                    cv_variant=res.cv_variant or variant,
                    cover_letter_sent=0,
                    db_path=target_db,
                )
                upsert_queue_item(
                    {"vacancy_id": item["id"], "status": "applied", "detail": res.detail},
                    queue_path=q_path,
                )
                _say("    -> [SYNC] На HH уже был отклик — синхронизировано в positions.db.")

            elif res.status == "archived":
                stats["archived"] += 1
                _mark_vacancy_inactive(target_db, item["id"])
                upsert_queue_item(
                    {"vacancy_id": item["id"], "status": "archived", "detail": res.detail},
                    queue_path=q_path,
                )
                _say("    -> [ARCHIVED] Вакансия закрыта на HH — помечена неактивной в БД.")

            elif res.status == "needs_human":
                stats["needs_human"] += 1
                upsert_queue_item(
                    {
                        "vacancy_id": item["id"],
                        "title": item["title"],
                        "company": item["company"],
                        "url": item["url"],
                        "cover_letter": res.cover_letter or letter_text,
                        "status": "needs_human",
                        "detail": res.detail,
                    },
                    queue_path=q_path,
                )
                _say(f"    -> [NEEDS_HUMAN] {res.detail}")

            elif res.status == "skipped":
                stats["skipped"] += 1
                upsert_queue_item(
                    {"vacancy_id": item["id"], "status": "skipped", "detail": res.detail},
                    queue_path=q_path,
                )
                _say(f"    -> [SKIPPED] {res.detail}")
            else:
                stats["errors"] += 1
                _say(f"    -> [WARN] {res.detail}")

    except KeyboardInterrupt:
        stats["detail"] = "Interrupted cleanly by user"
        _say("\n[STOP] Остановлено пользователем. Прогресс и база сохранены.")
    finally:
        active_driver.close()
        if refresh_dash and not dry_run and (stats["applied"] > 0 or stats["already_applied"] > 0 or stats["archived"] > 0):
            try:
                build_dashboard_artifacts(db_path=target_db)
            except Exception as e:
                log_event("DASHBOARD_REFRESH_WARN", {"error": str(e)}, level="WARNING")
        log_event("HH_APPLY_SESSION", {k: v for k, v in stats.items() if k != "results"})

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Run visible Hermes + Ollama HeadHunter application pipeline")
    parser.add_argument("--mode", choices=("browser", "api", "assist"), default="browser", help="Submission driver")
    parser.add_argument("--confirm", choices=("none", "batch", "each"), default="none", help="Confirmation policy")
    parser.add_argument("--on-questions", choices=("defer", "pause"), default="defer", help="Action on employer questionnaire")
    parser.add_argument("--limit", type=int, default=200, help="Max vacancies to process in this run")
    parser.add_argument("--daily-limit", type=int, default=200, help="Daily application cap (max HH limit is 200)")
    parser.add_argument("--wave-size", type=int, default=25, help="Applications per wave before wave break")
    parser.add_argument("--wave-pause", type=int, default=120, help="Break seconds between waves")
    parser.add_argument("--min-delay", type=float, default=5.0, help="Min seconds between applications")
    parser.add_argument("--max-delay", type=float, default=12.0, help="Max seconds between applications")
    parser.add_argument("--word-delay-min", type=float, default=2.0, help="Min seconds to spend typing each word")
    parser.add_argument("--word-delay-max", type=float, default=3.0, help="Max seconds to spend typing each word")
    parser.add_argument("--min-score", type=int, default=55, help="Minimum role-fit score (0-100)")
    parser.add_argument("--backend", choices=("ollama", "hermes", "none"), default="ollama", help="LLM cover letter backend")
    parser.add_argument("--start-url", type=str, default="", help="Paginated HH category/search URL to harvest and apply first")
    parser.add_argument("--harvest-max-pages", type=int, default=25, help="Max search pages to harvest from --start-url")
    parser.add_argument("--target-min-score", type=int, default=0, help="Min role-fit score for explicit --start-url items (0 = all)")
    parser.add_argument("--target-only", action="store_true", help="Stop after completing --start-url items without general DB fallback")
    parser.add_argument("--harvest-queries", type=str, default="", help="Comma-separated queries to refresh via Edge search")
    parser.add_argument("--profile-dir", type=str, default=None, help="Custom Edge user-data-dir")
    parser.add_argument("--db-path", type=str, default=None, help="Custom SQLite DB path")
    parser.add_argument("--queue-path", type=str, default=None, help="Custom queue JSON path")
    parser.add_argument("--state-path", type=str, default=None, help="Custom daily state JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Simulate scoring and cover letters without submitting")
    parser.add_argument("--json", action="store_true", help="Output summary as JSON")
    args = parser.parse_args()

    queries = [q.strip() for q in args.harvest_queries.split(",") if q.strip()] or None
    summary = run_apply_session(
        mode=args.mode,
        confirm_mode=args.confirm,
        on_questions=args.on_questions,
        limit=args.limit,
        daily_limit=args.daily_limit,
        wave_size=args.wave_size,
        wave_pause_sec=args.wave_pause,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        word_delay_min=args.word_delay_min,
        word_delay_max=args.word_delay_max,
        min_score=args.min_score,
        backend=args.backend,
        dry_run=args.dry_run,
        db_path=Path(args.db_path) if args.db_path else None,
        queue_path=Path(args.queue_path) if args.queue_path else None,
        state_path=Path(args.state_path) if args.state_path else None,
        profile_dir=Path(args.profile_dir) if args.profile_dir else None,
        harvest_queries=queries,
        start_url=args.start_url.strip() or None,
        harvest_max_pages=args.harvest_max_pages,
        target_min_score=args.target_min_score,
        target_only=args.target_only,
        verbose=not args.json,
    )

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"\n[SUMMARY] mode={summary['mode']}/{summary['confirm_mode']} | "
            f"applied={summary['applied']} | synced={summary['already_applied']} | "
            f"archived={summary['archived']} | needs_human={summary['needs_human']} | "
            f"simulated={summary['simulated']} | errors={summary['errors']}"
        )
    return int(summary.get("code", Config.EXIT_SUCCESS))


if __name__ == "__main__":
    sys.exit(main())
