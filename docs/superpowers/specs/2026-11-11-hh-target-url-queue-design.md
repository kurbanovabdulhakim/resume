---
title: Targeted HH Category URL Queue & Paginated Harvester Design Addendum
date: 2026-11-11
status: approved
scope: scripts/hh_ai.py, scripts/hh_queue.py, scripts/hh_apply.py, scripts/launch_hh_visible.ps1
---

# Design Addendum: Targeted Category URL Priority Queue (`finansovyy_analitik`)

## Context & Approved Requirements
- **Browser Session:** Continue using the isolated visible Microsoft Edge window (`hh_main_session` via `msedgedriver`), prompting once for manual HH login if not yet authenticated, keeping the user's personal Vivaldi tabs untouched.
- **Target Batch First:** Start strictly with all open unapplied vacancies harvested from `https://tashkent.hh.uz/vacancies/finansovyy_analitik` (currently ~320 vacancies across search pages), applying to every open unapplied vacancy from this URL (`min_score = 0`, bypassing generic exclude keywords only for explicit URL items) with an individualized Ollama cover letter matched to each vacancy's description, then transitioning seamlessly to remaining unapplied roles in `db/positions.db` (`min_score = 55`).
- **Daily Throughput:** Honor HH's 200 applications/day cap (`--daily-limit 200`) across waves (`--wave-size 25`, `--wave-pause 600`) so the ~320 batch spans day 1 (up to 200) and resumes automatically for the remaining ~120 on the next session before moving to other DB roles.

## Component Design

### 1. Role Scoring & Variant Matching (`scripts/hh_ai.py`)
- Add `r"\bfinance\b"` to `FINANCE_PATTERNS` so English titles such as `"Finance Specialist (строительство)"` resolve cleanly to `cv_variant = "financial_analyst"` and receive accurate role-fit scores.
- Add `respect_excludes: bool = True` to `score_vacancy(...)`. When `respect_excludes=False` (used only for an explicit user-supplied `--start-url` batch), role variant selection (`cv_variant`), keyword extraction, and numeric `score` still compute normally for cover-letter tailoring, without rejecting the vacancy.

### 2. Priority URL Metadata & Selection (`scripts/hh_queue.py`)
- Normalize target category URLs via `normalize_target_url(url)` (strips `page` query param while preserving category path/filters).
- Add `tag_target_url_vacancies(items, target_url, queue_path=...)` or tag directly during URL harvest in `hh_autonomy_queue.json` using `"priority_url"` and 1-based `"priority_rank"` without mutating `db/schema.sql`.
- Extend `select_candidate_vacancies(...)` with:
  - `target_url: Optional[str] = None`
  - `target_min_score: int = 0`
  - `target_only: bool = False`
  - Ordering rule:
    1. Items matching `priority_url == normalize_target_url(target_url)` sort strictly first, ordered by `priority_rank ASC`.
    2. General `db/positions.db` items follow only when `not target_only`, filtered by `min_score` (default `55`) and sorted by `(-score, tier)`.
  - Status safety: vacancies already in `applications` (`applied`, `interview`, etc.) or queued as `applied` / `archived` are never re-queued. Previously `skipped` queue items re-enter if claimed by an explicit `--start-url` (`target_min_score=0`).

### 3. Paginated Category Harvester & Submit Robustness (`scripts/hh_apply.py`, `scripts/launch_hh_visible.ps1`)
- Add pure HTML/card extraction helper `extract_serp_cards_from_html(html)` alongside live Selenium card harvesting `harvest_url(start_url, max_pages=25, limit=500, db_path=..., queue_path=...)`:
  - Opens `start_url` in visible Edge; if logged out / CAPTCHA, beeps and pauses cleanly for manual login/solve before scraping pages (`?page=0`, `?page=1`, ...).
  - Extracts `vacancy_id`, `title`, real `company` (`[data-qa='vacancy-serp__vacancy-employer']`), clean `https://tashkent.hh.uz/vacancy/<id>` URL, `tier`, `sector`, and card badge `"Вы откликнулись"` (syncing pre-existing applications straight into `db/positions.db` if needed!).
  - Stops cleanly when a page returns zero new vacancy links, reaches total limit, or hits the final HH pagination page.
- Enhance `EdgeSeleniumDriver.apply(...)` cover-letter modal handling:
  - Handle relocation warning popup (`[data-qa='relocation-warning-confirm']`) if shown.
  - Detect `"Добавить сопроводительное"` toggle even when text-matched fallback is needed, track whether the cover letter textarea was actually populated (`letter_attached`), and handle inline post-submit letter submission (`[data-qa='vacancy-response-letter-submit']` / form submit).
- Wire `--start-url`, `--target-min-score`, `--target-max-pages`, `--target-only` in `hh_apply.py` and `-StartUrl`, `-TargetMinScore` in `scripts/launch_hh_visible.ps1`.
