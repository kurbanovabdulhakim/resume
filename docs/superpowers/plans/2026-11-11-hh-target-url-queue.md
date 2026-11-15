---
title: TDD Plan — Targeted HH Category URL Queue & Paginated Harvester
date: 2026-11-11
spec: docs/superpowers/specs/2026-11-11-hh-target-url-queue-design.md
---

# Implementation Plan (Red-Green TDD)

## Task 1: `hh_ai.py` — `\bfinance\b` Matching & `respect_excludes`
- **Tests (`tests/test_hh_ai.py`):**
  - Assert `"Finance Specialist (строительство)"` (`tier=2`, `"OOO UET CONSTRUCTION"`) classifies as `financial_analyst` with `fit=True` at `min_score=55`.
  - Assert `score_vacancy(..., respect_excludes=False, min_score=0)` returns `fit=True` while preserving `cv_variant` and numeric `score`.
- **Implementation (`scripts/hh_ai.py`):**
  - Add `r"\bfinance\b"` to `FINANCE_PATTERNS`.
  - Add `respect_excludes: bool = True` parameter to `score_vacancy`.

## Task 2: `hh_queue.py` — `normalize_target_url` & Priority Ordering
- **Tests (`tests/test_hh_queue.py`):**
  - Assert `normalize_target_url` preserves base filters while removing `page`.
  - Seed DB with mixed high-score general DB rows and lower-score `target_url` rows (`priority_url` + `priority_rank`). Assert `target_url` rows sort strictly first in `priority_rank` order (`1, 2, ...`), include all open items at `target_min_score=0`, exclude already-applied DB rows, and `target_only=True` omits non-target rows.
- **Implementation (`scripts/hh_queue.py`):**
  - Implement `normalize_target_url` and extend `select_candidate_vacancies`.

## Task 3: `hh_apply.py` & `launch_hh_visible.ps1` — Paginated URL Harvester & Session Integration
- **Tests (`tests/test_hh_apply.py`):**
  - Parse multi-card HH SERP HTML fixture containing `Finance Specialist (строительство)` (`OOO UET CONSTRUCTION`) and `Финансовый менеджер`, verifying real `company` extraction and URL deduplication.
  - Test `run_apply_session(..., start_url=..., harvest_max_pages=2, target_min_score=0)` with a mock driver implementing `harvest_url(...)` to assert URL harvesting executes before selection, prioritizes the harvested items before non-target DB rows, and falls back to non-target DB rows after exhausting target items.
- **Implementation (`scripts/hh_apply.py`, `scripts/launch_hh_visible.ps1`, `scripts/README.md`):**
  - Implement `extract_serp_cards_from_html`, `_set_url_page`, `EdgeSeleniumDriver.harvest_url`, relocation dialog click + cover-letter toggle fallback in `apply`, and CLI/PowerShell `-StartUrl` flags.
- **Verification:**
  - `python -m unittest discover tests -v`
  - CLI `--help` + `--dry-run --json` smoke check
  - Live visible Edge foreground launch targeting `https://tashkent.hh.uz/vacancies/finansovyy_analitik`
