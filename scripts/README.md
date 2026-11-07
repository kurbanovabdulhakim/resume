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
