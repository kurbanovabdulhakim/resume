---
title: AI-First Job Tracker and Document Generator Implementation Plan
description: Comprehensive implementation plan to build the resume repository as an autonomous, AI-first hub for job application tracking and tailored document generation.
status: active
category: runbook
tags: [ai-first, job-tracker, resume, hermes, automation, sqlite, implementation-plan]
last-verified: 2026-11-08
summary-ru: Пошаговый план реализации репозитория resume по стандарту AI-First для автономной обработки вакансий, откликов и документов.
summary-uz: Vakansiyalar, arizalar va hujjatlarni avtonom tarzda boshqarish uchun resume repozitoriyasini AI-First standartida yaratish bo'yicha bosqichma-bosqich reja.
related:
  - docs/superpowers/specs/2026-11-07-job-tracker-design.md
  - .agents/rules/ai-first-draft.md
  - .agents/rules/doc-standarts-draft.md
  - .agents/rules/ponytail.md
  - AGENTS.md
---

# AI-First Job Tracker & Document Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `resume` repository as a fully functional, self-healing, AI-first job search hub with SQLite position tracking (`db/positions.db`), Hermes 2.0 integration (`sync_hermes.py`), automated cover letter and CV generation (`generate_docs.py`), pipeline visualization (`dashboard.py`), and machine-readable context files (`AGENTS.md`, `AI_CONTEXT.md`).

**Architecture:** A lightweight, stdlib-first Python architecture centered around an SQLite database (`db/positions.db`) acting as the Single Source of Truth (SSOT). Independent, idempotent CLI scripts with structured JSON output and `--help` interfaces allow any AI agent or human operator to query pipeline state, sync Hermes batches, update interview stages, and generate tailored documents without conversational state. Visual reporting is compiled into a standalone HTML Kanban board and Markdown summaries (`dashboard.html`, `PIPELINE.md`, `AI_CONTEXT.md`).

**Tech Stack:** Python 3.12 (stdlib: `sqlite3`, `pathlib`, `json`, `argparse`, `re`, `datetime`, `string.Template`), Headless Microsoft Edge / ReportLab for PDF rendering, Markdown / YAML for structured templates and AI context.

## Global Constraints

- **Single Source of Truth:** `db/positions.db` is the primary database for all vacancies and applications; it is tracked in Git.
- **Artifacts Isolation:** The `generated/` directory is strictly gitignored (PDFs and temporary outputs).
- **Scope Boundary (Telegram):** Telegram channel parsing is explicitly marked as pending/deferred for a future phase (`not yet telegram channels`); no active Telegram dependency is introduced.
- **Minimalist & Stdlib First:** Adhere to `ponytail.md` — leverage standard library modules (`sqlite3`, `pathlib`, `json`, `argparse`, `re`) before third-party packages.
- **AI-Native Interface:** Every CLI tool must support `--help`, structured JSON output mode (`--json`), and standard exit codes (`0` = success, `1` = error, `2` = no data / skipped).
- **No Magic Paths:** All filesystem paths are resolved relative to repository root via `scripts/config.py`.
- **Zero-Stale-Docs & Frontmatter:** Every created or updated `.md` file must strictly adhere to `.agents/rules/doc-standarts-draft.md` with full YAML frontmatter.
- **Verification Gates:** Every task must feature an automated verification test using Python `unittest` prior to completion.

---

## File Structure Map

