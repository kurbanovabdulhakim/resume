---
title: Scripts and CLI Reference Manual
description: Comprehensive CLI argument reference, usage examples, and JSON output schemas for all repository scripts.
status: active
category: reference
tags: [scripts, cli, reference, automation, python]
last-verified: 2026-11-08
summary-ru: Справочник по всем консольным скриптам репозитория, флагам аргументов и форматам JSON-вывода.
summary-uz: Repozitoriyadagi barcha konsol skriptlari, argumentlar va JSON javob formatlari bo'yicha ma'lumotnoma.
related:
  - AGENTS.md
  - db/schema.md
---

# Scripts & CLI Reference Manual

All scripts are located in `scripts/` and designed to be executed from the repository root:
`python scripts/<script_name>.py [OPTIONS]`

Every script provides:
- `--help`: Human-readable argument documentation.
- `--json`: Machine-readable JSON output for AI agent consumption.
- Standardized exit codes (`0` = success, `1` = error, `2` = no data / not found).

---

## 1. `init_db.py`
Idempotently initializes or verifies the SQLite database schema at `db/positions.db`.

```bash
python scripts/init_db.py [--db-path PATH] [--json]
```
**Flags:**
- `--db-path PATH`: Path to target SQLite database (default: `db/positions.db`).
- `--json`: Output result as JSON.

---

## 2. `sync_hermes.py`
Synchronizes vacancies and confirmed application stages from `HERMES_BATCH_QUEUE.json` in `mywork`.

```bash
python scripts/sync_hermes.py [--queue-file PATH] [--limit N] [--dry-run] [--json]
```
**Flags:**
- `--queue-file PATH`: Path to queue JSON (autodetected if omitted).
- `--limit N`: Limit number of vacancies processed.
- `--dry-run`: Test execution without modifying the database.
- `--json`: Output machine-readable JSON.

---

## 3. `add_position.py`
Manually registers a vacancy and initial application status in the database.

```bash
python scripts/add_position.py --title "Title" --company "Company" [OPTIONS]
```
**Flags:**
- `--title TEXT` *(required)*: Job title.
- `--company TEXT` *(required)*: Employer name.
- `--url TEXT`: Web link to posting.
- `--tier INT`: Priority tier (`1` = Banks/Corps, `2` = Mid, `3` = Small).
- `--sector TEXT`: `Finance`, `Logistics`, `Analytics`, or `Management`.
- `--salary TEXT`: Salary string.
- `--notes TEXT`: Notes / remarks.
- `--status TEXT`: Initial status (default: `applied`).
- `--json`: Output machine-readable JSON.

---

## 4. `update_status.py`
Progresses an application through recruitment stages:
`applied` → `viewed` → `invited` → `interview` → `offer` → `rejected` / `declined`.

```bash
python scripts/update_status.py --vacancy-id ID --status STATUS [--notes NOTES] [--json]
```
**Flags:**
- `--vacancy-id ID` *(required)*: Target vacancy ID.
- `--status STATUS` *(required)*: Target status.
- `--notes TEXT`: Notes, interviewer feedback, or scheduling info.
- `--cv-variant TEXT`: Record specific CV variant used.
- `--json`: Output machine-readable JSON.

---

## 5. `generate_docs.py`
Generates tailored cover letter and role-specific CV for a target vacancy.

```bash
python scripts/generate_docs.py --vacancy-id ID [--format md,pdf] [--json]
```
**Flags:**
- `--vacancy-id ID` *(required)*: Target vacancy ID.
- `--format FORMATS`: Formats comma-separated (`md`, `html`, `pdf`). Default: `md,pdf`.
- `--json`: Output machine-readable JSON.

**Output Destination:** `generated/<company_slug>_<vacancy_id>/`

---

## 6. `dashboard.py`
Compiles live pipeline state into `dashboard.html`, `PIPELINE.md`, and `AI_CONTEXT.md`.

```bash
python scripts/dashboard.py [--json]
```
**Flags:**
- `--db-path PATH`: Custom DB path.
- `--html-path PATH`: Custom HTML path.
- `--json`: Output machine-readable JSON.

---

## 7. `hh_ai.py`
Scores HeadHunter vacancies against `master/resume.md` and composes `humanizer`-verified Russian cover letters via local Ollama (`qwen2.5-coder:7b`) or Hermes.

```bash
python scripts/hh_ai.py --vacancy-id 139244548 --backend ollama --json
```
**Flags:**
- `--vacancy-id ID` / `--title TITLE`: Target vacancy from DB or manual input.
- `--backend ollama|hermes|none`: LLM composer backend. Default: `ollama`.
- `--json`: Output machine-readable JSON.

---

## 8. `hh_queue.py`
Selects eligible unapplied `hh.uz` vacancies, tracks daily quota (`--daily-limit 200`), and persists queue states (`data/hh_autonomy_queue.json`, `data/hh_autonomy_state.json`).

```bash
python scripts/hh_queue.py --status --json
python scripts/hh_queue.py --prepare --limit 25 --backend ollama --json
```

---

## 9. `hh_apply.py` & `launch_hh_visible.ps1`
Visible multi-mode HeadHunter application runner supporting autonomous wave mode (`--mode browser --confirm none`), per-item manual confirmation (`--confirm each`), official `dev.hh.ru` OAuth API (`--mode api`), and clipboard-assist (`--mode assist`). Pauses with audible + console alert on CAPTCHA or login screens and lets the user switch live to `--confirm each`.

```bash
python scripts/hh_apply.py --dry-run --limit 5 --backend ollama --json
python scripts/hh_apply.py --mode browser --confirm none --daily-limit 200 --wave-size 25 --start-url "https://tashkent.hh.uz/vacancies/finansovyy_analitik" --target-min-score 0
scripts\Start_HH_Visible.cmd
```
**Key URL priority flags:**
- `--start-url URL`: Harvests all pages of an explicit HH category/search URL and prioritizes those vacancies strictly first.
- `--target-min-score N` (default `0` for explicit URL): Allows applying to all open unapplied vacancies from `--start-url` before falling back to general `db/positions.db` (`--min-score 55`).
- `--harvest-max-pages N` / `--target-only`: Controls search page depth and whether to stop after `--start-url`.
