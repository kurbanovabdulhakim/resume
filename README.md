---
title: Job Position Tracker and Document Generator Hub
description: Central command repository for job vacancy tracking, automated document generation, and recruitment pipeline visualization across Uzbekistan.
status: active
category: index
tags: [job-tracker, resume, hermes, automation, kanban, uzbekistan]
last-verified: 2026-11-08
summary-ru: Центральный репозиторий для учета вакансий, генерации резюме и визуализации воронки откликов в Узбекистане.
summary-uz: O'zbekiston bo'yicha vakansiyalarni boshqarish, rezyumelarni avtomatlashtirish va suhbat bosqichlarini kuzatish uchun markaziy repozitoriy.
related:
  - AGENTS.md
  - AI_CONTEXT.md
  - PIPELINE.md
  - db/schema.md
  - scripts/README.md
  - scripts/portals/README.md
---

# `resume` — Job Position Tracker & Document Generator

Welcome to the **central operational repository** for Abdulkhakim Kurbanov's professional job search and career operations in Uzbekistan.

This repository is built following **AI-First & Autonomous Maintenance principles**: any human operator or AI agent can open the project cold and immediately understand the pipeline, process vacancies, and generate tailored application assets without conversational dependencies.

---

## ⚡ Quick Start

### 1. View Current Pipeline State
Open [dashboard.html](file:///c:/Users/Abdulkhakim/gitHub/resume/dashboard.html) in your browser for the visual Kanban board, or inspect [PIPELINE.md](file:///c:/Users/Abdulkhakim/gitHub/resume/PIPELINE.md).

### 2. Synchronize Vacancies from Hermes 2.0
```bash
python scripts/sync_hermes.py
python scripts/dashboard.py
```

### 3. Generate Tailored CV and Cover Letter for a Vacancy
```bash
python scripts/generate_docs.py --vacancy-id 138959503 --format md,pdf
```
Outputs are saved to `generated/<company_slug>_<vacancy_id>/` (gitignored).

### 4. Progress Application Status
```bash
python scripts/update_status.py --vacancy-id 138959503 --status interview --notes "1st round scheduled"
python scripts/dashboard.py
```

---

## 📑 Repository Documentation Index

| Document | Category | Description |
| :--- | :--- | :--- |
| **[AGENTS.md](file:///c:/Users/Abdulkhakim/gitHub/resume/AGENTS.md)** | Runbook | Master AI-First operating manual, cold-start protocol, and CLI guide. |
| **[AI_CONTEXT.md](file:///c:/Users/Abdulkhakim/gitHub/resume/AI_CONTEXT.md)** | Status | Machine-readable real-time pipeline state consumed by autonomous agents. |
| **[PIPELINE.md](file:///c:/Users/Abdulkhakim/gitHub/resume/PIPELINE.md)** | Status | Markdown summary table of response rates, active batches, and tiers. |
| **[db/schema.md](file:///c:/Users/Abdulkhakim/gitHub/resume/db/schema.md)** | Architecture | Data dictionary for `positions.db` (`vacancies`, `applications`, `documents`). |
| **[scripts/README.md](file:///c:/Users/Abdulkhakim/gitHub/resume/scripts/README.md)** | Reference | Comprehensive argument manual and JSON examples for all CLI tools. |
| **[scripts/portals/README.md](file:///c:/Users/Abdulkhakim/gitHub/resume/scripts/portals/README.md)** | Architecture | Portals status (hh.uz, OLX UZ) and policy (Telegram channels deferred). |
| **[cover_letters/_template_base.md](file:///c:/Users/Abdulkhakim/gitHub/resume/cover_letters/_template_base.md)** | Reference | Base cover letter template with placeholder definitions. |

---

## 🏗️ Architecture & Storage Strategy

- **Single Source of Truth (SSOT):** `db/positions.db` is an SQLite database tracked in git. It stores all vacancy metadata, recruitment statuses, and document generation logs.
- **Git Hygiene:** Large PDFs and vacancy-specific outputs in `generated/` are strictly **gitignored**.
- **Stdlib-First Architecture:** Adheres to minimalist design (`.agents/rules/ponytail.md`) using Python standard libraries (`sqlite3`, `pathlib`, `json`, `argparse`, `re`).
- **Headless PDF Generation:** High-fidelity PDFs are rendered using Microsoft Edge headless engine or standard fallback tools.

---

## 🧪 Testing and Verification

To run the complete automated test suite:
```bash
python -m unittest discover tests
```