```
resume/
├── .agents/
│   └── rules/
│       ├── ai-first-draft.md          # Existing AI governance rules
│       ├── doc-standarts-draft.md     # Existing documentation rules
│       └── ponytail.md                # Existing minimalist senior dev rules
├── .gitignore                         # Ignores generated/, tracks db/positions.db
├── AGENTS.md                          # Root AI-first operations guide and index
├── AI_CONTEXT.md                      # Machine-readable current pipeline state (auto-generated)
├── PIPELINE.md                        # Human-readable pipeline summary (auto-generated)
├── dashboard.html                     # Visual Kanban board (auto-generated)
├── README.md                          # Repository overview and master index
├── requirements.txt                   # Minimal pinned dependencies
├── db/
│   ├── schema.sql                     # Canonical database schema (SSOT)
│   ├── schema.md                      # Human & AI documentation of DB tables and queries
│   └── positions.db                   # SQLite database (tracked in git)
├── master/
│   ├── resume.md                      # Canonical Markdown resume source
│   ├── resume.html                    # Styled HTML printable version
│   └── resume.pdf                     # Exported master PDF
├── variants/
│   ├── business_analyst.md            # Role-tailored CV variant
│   ├── financial_analyst.md           # Role-tailored CV variant
│   └── operations_manager.md          # Role-tailored CV variant
├── cover_letters/
│   ├── _template_base.md              # Base template explaining all {{placeholders}}
│   ├── banking_finance.md             # Sector cover letter template
│   ├── logistics_aviation.md          # Sector cover letter template
│   ├── fmcg_distribution.md           # Sector cover letter template
│   └── it_analytics.md                # Sector cover letter template
├── generated/                         # Output per vacancy: <company_slug>_<id>/ (gitignored)
├── logs/                              # Structured JSONL audit logs: YYYY-MM-DD.jsonl
├── scripts/
│   ├── config.py                      # Single configuration & path resolver
│   ├── logger.py                      # JSONL structured audit logger
│   ├── init_db.py                     # Idempotent DB schema initializer
│   ├── sync_hermes.py                 # Idempotent sync from HERMES_BATCH_QUEUE.json
│   ├── add_position.py                # CLI: manual vacancy & application insertion
│   ├── update_status.py               # CLI: status progression & notes update
│   ├── generate_docs.py               # CLI: cover letter and CV generation engine
│   ├── dashboard.py                   # CLI: compiles dashboard.html, PIPELINE.md, AI_CONTEXT.md
│   ├── README.md                      # CLI manual for AI agents and human operators
│   └── portals/
│       ├── README.md                  # Portals roadmap & status (Telegram noted as future)
│       ├── hh_watcher.py              # Ingests fresh vacancies from HeadHunter
│       └── olx_scraper.py             # OLX Uzbekistan scraper stub
└── tests/
    ├── test_config.py
    ├── test_db.py
    ├── test_sync_hermes.py
    ├── test_position_crud.py
    ├── test_templates.py
    ├── test_generate_docs.py
    ├── test_dashboard.py
    ├── test_portals.py
    └── test_ai_first_pipeline.py
```

---

## Tasks

### Task 1: Core Configuration, Directory Layout & Git Hygiene

**Files:**
- Create: `resume/.gitignore`
- Create: `resume/scripts/config.py`
- Create: `resume/scripts/logger.py`
- Create: `resume/requirements.txt`
- Test: `resume/tests/test_config.py`

**Interfaces:**
- Consumes: Environment variables, filesystem paths.
- Produces: `config.Config` object (paths, exit codes, defaults), `logger.log_event()` structured logger.

- [ ] **Step 1: Write the failing test for configuration and paths**
  ```python
  # tests/test_config.py
  import unittest
  from scripts.config import Config

  class TestConfig(unittest.TestCase):
      def test_paths_exist_or_derivable(self):
          self.assertTrue(Config.PROJECT_ROOT.exists())
          self.assertEqual(Config.DB_PATH.name, "positions.db")
          self.assertEqual(Config.EXIT_SUCCESS, 0)
          self.assertEqual(Config.EXIT_ERROR, 1)
          self.assertEqual(Config.EXIT_NO_DATA, 2)
  ```
- [ ] **Step 2: Run test to verify it fails**
  `python -m unittest tests/test_config.py`
- [ ] **Step 3: Implement `resume/.gitignore`, `scripts/config.py`, `scripts/logger.py`, and `requirements.txt`**
  - Configure `.gitignore` to ignore `generated/*`, `.venv`, `__pycache__`, `*.pyc`, `.DS_Store`, but explicitly ensure `!db/positions.db` is tracked.
  - Implement `scripts/config.py` with cross-platform `pathlib.Path` resolution, fallback detection for `HERMES_BATCH_QUEUE.json`, Edge path, and standard exit codes.
  - Implement `scripts/logger.py` writing append-only JSON lines to `logs/YYYY-MM-DD.jsonl`.
  - Create directories: `db/`, `master/`, `variants/`, `cover_letters/`, `generated/`, `logs/`, `scripts/portals/`, `tests/`.
- [ ] **Step 4: Run test to verify it passes**
  `python -m unittest tests/test_config.py`
- [ ] **Step 5: Commit task deliverable**
  `git add .gitignore requirements.txt scripts/config.py scripts/logger.py tests/test_config.py && git commit -m "chore: setup repo layout, config, logger and gitignore"`

