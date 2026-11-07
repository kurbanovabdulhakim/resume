---
title: AI-First Development Rules — Resume & Job Search Hub
description: Mandatory operational guidelines for AI agents managing job tracking, tailored document generation, and portal synchronizations in the resume repository.
status: active
category: rule
tags: [ai-first, job-tracker, resume, hermes, automation, sqlite, guidelines]
last-verified: 2026-11-08
summary-ru: Обязательные правила для ИИ-агентов по управлению базой вакансий, генерации резюме/писем и синхронизации с Hermes в репозитории resume.
summary-uz: Resume repozitoriyasida vakansiyalar bazasi, moslashtirilgan rezyume/xatlar yaratish va Hermes bilan sinxronizatsiyani boshqaruvchi AI agentlari uchun qoidalar.
related:
  - AGENTS.md
  - AI_CONTEXT.md
  - docs/superpowers/plans/2026-11-08-ai-first-job-tracker.md
  - .agents/rules/doc-standarts-draft.md
  - .agents/rules/ponytail.md
  - db/schema.md
---
# AI-First Development & Maintenance Rules (`resume`)

> **Scope:** These directives govern how AI agents (Antigravity, Cursor, Hermes, Codex) autonomously discover state, execute tasks, generate application assets, and maintain data integrity in `c:\Users\Abdulkhakim\gitHub\resume`.

---

## 1. Core Architecture & Single Source of Truth (SSOT)

1. **SQLite Database as Master Record:**
   - `db/positions.db` is the **Single Source of Truth** for all vacancy statuses, interview logs, and document references.
   - `db/positions.db` is strictly **tracked in Git** (small, portable, binary-diffable).
   - Never store application state across loose text files, ad-hoc spreadsheets, or memory scratchpads.
2. **Schema Authority:**
   - `db/schema.sql` defines the canonical schema. Any table or column addition must be reflected there and documented in `db/schema.md`.
3. **Artifact Isolation (`generated/` is Ephemeral):**
   - All rendered documents (PDFs, temporary HTMLs, company-specific output) live in `generated/<company_slug>_<vacancy_id>/`.
   - `generated/` is **strictly gitignored**. Never commit generated PDFs to the repository.
   - The file paths to generated documents are tracked inside the `documents` table in `db/positions.db`.

---

## 2. Cold-Start Protocol & Machine-Readable State

1. **Orientation Sequence for Agents:**
   - Step 1: Read `AGENTS.md` for role boundaries, CLI reference, and tool conventions.
   - Step 2: Read `AI_CONTEXT.md` for live pipeline telemetry (total applications, active batch, interviews needing action).
   - Step 3: Run queries via `scripts/query.py --json` or `sqlite3` on `db/positions.db`.
2. **Auto-Regenerating Context:**
   - After any DB update or sync operation, the agent must run `python scripts/dashboard.py` to refresh `dashboard.html`, `PIPELINE.md`, and `AI_CONTEXT.md`.
   - Never manually hand-edit `AI_CONTEXT.md`.

---

## 3. Autonomous Execution & Hermes Synchronization

1. **Idempotence Required:**
   - Every script in `scripts/` (e.g., `sync_hermes.py`, `init_db.py`, `generate_docs.py`) must be strictly idempotent. Running them multiple times must never create duplicate records or corrupted states.
2. **Hermes 2.0 Integration Contract:**
   - `scripts/sync_hermes.py` reads `HERMES_BATCH_QUEUE.json` from `mywork` (or mirror) and performs atomic upserts into `vacancies` and `applications`.
   - Status transitions follow canonical enums: `applied` -> `viewed` -> `invited` -> `interview` -> `offer` -> `rejected` -> `declined`.
3. **Scope Boundary (Portals & Telegram):**
   - Active job ingestion sources: `hh.uz` (via Hermes queue / watcher) and `olx.uz` (via `scripts/portals/olx_scraper.py`).
   - **Telegram channels are deferred (`not yet telegram channels`)**. Agents must not build unprompted Telegram bots or scrape telegram channels until explicitly requested in future phases.

---

## 4. Scripting & Tool Standards

1. **Standard Library & Ponytail Minimalist Ladder:**
   - Prioritize Python stdlib: `sqlite3`, `pathlib`, `json`, `argparse`, `re`, `datetime`.
   - Avoid bloated dependencies for simple transformations.
2. **Unified Configuration (`scripts/config.py`):**
   - Never hardcode absolute Windows paths in business logic scripts. All paths must be imported from `scripts.config.Config`.
3. **CLI Contract for Agent Consumption:**
   - Every script must provide:
     - `--help` describing arguments and examples.
     - `--json` providing structured output (machine-readable for calling agents).
     - Standard exit codes: `0` = success, `1` = runtime/validation error, `2` = no data / skipped.
4. **Structured Audit Logs:**
   - Operational logs must be written as structured JSON Lines (JSONL) into `logs/YYYY-MM-DD.jsonl` (handled by `scripts/logger.py`).

---

## 5. Security, Secrets & Candidate Hygiene

1. **Zero Hardcoded Secrets:**
   - Never commit HeadHunter account tokens, session cookies, passwords, or personal identity numbers.
   - Session states rely on existing persistent profiles (e.g., `%LOCALAPPDATA%\HermesAutomationProfile`).
2. **Accurate Representation:**
   - Generated resumes and cover letters must draw exclusively from `master/resume.md` and approved variants. Never hallucinate fake employment history, exaggerated metrics, or unverified certifications.

---

## 6. Failure Behavior & Self-Healing

1. **Halt and Report on Critical Errors:**
   - If SQLite migration fails, schema validation breaks, or file locks occur, stop immediately.
   - Log the structured error into `logs/YYYY-MM-DD.jsonl` and return exit code `1`.
2. **Preflight Verification:**
   - Run unit tests (`python -m unittest discover tests`) before concluding any significant multi-step feature implementation.
