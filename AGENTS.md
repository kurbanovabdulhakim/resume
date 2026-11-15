---
title: AI Agent Operating Manual — Resume Hub
description: Canonical operating directives and CLI workflows for AI agents in the resume repository.
status: active
category: runbook
last-verified: 2026-11-08
---

# AI Agent Operating Manual (`resume`)

> **Cold-Start Directive:** Any AI agent opening this repository must read this file and inspect [AI_CONTEXT.md](file:///c:/Users/Abdulkhakim/gitHub/resume/AI_CONTEXT.md) (or run `python scripts/dashboard.py --json`) to understand live pipeline state before taking action.

---

## 1. Core Architecture & Mandatory Boundaries

1. **Single Source of Truth (SSOT):**
   - `db/positions.db` is the authoritative SQLite database. It is **tracked in Git**.
   - `generated/` contains ephemeral rendered PDFs/HTMLs and is strictly **gitignored**. Never commit generated documents.
   - After any DB update or sync, run `python scripts/dashboard.py` to refresh `dashboard.html`, `PIPELINE.md`, and `AI_CONTEXT.md`. Never hand-edit `AI_CONTEXT.md`.
2. **CLI & Script Standards:**
   - Always pass `--json` when executing scripts programmatically.
   - All scripts must support `--help` and `--json`, be idempotent, and return standard exit codes (`0` = success, `1` = error, `2` = skipped).
   - Never hardcode absolute paths; always import paths from `scripts.config.Config`.
3. **Operational Scope:**
   - Active sources: HeadHunter (`hh.uz`) and OLX (`olx.uz`).
   - **No Telegram channels yet:** Telegram scraping and bot listeners are explicitly deferred.
4. **Minimalist Standard Library Rule (Ponytail):**
   - Standard library first: prioritize Python stdlib (`sqlite3`, `pathlib`, `json`, `argparse`, `re`, `datetime`).
   - Reuse existing utilities in `scripts/`; avoid adding external dependencies.
5. **Quality, Testing & Humanization:**
   - Run unit tests before closing multi-step tasks: `python -m unittest discover tests`.
   - All generated documents (CVs, cover letters, reports) must strictly follow the global `document-humanizer` rule (`skill: humanizer`).

---

## 2. Key CLI Workflows

### A. Cold-Start Pipeline Inspection
```bash
python scripts/dashboard.py --json
```

### B. Sync from Hermes 2.0 Queue
```bash
python scripts/sync_hermes.py --json
python scripts/dashboard.py --json
```

### C. Manually Register Vacancy
```bash
python scripts/add_position.py \
  --title "Senior Financial Analyst" \
  --company "Uzum Bank" \
  --url "https://tashkent.hh.uz/vacancy/138999999" \
  --tier 1 \
  --sector Finance \
  --notes "Direct outreach" \
  --json
```

### D. Progress Application Stage
*Valid stages:* `applied`, `viewed`, `invited`, `interview`, `offer`, `rejected`, `declined`.
```bash
python scripts/update_status.py \
  --vacancy-id 138999999 \
  --status interview \
  --notes "1st round scheduled" \
  --json
python scripts/dashboard.py --json
```

### E. Generate Tailored CV and Cover Letter
```bash
python scripts/generate_docs.py \
  --vacancy-id 138999999 \
  --format md,html,pdf \
  --json
```
