# Design Spec: `resume` Repo — Job Position Tracker & Document Generator

**Date:** 2026-11-07  
**Author:** Abdulkhakim Kurbanov  
**Status:** Approved for Implementation

---

## 1. Purpose

The `resume` repository is the **central hub** for Abdulkhakim's job search in Uzbekistan:

1. **Position Tracking** — SQLite database as single source of truth for all vacancies from hh.uz, OLX UZ, Telegram channels, LinkedIn. Tracks application status, interview stages, documents sent.
2. **Document Generation** — Python scripts auto-generate tailored cover letters and CV variants per vacancy, based on the master resume.
3. **Pipeline Dashboard** — HTML Kanban board (Applied → Interview → Offer → Rejected) auto-generated from the DB.
4. **Hermes Integration** — `sync_hermes.py` pulls already-applied vacancies from `HERMES_BATCH_QUEUE.json` in `mywork` repo into the DB.

---

## 2. Repo Structure

```
resume/
│
├── master/                           # Canonical master resume — source of truth
│   ├── resume.md                     # Master resume (Markdown)
│   ├── resume.pdf                    # Rendered PDF
│   ├── resume.html                   # Styled HTML version
│   └── portfolio.pdf                 # Portfolio document
│
├── variants/                         # Role-tailored CV templates (Markdown)
│   ├── business_analyst.md
│   ├── financial_analyst.md
│   └── operations_manager.md
│
├── cover_letters/                    # Cover letter templates per sector
│   ├── _template_base.md             # Base template with {{placeholders}}
│   ├── banking_finance.md
│   ├── logistics_aviation.md
│   ├── fmcg_distribution.md
│   └── it_analytics.md
│
├── generated/                        # Auto-generated per-vacancy documents (gitignored)
│   └── <company_slug>_<vacancy_id>/
│       ├── cover_letter.pdf
│       └── cv_tailored.pdf
│
├── db/
│   └── positions.db                  # SQLite database (see schema below)
│
├── scripts/
│   ├── sync_hermes.py                # Import from HERMES_BATCH_QUEUE.json → DB
│   ├── add_position.py               # CLI: manually add a vacancy to DB
│   ├── update_status.py              # CLI: update application status
│   ├── generate_docs.py              # Generate cover letter + CV for a vacancy
│   ├── dashboard.py                  # Generate HTML Kanban from DB
│   └── portals/
│       ├── hh_watcher.py             # Monitor hh.uz for new vacancies (from mywork)
│       ├── olx_scraper.py            # OLX Uzbekistan job scraper
│       └── telegram_parser.py        # Telegram job channel parser
│
├── dashboard.html                    # Latest Kanban pipeline dashboard (auto-generated)
├── PIPELINE.md                       # Human-readable pipeline summary (auto-generated)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 3. Database Schema (SQLite — `db/positions.db`)

### Table: `vacancies`
| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | HH vacancy ID or generated UUID |
| `title` | TEXT | Job title |
| `company` | TEXT | Employer name |
| `url` | TEXT | Link to posting |
| `source` | TEXT | `hh.uz` / `olx` / `telegram` / `linkedin` / `manual` |
| `tier` | INTEGER | 1=Bank/Corp, 2=Mid, 3=Small |
| `sector` | TEXT | Finance / Logistics / Analytics / Management |
| `salary_min` | INTEGER | Min salary (USD) |
| `salary_max` | INTEGER | Max salary (USD) |
| `salary_text` | TEXT | Original salary string |
| `published_at` | TEXT | ISO 8601 |
| `scraped_at` | TEXT | ISO 8601 |
| `is_active` | INTEGER | 1=active, 0=archived |

### Table: `applications`
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK AUTOINCREMENT | |
| `vacancy_id` | TEXT FK → vacancies | |
| `status` | TEXT | `applied` / `viewed` / `invited` / `interview` / `offer` / `rejected` / `declined` |
| `applied_at` | TEXT | ISO 8601 |
| `cv_variant` | TEXT | Which variant was used |
| `cover_letter_sent` | INTEGER | 0/1 |
| `pdf_sent_in_chat` | INTEGER | 0/1 — Hermes Round 2 |
| `notes` | TEXT | Free-form notes |
| `last_updated` | TEXT | ISO 8601 |

### Table: `documents`
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK AUTOINCREMENT | |
| `vacancy_id` | TEXT FK | |
| `doc_type` | TEXT | `cover_letter` / `cv` |
| `variant_used` | TEXT | e.g. `financial_analyst` |
| `file_path` | TEXT | Relative path under `generated/` |
| `generated_at` | TEXT | ISO 8601 |

---

## 4. Key Scripts

### `sync_hermes.py`
- Reads `HERMES_BATCH_QUEUE.json` from `mywork` repo
- For each vacancy with `status=applied`: upserts into `vacancies`, inserts into `applications`
- Idempotent — safe to run multiple times
- Reports: new, updated, skipped counts

### `generate_docs.py`
- Takes `vacancy_id` as argument
- Looks up vacancy in DB (title, company, sector, tier)
- Selects appropriate cover letter template by sector
- Fills `{{placeholders}}` with vacancy data + master resume highlights
- Outputs PDF to `generated/<company_slug>_<id>/`
- Records in `documents` table

### `dashboard.py`
- Queries `applications` joined with `vacancies`
- Groups by status column
- Generates `dashboard.html` — styled HTML Kanban board
- Generates `PIPELINE.md` — markdown summary table
- Style matches existing `РЕЙТИНГ_ВАКАНСИЙ_ХЭДХАНТЕР.html` aesthetic

### `add_position.py`
- Interactive CLI to manually add a vacancy not found by scrapers
- Prompts for: URL, company, title, source, notes
- Scrapes metadata from URL if hh.uz domain detected

---

## 5. Cover Letter Template System

Templates use `{{placeholder}}` syntax:
- `{{company}}` — employer name
- `{{position}}` — vacancy title
- `{{sector_hook}}` — sector-specific opening paragraph (pulled from template file)
- `{{key_achievement}}` — rotated from master resume achievements list
- `{{salary_expectation}}` — from resume.md

Each sector template (`banking_finance.md`, etc.) is a full Markdown cover letter with these placeholders. `generate_docs.py` selects the right template based on `sector` field in DB.

---

## 6. Portal Coverage

| Portal | Method | Script |
|--------|--------|--------|
| **hh.uz** | Selenium (Edge + HermesProfile) | `portals/hh_watcher.py` |
| **OLX UZ** (rabota section) | requests + BeautifulSoup | `portals/olx_scraper.py` |
| **Telegram channels** | Telethon or Pyrogram | `portals/telegram_parser.py` |
| **LinkedIn** | Manual or API | Manual entry via `add_position.py` |

---

## 7. Git Strategy

- `main` branch — stable, always has latest `dashboard.html` and `PIPELINE.md`
- `generated/` folder is **gitignored** (PDFs are large)
- `db/positions.db` is **tracked** in git (SQLite files are small, binary diff is acceptable)
- Commit message convention: `track: <company> — <status>` or `docs: generate <n> cover letters`

---

## 8. Integration with Existing Repos

| Repo | Integration |
|------|-------------|
| `mywork` | `sync_hermes.py` reads `HERMES_BATCH_QUEUE.json` |
| `MY-WORK` | Master resume files copied here as source; `ОТЧЕТ_ОТКЛИКОВ_ГЕРМЕС.md` mirrored |
| `resume` | This repo — central hub, tracks everything |

---

## 9. Success Criteria

- [ ] All 1,500+ target vacancies from Hermes importable via `sync_hermes.py`
- [ ] Dashboard shows real-time pipeline status
- [ ] Cover letter generation takes < 10 seconds per vacancy
- [ ] DB query: "show all Tier 1 vacancies with status=invited" works instantly
- [ ] New vacancies from OLX/Telegram auto-appear in DB daily