---

### Task 2: Canonical Database Layer & CLI Initializer

**Files:**
- Create: `resume/db/schema.sql`
- Create: `resume/db/schema.md`
- Create: `resume/scripts/init_db.py`
- Test: `resume/tests/test_db.py`

**Interfaces:**
- Consumes: `schema.sql`, `config.Config.DB_PATH`.
- Produces: Fully initialized SQLite database at `db/positions.db` with tables `vacancies`, `applications`, `documents`, and performance indexes.

- [ ] **Step 1: Write the failing test for DB initialization and constraints**
  ```python
  # tests/test_db.py
  import unittest
  import sqlite3
  from scripts.config import Config
  from scripts.init_db import init_database

  class TestDatabase(unittest.TestCase):
      def test_init_creates_tables_and_indexes(self):
          test_db = Config.PROJECT_ROOT / "tests" / "test_tmp.db"
          if test_db.exists(): test_db.unlink()
          try:
              count = init_database(db_path=test_db)
              self.assertGreaterEqual(count, 3)
              conn = sqlite3.connect(test_db)
              tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
              self.assertIn("vacancies", tables)
              self.assertIn("applications", tables)
              self.assertIn("documents", tables)
              conn.close()
          finally:
              if test_db.exists(): test_db.unlink()
  ```
- [ ] **Step 2: Run test to verify it fails**
  `python -m unittest tests/test_db.py`
