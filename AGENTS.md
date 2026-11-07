---
title: AI Agent Operating Manual and System Architecture
description: Canonical entry point and operational manual for AI agents working in the resume repository.
status: active
category: runbook
tags: [agents, ai-first, architecture, operations, cli, hermes, guide]
last-verified: 2026-11-08
summary-ru: Главное руководство и справочник для ИИ-агентов по работе с репозиторием resume.
summary-uz: resume repozitoriyasida sun'iy intellekt agentlari ishlashi uchun asosiy qo'llanma.
related:
  - README.md
  - AI_CONTEXT.md
  - PIPELINE.md
  - db/schema.md
  - scripts/README.md
---

# AI Agent Operating Manual (`AGENTS.md`)

> **Cold-Start Directive:** Any AI agent (Antigravity, Claude, Codex, Gemini) opening this repository should immediately read this file and inspect [AI_CONTEXT.md](file:///c:/Users/Abdulkhakim/gitHub/resume/AI_CONTEXT.md) to understand the current live pipeline state without relying on chat history.

---

## 1. Purpose of this Repository

The `resume` repository is the **central command hub and Single Source of Truth (SSOT)** for Abdulkhakim Kurbanov's job search operations across Uzbekistan. It hosts:
1. **SQLite Database (`db/positions.db`)**: Tracks all vacancies (1,500+ targets), application progression stages (`applied`, `viewed`, `invited`, `interview`, `offer`, `rejected`), and document audit trails.
2. **Hermes 2.0 Integration (`scripts/sync_hermes.py`)**: Ingests automated application batches dispatched from `mywork`.
3. **Automated Document Generator (`scripts/generate_docs.py`)**: Renders vacancy-tailored cover letters and role-specific CV variants in Markdown, HTML, and PDF.
4. **Visual & Machine Reporting (`dashboard.py`)**: Compiles `dashboard.html` (visual Kanban board), `PIPELINE.md` (human overview), and `AI_CONTEXT.md` (machine-readable state).

---

## 2. Repository Layout & File Map

```
resume/
├── .agents/                    # Agent governance rules (AI-First, Doc standards, Ponytail)
├── AGENTS.md                   # YOU ARE HERE — Primary AI entry point & CLI guide
├── AI_CONTEXT.md               # Machine-readable current state (auto-regenerated)
├── PIPELINE.md                 # Human-readable pipeline summary table
├── dashboard.html              # Standalone interactive Kanban board
├── README.md                   # Top-level index and onboarding guide
├── requirements.txt            # Minimal stdlib-first dependencies
├── db/
│   ├── schema.sql              # Canonical SQLite schema (SSOT)
│   ├── schema.md               # Table data dictionary and SQL query cheat-sheet
│   └── positions.db            # SQLite database (TRACKED in git)
├── master/
│   ├── resume.md               # Canonical master Markdown resume
│   └── resume.html             # Styled printable HTML version
├── variants/                   # Role-tailored CV markdown variants
│   ├── business_analyst.md
│   ├── financial_analyst.md
│   └── operations_manager.md
├── cover_letters/              # Sector cover letter templates with {{placeholders}}
│   ├── _template_base.md       # Annotated template specification
│   ├── banking_finance.md      # Tier 1 Banks / Auditing / Corporate Finance
│   ├── logistics_aviation.md   # Supply Chain / Freight / Logistics
│   ├── fmcg_distribution.md    # Retail / FMCG / Distribution
│   └── it_analytics.md         # Tech / Business Analysis / Product
├── generated/                  # Generated vacancy assets (GITIGNORED)
│   └── <company_slug>_<id>/    # cover_letter.md/.pdf, cv_tailored.md/.pdf
├── logs/                       # Daily structured JSONL audit logs (YYYY-MM-DD.jsonl)
├── scripts/
│   ├── config.py               # Central configuration & path resolver
│   ├── logger.py               # Structured JSONL event logger
│   ├── init_db.py              # Idempotent DB schema creator
│   ├── sync_hermes.py          # Hermes batch queue synchronization
│   ├── add_position.py         # Manual vacancy & application registration
│   ├── update_status.py        # Application status progression
│   ├── generate_docs.py        # Tailored CV and Cover Letter generator
│   ├── dashboard.py            # Dashboard and context compiler
│   ├── README.md               # Detailed CLI documentation
│   └── portals/
│       ├── README.md           # Portal roadmap (Telegram deferred)
│       ├── hh_watcher.py       # Fresh HeadHunter postings watcher
│       └── olx_scraper.py      # OLX Uzbekistan scraper
└── tests/                      # Python unittest test suite
```

---

## 3. Data Flow Architecture

```
[ HeadHunter / Hermes 2.0 ]  -->  mywork/HERMES_BATCH_QUEUE.json
                                        │
                                        ▼  python scripts/sync_hermes.py
                                 [ db/positions.db ]  <──  python scripts/add_position.py
                                        │
            ┌───────────────────────────┼───────────────────────────┐
            ▼                           ▼                           ▼
python scripts/generate_docs.py  python scripts/update_status.py  python scripts/dashboard.py
            │                           │                           │
            ▼                           ▼                           ▼
generated/<slug>_<id>/           Updated Stage              dashboard.html
- cover_letter.pdf               (interview / offer)        PIPELINE.md
- cv_tailored.pdf                                           AI_CONTEXT.md
```

---

## 4. Key Agent Workflows & Exact Commands

### Workflow A: Cold-Start State Inspection
```bash
# 1. Read current machine state
cat AI_CONTEXT.md

# 2. Or query database metrics via CLI
python scripts/dashboard.py --json
```

### Workflow B: Sync from Hermes Batch Queue
```bash
# Pulls latest applications dispatched by Hermes from mywork
python scripts/sync_hermes.py --json

# Recompile dashboard
python scripts/dashboard.py --json
```

### Workflow C: Manually Add a New Vacancy
```bash
python scripts/add_position.py \
  --title "Senior Financial Analyst" \
  --company "Uzum Bank" \
  --url "https://tashkent.hh.uz/vacancy/138999999" \
  --tier 1 \
  --sector Finance \
  --notes "Contacted by HR directly on LinkedIn" \
  --json
```

### Workflow D: Update Candidate Recruitment Stage
Valid statuses: `applied`, `viewed`, `invited`, `interview`, `offer`, `rejected`, `declined`.
```bash
python scripts/update_status.py \
  --vacancy-id 138999999 \
  --status interview \
  --notes "1st Round with Head of BI scheduled for Thursday 15:00" \
  --json

# Refresh dashboard
python scripts/dashboard.py --json
```

### Workflow E: Generate Tailored Cover Letter & CV
```bash
python scripts/generate_docs.py \
  --vacancy-id 138999999 \
  --format md,html,pdf \
  --json
```

---

## 5. Mandatory Operating Directives for AI Agents

1. **Storage Hygiene**:
   - `db/positions.db` is **tracked in Git**. Commit it whenever updates occur.
   - `generated/` is strictly **gitignored**. Never force-add generated PDFs to git.
2. **No Telegram Channels Yet**:
   - Telegram channels are explicitly deferred (`not yet telegram channels`). Do not create or run telegram background listeners.
3. **Paths & Config**:
   - Never hardcode absolute Windows paths. Always import paths from `scripts.config.Config`.
4. **Tool Interfaces**:
   - Every script supports `--help` and `--json`. Always pass `--json` when executing commands programmatically.
   - Standard exit codes: `0` = success, `1` = error, `2` = no data / skipped.
5. **Documentation Standard**:
   - When modifying any markdown file, strictly maintain YAML frontmatter according to `.agents/rules/doc-standarts-draft.md`.