- [ ] **Step 3: Implement `db/schema.sql`, `db/schema.md`, and `scripts/init_db.py`**
  - `schema.sql`: define `vacancies`, `applications`, and `documents` schemas with foreign keys, checks on status enum, and indexes on `tier`, `sector`, `status`.
  - `scripts/init_db.py`: CLI with `--db-path`, `--json`, `--help` flags; executes `schema.sql` idempotently (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`).
  - Initialize active database `resume/db/positions.db`.
  - `db/schema.md`: English documentation with frontmatter, data dictionary, and example SQL queries for AI agents.
- [ ] **Step 4: Run test to verify it passes**
  `python -m unittest tests/test_db.py`
- [ ] **Step 5: Commit task deliverable**
  `git add db/schema.sql db/schema.md db/positions.db scripts/init_db.py tests/test_db.py && git commit -m "feat(db): canonical sqlite schema and idempotent init_db CLI"`

---

### Task 3: Hermes Batch Queue Sync Script (`sync_hermes.py`)

**Files:**
- Create: `resume/scripts/sync_hermes.py`
- Test: `resume/tests/test_sync_hermes.py`

**Interfaces:**
- Consumes: `HERMES_BATCH_QUEUE.json` (from `mywork` or CLI parameter `--queue-file`), `positions.db`.
- Produces: Upserted vacancy rows in `vacancies`, synced application records in `applications`, structured JSON report.

- [ ] **Step 1: Write the failing test for Hermes sync**
  ```python
  # tests/test_sync_hermes.py
  import unittest
  import json
  from scripts.sync_hermes import sync_queue_to_db

  class TestSyncHermes(unittest.TestCase):
      def test_sync_upserts_vacancies(self):
          # verify sample batch items are loaded into vacancies and applications table
          pass
  ```
- [ ] **Step 2: Run test to verify it fails**
  `python -m unittest tests/test_sync_hermes.py`
- [ ] **Step 3: Implement `scripts/sync_hermes.py`**
  - Parse `HERMES_BATCH_QUEUE.json` (1,500+ vacancies across batches).
  - Map fields: `id`, `title`, `company`, `url`, `salary`, `tier`, `category` -> `sector` (normalized to Finance / Logistics / Analytics / Management), `source='hh.uz'`.
  - Application mapping: if `applied_count > 0` or vacancy has application flag, record status as `applied` with `pdf_sent_in_chat` status.
  - Idempotent upsert logic using `INSERT ... ON CONFLICT(id) DO UPDATE`.
  - Support CLI arguments: `--queue-file`, `--dry-run`, `--limit`, `--json`, `--help`.
- [ ] **Step 4: Run test and verify live sync from `mywork`**
  - Run unit tests: `python -m unittest tests/test_sync_hermes.py`.
  - Execute sync CLI: `python scripts/sync_hermes.py --json`.
  - Verify records inserted into `db/positions.db`.
- [ ] **Step 5: Commit task deliverable**
  `git add scripts/sync_hermes.py db/positions.db tests/test_sync_hermes.py && git commit -m "feat(sync): idempotent Hermes batch queue sync script with json output"`

---

### Task 4: Manual Position Management CLIs (`add_position.py` & `update_status.py`)

**Files:**
- Create: `resume/scripts/add_position.py`
- Create: `resume/scripts/update_status.py`
- Test: `resume/tests/test_position_crud.py`

**Interfaces:**
- Consumes: CLI options (`--url`, `--company`, `--title`, `--status`, `--notes`), `positions.db`.
- Produces: Inserted/updated database rows, JSON response with updated entity details.

- [ ] **Step 1: Write the failing test for add_position and update_status**
  ```python
  # tests/test_position_crud.py
  import unittest
  from scripts.add_position import add_vacancy
  from scripts.update_status import update_application_status

  class TestPositionCRUD(unittest.TestCase):
      def test_add_and_update_lifecycle(self):
          pass
  ```
- [ ] **Step 2: Run test to verify it fails**
  `python -m unittest tests/test_position_crud.py`
- [ ] **Step 3: Implement `scripts/add_position.py` and `scripts/update_status.py`**
  - `add_position.py`: CLI accepting `--title`, `--company`, `--url`, `--source` (default `manual`), `--sector`, `--tier` (default 2), `--salary-text`, `--notes`, `--json`.
  - `update_status.py`: CLI accepting `--vacancy-id`, `--status` (`applied`, `viewed`, `invited`, `interview`, `offer`, `rejected`, `declined`), `--notes`, `--cv-variant`, `--json`.
  - Include validation for allowed status values and ISO 8601 timestamps for `last_updated`.
- [ ] **Step 4: Run test to verify it passes**
  `python -m unittest tests/test_position_crud.py`
- [ ] **Step 5: Commit task deliverable**
  `git add scripts/add_position.py scripts/update_status.py tests/test_position_crud.py && git commit -m "feat(cli): add_position and update_status CLI tools"`

---

### Task 5: Master Resumes, Variants & Sector Cover Letter Templates

**Files:**
- Create: `resume/master/resume.md`
- Create: `resume/master/resume.html`
- Create: `resume/variants/business_analyst.md`
- Create: `resume/variants/financial_analyst.md`
- Create: `resume/variants/operations_manager.md`
- Create: `resume/cover_letters/_template_base.md`
- Create: `resume/cover_letters/banking_finance.md`
- Create: `resume/cover_letters/logistics_aviation.md`
- Create: `resume/cover_letters/fmcg_distribution.md`
- Create: `resume/cover_letters/it_analytics.md`
- Test: `resume/tests/test_templates.py`

**Interfaces:**
- Consumes: Candidate profile data from `MY-WORK` and Desktop.
- Produces: Standardized markdown templates with validated `{{placeholder}}` markers for automated substitution.

- [ ] **Step 1: Write the failing test for template consistency and placeholder validation**
  ```python
  # tests/test_templates.py
  import unittest
  from scripts.config import Config

  class TestTemplates(unittest.TestCase):
      def test_cover_letter_templates_have_required_placeholders(self):
          required = ["{{company}}", "{{position}}", "{{candidate_name}}"]
          # check all files under cover_letters/
          pass
  ```
- [ ] **Step 2: Run test to verify it fails**
  `python -m unittest tests/test_templates.py`
- [ ] **Step 3: Implement master resume, variants, and sector cover letter templates**
  - Sourced from Abdulkhakim's profile: Senior Business Analyst / Financial Analyst / Operations.
  - Document all placeholders in `cover_letters/_template_base.md` (`{{company}}`, `{{position}}`, `{{sector_hook}}`, `{{key_achievement}}`, `{{salary_expectation}}`, `{{candidate_name}}`, `{{candidate_phone}}`, `{{candidate_email}}`, `{{date}}`).
  - Create sector templates for Banking/Finance, Logistics/Aviation, FMCG/Distribution, IT/Analytics.
- [ ] **Step 4: Run test to verify it passes**
  `python -m unittest tests/test_templates.py`
- [ ] **Step 5: Commit task deliverable**
  `git add master/ variants/ cover_letters/ tests/test_templates.py && git commit -m "feat(templates): master resume, role variants, and sector cover letters"`

---

### Task 6: Document Generator Engine (`generate_docs.py`)

**Files:**
- Create: `resume/scripts/generate_docs.py`
- Test: `resume/tests/test_generate_docs.py`

**Interfaces:**
- Consumes: `vacancy_id` from `positions.db`, templates from `cover_letters/` and `variants/`.
- Produces: Rendered documents in `generated/<company_slug>_<vacancy_id>/` (`cover_letter.md`, `cover_letter.pdf`, `cv_tailored.md`, `cv_tailored.pdf`), database record in `documents` table.

- [ ] **Step 1: Write the failing test for document generation**
  ```python
  # tests/test_generate_docs.py
  import unittest
  from scripts.generate_docs import generate_documents_for_vacancy

  class TestGenerateDocs(unittest.TestCase):
      def test_generates_markdown_and_records_in_db(self):
          pass
  ```
- [ ] **Step 2: Run test to verify it fails**
  `python -m unittest tests/test_generate_docs.py`
- [ ] **Step 3: Implement `scripts/generate_docs.py`**
  - Read vacancy metadata (`company`, `title`, `sector`, `tier`) from `positions.db`.
  - Resolve appropriate sector template and role variant.
  - Render placeholders into target markdown files.
  - Generate clean HTML/PDF export into `generated/<company_slug>_<vacancy_id>/` (using headless Edge or ReportLab).
  - Register generated files in `documents` table.
  - Support CLI arguments: `--vacancy-id`, `--format` (`md`, `html`, `pdf`), `--variant`, `--dry-run`, `--json`, `--help`.
- [ ] **Step 4: Run test to verify it passes**
  `python -m unittest tests/test_generate_docs.py`
- [ ] **Step 5: Commit task deliverable**
  `git add scripts/generate_docs.py tests/test_generate_docs.py && git commit -m "feat(generator): automated cover letter and CV generation engine"`

---

### Task 7: Pipeline Dashboard, Markdown Summary & AI Context (`dashboard.py`)

**Files:**
- Create: `resume/scripts/dashboard.py`
- Create: `resume/dashboard.html`
- Create: `resume/PIPELINE.md`
- Create: `resume/AI_CONTEXT.md`
- Test: `resume/tests/test_dashboard.py`

**Interfaces:**
- Consumes: Data in `positions.db` (`vacancies`, `applications`, `documents`).
- Produces: Updated `dashboard.html`, `PIPELINE.md`, and `AI_CONTEXT.md`.

- [ ] **Step 1: Write the failing test for dashboard generation**
  ```python
  # tests/test_dashboard.py
  import unittest
  from scripts.dashboard import build_dashboard_artifacts

  class TestDashboard(unittest.TestCase):
      def test_generates_all_three_artifacts(self):
          pass
  ```
- [ ] **Step 2: Run test to verify it fails**
  `python -m unittest tests/test_dashboard.py`
- [ ] **Step 3: Implement `scripts/dashboard.py`**
  - Query DB for aggregation: status breakdown (`applied`, `viewed`, `invited`, `interview`, `offer`, `rejected`), tier breakdown, recent applications.
  - Build `dashboard.html`: standalone responsive HTML Kanban board with search and filter.
  - Build `PIPELINE.md`: Markdown summary table with full YAML frontmatter complying with `doc-standarts-draft.md`.
  - Build `AI_CONTEXT.md`: Machine-readable YAML/Markdown context file containing total counts, active batch info, next actions, and query hints for AI agents.
  - Support CLI flags: `--json`, `--output-dir`, `--help`.
- [ ] **Step 4: Run test to verify it passes and inspect generated artifacts**
  `python -m unittest tests/test_dashboard.py`
- [ ] **Step 5: Commit task deliverable**
  `git add scripts/dashboard.py dashboard.html PIPELINE.md AI_CONTEXT.md tests/test_dashboard.py && git commit -m "feat(dashboard): visual kanban, PIPELINE.md and AI_CONTEXT.md generator"`

---

### Task 8: Portal Scraping Stubs & Policy Documentation (`scripts/portals/`)

**Files:**
- Create: `resume/scripts/portals/README.md`
- Create: `resume/scripts/portals/hh_watcher.py`
- Create: `resume/scripts/portals/olx_scraper.py`
- Test: `resume/tests/test_portals.py`

**Interfaces:**
- Consumes: Web responses from hh.uz and OLX UZ.
- Produces: Standardized vacancy dictionaries for ingestion into `positions.db`.

- [ ] **Step 1: Write the failing test for portal parsers**
  ```python
  # tests/test_portals.py
  import unittest
  from scripts.portals.olx_scraper import parse_olx_html

  class TestPortals(unittest.TestCase):
      def test_parse_olx_sample_html(self):
          pass
  ```
- [ ] **Step 2: Run test to verify it fails**
  `python -m unittest tests/test_portals.py`
- [ ] **Step 3: Implement portal scrapers and document portal policy**
  - `scripts/portals/README.md`: Document portal statuses. Explicitly document that **Telegram channels are deferred to a future phase (`not yet telegram channels`)** and define the future intake interface.
  - `scripts/portals/hh_watcher.py`: Syncs new postings found on hh.uz into `positions.db`.
  - `scripts/portals/olx_scraper.py`: Scrapes OLX Uzbekistan job listings and normalizes them into the standard vacancy schema.
- [ ] **Step 4: Run test to verify it passes**
  `python -m unittest tests/test_portals.py`
- [ ] **Step 5: Commit task deliverable**
  `git add scripts/portals/ tests/test_portals.py && git commit -m "feat(portals): hh watcher, olx scraper, and telegram roadmap documentation"`

---

### Task 9: AI-First Documentation System & Agent Cold-Start Protocol

**Files:**
- Create: `resume/AGENTS.md`
- Create: `resume/README.md`
- Create: `resume/scripts/README.md`
- Test: `resume/tests/test_ai_first_pipeline.py`

**Interfaces:**
- Consumes: All repository tools, schema, and documentation.
- Produces: Single entry point for any AI agent to inspect, navigate, and execute any job tracking workflow.

- [ ] **Step 1: Write an end-to-end integration test simulating an AI agent lifecycle**
  ```python
  # tests/test_ai_first_pipeline.py
  import unittest
  import subprocess
  import sys
  from scripts.config import Config

  class TestAIFirstPipeline(unittest.TestCase):
      def test_full_agent_workflow(self):
          # 1. Check DB health via CLI
          # 2. Add sample position via CLI
          # 3. Update status via CLI
          # 4. Generate docs via CLI
          # 5. Refresh dashboard & AI context via CLI
          pass
  ```
- [ ] **Step 2: Run test to verify full end-to-end flow**
  `python -m unittest tests/test_ai_first_pipeline.py`
- [ ] **Step 3: Author comprehensive AI-First documentation with mandatory YAML frontmatter**
  - `AGENTS.md`: Cold-start guide for AI agents. Contains:
    - 1-paragraph purpose.
    - Architecture and file map.
    - CLI Dictionary with exact commands and JSON flags.
    - SQLite schema cheat sheet & common queries.
    - Rules: no hardcoded secrets, no direct writes to tracked DB without CLI validation, gitignore rules for `generated/`.
  - `README.md`: Master human and agent navigation index complying with `doc-standarts-draft.md`.
  - `scripts/README.md`: Detailed CLI reference documentation for every script.
- [ ] **Step 4: Run complete repository test suite**
  `python -m unittest discover tests`
- [ ] **Step 5: Commit task deliverable and final documentation**
  `git add AGENTS.md README.md scripts/README.md tests/test_ai_first_pipeline.py && git commit -m "docs(ai-first): AGENTS.md, master README and end-to-end AI agent test suite"`

---

## Verification Gates & Acceptance Criteria

1. **AI Cold-Start Gate:**
   - Any AI agent opening the repo cold can read `AGENTS.md` and `AI_CONTEXT.md` to know the exact pipeline status, active batch number, and required command to execute.
2. **Git Hygiene Gate:**
   - `git status` confirms `generated/` is ignored.
   - `git status` confirms `db/positions.db` is tracked.
3. **Hermes Integration Gate:**
   - `python scripts/sync_hermes.py --json` imports all batches from `HERMES_BATCH_QUEUE.json` idempotently without duplicates.
4. **Document Generation Gate:**
   - `python scripts/generate_docs.py --vacancy-id <id> --json` generates tailored cover letter and CV into `generated/<slug>_<id>/` in under 5 seconds.
5. **Dashboard Gate:**
   - `python scripts/dashboard.py` creates or refreshes `dashboard.html`, `PIPELINE.md`, and `AI_CONTEXT.md`.
6. **Test Suite Gate:**
   - `python -m unittest discover tests` runs with 100% passing tests.
